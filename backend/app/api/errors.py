"""Error responses.

Two rules, from `api-specification.md` and `security-specification.md` §6: every error uses
`code` and `message` (and `field` only where naming one is safe), and no error reveals an
internal detail — not a stack trace, not a database path, not which half of a credential
was wrong.
"""

from fastapi.responses import JSONResponse


def error(status: int, code: str, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"code": code, "message": message}, headers=headers
    )


def not_authenticated() -> JSONResponse:
    return error(401, "not_authenticated", "Please sign in to continue.")


def invalid_credentials() -> JSONResponse:
    """Identical for an unknown email and a wrong password (SEC-A-001, STEST-003).

    No `field` key: naming one would say which half was wrong.
    """
    return error(401, "invalid_credentials", "The email or password is incorrect.")


def too_many_attempts(retry_after_seconds: int) -> JSONResponse:
    return error(
        429,
        "too_many_attempts",
        "Too many sign-in attempts. Please try again later.",
        headers={"Retry-After": str(retry_after_seconds)},
    )


def validation_error(message: str) -> JSONResponse:
    return error(400, "validation_error", message)


def internal_error() -> JSONResponse:
    return error(500, "internal_error", "Something went wrong. Please try again later.")
