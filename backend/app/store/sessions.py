"""Server-side sessions (CHG-008).

The raw session value exists in the cookie and in nothing else. This table holds a SHA-256
digest of it, which is what keeps Q-007's "no session values in the database" true of a
durable session table. A fast digest is right here and a slow one would be wrong: the value
is 256 bits of `secrets` output, so there is no low-entropy guess for a slow hash to defend.
"""

import hashlib
import secrets
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

TOKEN_BYTES = 32


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("ascii")).hexdigest()


def create(connection: sqlite3.Connection, user_id: str) -> str:
    """Create a session and return the raw token. It is never recoverable again."""
    raw_token = secrets.token_urlsafe(TOKEN_BYTES)
    now = datetime.now(UTC).isoformat()
    connection.execute(
        "insert into sessions (id, token_hash, user_id, created_at, last_seen_at, ended_at)"
        " values (?, ?, ?, ?, ?, null)",
        (f"SESS-{uuid.uuid4().hex[:12]}", hash_token(raw_token), user_id, now, now),
    )
    connection.commit()
    return raw_token


def find(connection: sqlite3.Connection, raw_token: str) -> sqlite3.Row | None:
    return connection.execute(
        "select * from sessions where token_hash = ?", (hash_token(raw_token),)
    ).fetchone()


def is_live(row: sqlite3.Row, *, idle_minutes: int, absolute_hours: int, now: datetime) -> bool:
    """Both of ADR-006's limits, plus sign-out. Checked here on every request.

    No constraint can express these — they are relative to the current time, so a row valid
    when written expires without being touched. `database-design.md` §3 names STEST-002 as
    the test that fails if this stops being enforced.
    """
    if row["ended_at"] is not None:
        return False
    if datetime.fromisoformat(row["last_seen_at"]) + timedelta(minutes=idle_minutes) <= now:
        return False
    # The absolute cap, measured from sign-in and never refreshed by activity.
    return datetime.fromisoformat(row["created_at"]) + timedelta(hours=absolute_hours) > now


def touch(connection: sqlite3.Connection, session_id: str, now: datetime) -> None:
    """Restart the idle clock. The absolute cap is untouched, on purpose."""
    connection.execute(
        "update sessions set last_seen_at = ? where id = ?", (now.isoformat(), session_id)
    )
    connection.commit()


def end(connection: sqlite3.Connection, raw_token: str) -> None:
    """Sign out, in the store. A logout the server does not know about is a session still open."""
    connection.execute(
        "update sessions set ended_at = ? where token_hash = ? and ended_at is null",
        (datetime.now(UTC).isoformat(), hash_token(raw_token)),
    )
    connection.commit()


def end_all_for_user(connection: sqlite3.Connection, user_id: str) -> None:
    connection.execute(
        "update sessions set ended_at = ? where user_id = ? and ended_at is null",
        (datetime.now(UTC).isoformat(), user_id),
    )
    connection.commit()
