"""The two pieces of the API layer that every request passes through.

`SessionGuard` is **the** session check — one thing in the API layer, not a check per
handler (TASK-001 step 7). It runs *before* routing, which is what makes STEST-001 hold for
routes nobody has written yet: a data route added by TASK-002 is refused for a signed-out
caller by default, rather than by the author of that route remembering to guard it.
"""

import logging
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware

from app.api import errors
from app.api.events import log_event, new_request_id, request_id
from app.store import sessions, users

SESSION_COOKIE = "sgw_session"

# The only three things reachable without a session.
#   - the health check, because it has to answer during an incident and
#     `runtime-and-scale.md` §1 refuses on principle to gate it
#   - sign-in, because otherwise nobody could ever sign in
#   - sign-up (CHG-061), because a caller creating their first account has no session yet;
#     it creates operators only, and the role is not a parameter
PUBLIC_ROUTES = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/auth/session"),
    ("POST", "/api/v1/auth/signup"),
}

# What a signed-in holder of a temporary password may still do (CHG-053): learn who they
# are, leave, and set the real password. Everything else answers 403 until they have.
MUST_CHANGE_ALLOWED = {
    ("GET", "/api/v1/auth/session"),
    ("DELETE", "/api/v1/auth/session"),
    ("POST", "/api/v1/auth/password"),
}


class RequestContext(BaseHTTPMiddleware):
    """A correlation id for every request, and a safe answer for an unexpected failure."""

    async def dispatch(self, request, call_next):
        token = request_id.set(new_request_id())
        try:
            return await call_next(request)
        except Exception as exception:  # noqa: BLE001 — the catch-all IS the requirement
            # §9.1: an unexpected server error returns a general message and logs the
            # detail internally. Narrowing this would let some exception type through to
            # the framework's own handler, which answers with a stack trace.
            # The type, not the message: an exception string can carry anything, and this
            # log line is not the place to find out what. The response carries less again.
            log_event(
                "UNHANDLED_ERROR",
                level=logging.ERROR,
                reason=type(exception).__name__,
                path=request.url.path,
                method=request.method,
                outcome="request_failed",
            )
            return errors.internal_error()
        finally:
            request_id.reset(token)


class SessionGuard(BaseHTTPMiddleware):
    """Deny when there is no signed-in user. Allow only then.

    The order is *signed in → role on the action's allow-list*, two checks rather than
    three: there is one organisation, so there is no tenant to compare
    (`security-specification.md` §2). The role half belongs to each action's own allow-list
    and arrives with the endpoints that have one — TASK-001 builds none.
    """

    async def dispatch(self, request, call_next):
        if (request.method, request.url.path) in PUBLIC_ROUTES:
            return await call_next(request)

        raw_token = request.cookies.get(SESSION_COOKIE)
        if not raw_token:
            return errors.not_authenticated()

        connection = request.app.state.db
        config = request.app.state.config

        session = sessions.find(connection, raw_token)
        if session is None:
            return errors.not_authenticated()

        now = datetime.now(UTC)
        if not sessions.is_live(
            session,
            idle_minutes=config.session_idle_timeout_minutes,
            absolute_hours=config.session_absolute_max_hours,
            now=now,
        ):
            return errors.not_authenticated()

        user = users.find_by_id(connection, session["user_id"])
        if user is None:
            return errors.not_authenticated()

        # CHG-053: a temporary password buys exactly three things — learn who you are,
        # leave, and set a real password. Enforced here, in the one check every request
        # passes through, rather than by a redirect a browser could skip.
        if user["must_change_password"] and (
            request.method,
            request.url.path,
        ) not in MUST_CHANGE_ALLOWED:
            return errors.error(
                403,
                "password_change_required",
                "Set a new password before doing anything else.",
            )

        sessions.touch(connection, session["id"], now)
        request.state.user = user
        request.state.session_token = raw_token
        return await call_next(request)
