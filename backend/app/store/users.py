"""Accounts, and the password hashing that protects them.

No endpoint creates an account and none ever will: "Roles are set in the database, not
through any endpoint. There is no self-service promotion path, at any version."
(`security-specification.md` §7). `create_user` is reached by the seeding command and by
tests, never by a route.
"""

import hashlib
import sqlite3
import uuid
from datetime import UTC, datetime

import bcrypt

from app.config import load_config


# bcrypt silently ignores everything past 72 bytes, so a long passphrase would collide
# with its own prefix. Digesting first removes the limit; hex keeps the digest inside 72
# bytes and free of the NUL byte bcrypt also truncates on.
def _prepared(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")


def hash_password(password: str, cost: int) -> str:
    return bcrypt.hashpw(_prepared(password), bcrypt.gensalt(rounds=cost)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prepared(password), password_hash.encode("ascii"))
    except ValueError:
        # A stored value that is not a bcrypt hash must not be an exception path that
        # behaves differently from a wrong password.
        return False


# A real hash of a value nobody holds. Verifying against it when the email is unknown
# costs the same time as verifying a real one, so the response time does not say whether
# the account exists (SEC-A-001, STEST-003).
_ABSENT_ACCOUNT_HASH: dict[int, str] = {}


def absent_account_hash(cost: int) -> str:
    if cost not in _ABSENT_ACCOUNT_HASH:
        _ABSENT_ACCOUNT_HASH[cost] = hash_password(uuid.uuid4().hex, cost)
    return _ABSENT_ACCOUNT_HASH[cost]


def normalise_email(email: str) -> str:
    return email.strip().lower()


def create_user(
    connection: sqlite3.Connection,
    *,
    name: str,
    email: str,
    password: str,
    role: str,
    cost: int | None = None,
) -> str:
    if cost is None:
        cost = load_config().password_hash_cost

    user_id = f"USER-{uuid.uuid4().hex[:12]}"
    connection.execute(
        "insert into users (id, name, email, password_hash, role, created_at)"
        " values (?, ?, ?, ?, ?, ?)",
        (
            user_id,
            name,
            normalise_email(email),
            hash_password(password, cost),
            role,
            datetime.now(UTC).isoformat(),
        ),
    )
    connection.commit()
    return user_id


def set_temporary_password(
    connection: sqlite3.Connection,
    *,
    user_id: str,
    password: str,
    cost: int,
    expires_at: str,
) -> None:
    """An admin-set temporary password (CHG-053, CHG-004).

    Single-use in effect: `must_change_password` refuses every route but the change, and
    the change replaces the hash. `expires_at` is checked at sign-in — after it, the
    temporary password is a refused credential, not a slow-burning permanent one.
    """
    connection.execute(
        "update users set password_hash = ?, must_change_password = 1,"
        " temp_password_expires_at = ? where id = ?",
        (hash_password(password, cost), expires_at, user_id),
    )
    connection.commit()


def change_password(
    connection: sqlite3.Connection, *, user_id: str, password: str, cost: int
) -> None:
    """The holder chose this one: the temporary flags clear with the hash, atomically."""
    connection.execute(
        "update users set password_hash = ?, must_change_password = 0,"
        " temp_password_expires_at = null where id = ?",
        (hash_password(password, cost), user_id),
    )
    connection.commit()


def find_by_email(connection: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return connection.execute(
        "select * from users where email = ?", (normalise_email(email),)
    ).fetchone()


def find_by_id(connection: sqlite3.Connection, user_id: str) -> sqlite3.Row | None:
    return connection.execute("select * from users where id = ?", (user_id,)).fetchone()
