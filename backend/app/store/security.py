"""The security log (CHG-046) — the table CHG-015 decided.

Sign-in, sign-out, refused upload, permission denial, password change. Access-control
events, not decisions: CHG-015's line is why none of this is in `decision_records`, and
why nothing here needs a scenario to name.

**What may never appear in `detail`:** a credential, a session value, a password — Q-007's
list. The writers pass filenames, emails and reasons; the discipline is theirs, and
STEST-005 reads the rows back to check.
"""

import sqlite3
import uuid
from datetime import UTC, datetime

EVENTS = ("sign_in", "sign_out", "upload_refused", "permission_denied", "password_changed")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def log(connection: sqlite3.Connection, *, event: str, detail: str, actor_user_id=None) -> str:
    """Append one event. The caller's transaction if one is open; committed either way."""
    event_id = f"SEC-{uuid.uuid4().hex[:12]}"
    connection.execute(
        "insert into security_log (id, actor_user_id, event, detail, occurred_at, seq)"
        " values (?, ?, ?, ?, ?,"
        # The order is the history — allocated inside the statement, by the single writer,
        # because this clock cannot tell two rows in one 15.6 ms tick apart (CHG-018).
        " (select coalesce(max(seq), 0) + 1 from security_log))",
        (event_id, actor_user_id, event, detail, _now()),
    )
    connection.commit()
    return event_id


def recent(connection: sqlite3.Connection, *, limit: int = 50) -> list[sqlite3.Row]:
    return connection.execute(
        "select * from security_log order by seq desc limit ?", (limit,)
    ).fetchall()
