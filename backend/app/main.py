"""Application entry point.

Configuration is validated, and the schema is migrated, **before** the application object
exists. A missing value therefore fails at startup with a named message rather than at the
first request during a storm (TASK-001 acceptance criterion 7).
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api import (
    activity,
    asset_summaries,
    auth,
    dismissals,
    dispatch,
    errors,
    health,
    placements,
    quality,
    recommendations,
    scenarios,
    staging,
    summaries,
    triage,
)
from app.api.middleware import RequestContext, SessionGuard
from app.api.rate_limit import RateLimiter
from app.config import load_config
from app.store import db, migrate


def create_app() -> FastAPI:
    config = load_config()

    application = FastAPI(
        title="SGW Resilience Platform",
        version="1.0",
        description=(
            "Ranks assets by risk and records decisions. It recommends; people decide. "
            "No endpoint writes to anything outside this platform (BR-005, SEC-Z-005)."
        ),
    )
    application.state.config = config
    application.state.db = db.connect(config.database_path)
    application.state.rate_limiter = RateLimiter()

    migrate.run(application.state.db)

    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(scenarios.router)
    application.include_router(dispatch.router)
    application.include_router(dispatch.jobs_router)
    application.include_router(dismissals.router)
    application.include_router(placements.router)
    application.include_router(recommendations.router)
    application.include_router(quality.router)
    application.include_router(staging.router)
    application.include_router(summaries.router)
    application.include_router(asset_summaries.router)
    application.include_router(activity.router)
    application.include_router(triage.router)

    # Added inner-first: the last one added is the outermost, so every request gets a
    # correlation id and a safe failure before it reaches the session check.
    application.add_middleware(SessionGuard)
    application.add_middleware(RequestContext)

    @application.exception_handler(RequestValidationError)
    async def _validation_failed(request, exception):
        # The contract says 400 with `code` and `message` (`api-specification.md`), not
        # FastAPI's 422 with a raw parser dump — which would echo the submitted password
        # straight back in the error body.
        return errors.validation_error("The submitted value does not match the required format.")

    return application


# There is deliberately no module-level `app`. Building one at import time would run
# startup validation as a side effect of importing, which turns "fails at startup, named"
# into "fails when something happens to import this module". Run it as a factory:
#
#     uvicorn app.main:create_app --factory
