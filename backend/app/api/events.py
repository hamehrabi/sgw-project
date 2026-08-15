"""Structured logging.

`technical-spec.md` §9.6 fixes the shape: a clear event name, a severity, a correlation id,
safe context, and a failure reason that is an error type rather than a dump.

**Never logged:** passwords, hashes, session values, reset links, email addresses (log
`user_id`), full asset locations (log `asset_id`), household-level damage locations, and
the contents of an uploaded file. UTEST-001 fails if a credential reaches a log line.
"""

import logging
import uuid
from contextvars import ContextVar

logger = logging.getLogger("sgw")

request_id: ContextVar[str] = ContextVar("request_id", default="")


def new_request_id() -> str:
    return f"REQ-{uuid.uuid4().hex[:12]}"


def log_event(event: str, level: int = logging.INFO, **context) -> None:
    """Emit one event. Every field passed here must already be safe to write down."""
    logger.log(level, event, extra={"event": event, "request_id": request_id.get(), **context})
