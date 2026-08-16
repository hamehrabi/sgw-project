"""TASK-001 acceptance criterion 6 — defined in `02-tasks/02-task-files/TASK-001.md`.

"Attempting to insert a user with a role other than `admin` or `operator` is refused by the
**database**."

No `TEST-` identifier is cited because the register defines none for this criterion, and
minting one here would create an id `unit-tests.md` does not own.

The assertion is against the store, not the service layer. ADR-002 puts every constraint
the schema can express into the schema, precisely so that a rule survives a refactor of the
code above it — a service-layer role check is removed by the first tidy-up with every
functional test still green.
"""

import sqlite3

import pytest


def test_the_two_specified_roles_are_accepted(application):
    from app.store import users

    conn = application.state.db

    assert users.create_user(
        conn, name="A", email="a@sgw.example", password="a-password", role="admin"
    )
    assert users.create_user(
        conn, name="B", email="b@sgw.example", password="a-password", role="operator"
    )


@pytest.mark.parametrize("role", ["superuser", "user", "ADMIN", "", "administrator"])
def test_the_database_refuses_any_other_role(application, role):
    """Issued directly against the store, bypassing anything the application might check."""
    conn = application.state.db

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "insert into users (id, name, email, password_hash, role, created_at)"
            " values (?, ?, ?, ?, ?, ?)",
            ("U-1", "Third Role", "third@sgw.example", "$2b$04$notarealhash", role, "2026-08-15"),
        )
        conn.commit()


def test_email_is_unique(application):
    """`database-design.md` §1: one account per address."""
    from app.store import users

    conn = application.state.db
    users.create_user(conn, name="A", email="dup@sgw.example", password="pw", role="operator")

    with pytest.raises(sqlite3.IntegrityError):
        users.create_user(conn, name="B", email="dup@sgw.example", password="pw", role="operator")
