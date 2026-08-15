"""The two authentication endpoints from `api-specification.md`, plus the read of the
current session added by CHG-009.

No account-creation path, no self-service registration, no password reset, and no second
factor. Each is excluded by a decision rather than by omission: SEC-A-006 and Q-022 for the
factor, CHG-004 and A-003 for the reset, and `security-specification.md` §7 for account
creation — "roles are set in the database, not through any endpoint".
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from app.api import errors
from app.api.events import log_event
from app.api.middleware import SESSION_COOKIE
from app.store import sessions, users

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

EMAIL_MAX_LENGTH = 254  # RFC 5321's limit on an address
PASSWORD_MAX_LENGTH = 1024


class Credentials(BaseModel):
    # Bounded before any lookup (`security-specification.md` §3). An unbounded field is
    # work an unauthenticated caller can make the server do.
    email: str = Field(min_length=1, max_length=EMAIL_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


def _identity(user) -> dict:
    """What a caller learns about themselves. No hash, no session, no internals."""
    return {"user_id": user["id"], "name": user["name"], "role": user["role"]}


@router.post("/session", status_code=201)
async def sign_in(request: Request, credentials: Credentials) -> Response:
    connection = request.app.state.db
    config = request.app.state.config
    limiter = request.app.state.rate_limiter

    account_key = users.normalise_email(credentials.email)
    client_ip = request.client.host if request.client else "unknown"

    retry_after = limiter.retry_after(account_key, client_ip)
    if retry_after is not None:
        log_event("AUTH_LOGIN_RATE_LIMITED", level=logging.WARNING, outcome="refused")
        return errors.too_many_attempts(retry_after)

    user = users.find_by_email(connection, credentials.email)

    # Verify in both branches. Returning early on an unknown email would answer "does this
    # account exist?" in the response time, whatever the body says (STEST-003).
    password_hash = user["password_hash"] if user else users.absent_account_hash(
        config.password_hash_cost
    )
    password_matches = users.verify_password(credentials.password, password_hash)

    if user is None or not password_matches:
        limiter.record_failure(account_key, client_ip)
        # Neither the address nor the password reaches this line: an unknown-account
        # attempt logs no identifier at all (UTEST-001).
        log_event("AUTH_LOGIN_FAILED", level=logging.WARNING, outcome="refused")
        return errors.invalid_credentials()

    limiter.clear_account(account_key)
    raw_token = sessions.create(connection, user["id"])
    log_event("AUTH_LOGIN_SUCCEEDED", user_id=user["id"], role=user["role"], outcome="signed_in")

    response = JSONResponse(status_code=201, content=_identity(user))
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        httponly=True,          # never reachable from script
        samesite="strict",
        secure=config.cookies_require_https,
        path="/",
        max_age=config.session_absolute_max_hours * 3600,
    )
    return response


@router.get("/session")
async def read_session(request: Request) -> dict:
    """Who am I, and in which role (CHG-009).

    `AppShell` must "render no content until the signed-in role is known", and a page
    reload leaves it holding a session cookie and nothing else. Without this the role would
    have to be kept somewhere the browser can read, which is a worse answer to the same
    question.

    Reached only through the session guard, so a caller here is already signed in.
    """
    return _identity(request.state.user)


@router.delete("/session", status_code=204)
async def sign_out(request: Request) -> Response:
    sessions.end(request.app.state.db, request.state.session_token)
    log_event("AUTH_LOGOUT", user_id=request.state.user["id"], outcome="signed_out")

    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response
