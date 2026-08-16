"""ADR-002 — "the database owns everything durable. Nothing that matters lives in process
memory, so a restart is not an incident."

Raised as a check during the TASK-001 review rather than written with the task. It is the
property CHG-008 argued the `sessions` table into existence for, and nothing was asserting
it: a session held in memory would have passed every other test in this suite, because
every one of them uses a single application instance.

An operator signed in during a storm must still be signed in after the service restarts.
"""

from conftest import USER_PASSWORD, build_application, sign_in
from fastapi.testclient import TestClient


def make_account(application):
    from app.store import users

    return users.create_user(
        application.state.db,
        name="Dispatcher",
        email="user@sgw.example",
        password=USER_PASSWORD,
        role="operator",
    )


def test_a_session_outlives_the_process_that_created_it(tmp_path, monkeypatch):
    database = tmp_path / "restart.db"

    before = build_application(monkeypatch, database)
    make_account(before)
    first = TestClient(before)
    assert sign_in(first, "user@sgw.example", USER_PASSWORD).status_code == 201
    held_cookies = dict(first.cookies)
    before.state.db.close()  # the restart

    after = build_application(monkeypatch, database)
    second = TestClient(after)
    for name, value in held_cookies.items():
        second.cookies.set(name, value)

    response = second.get("/api/v1/auth/session")

    assert response.status_code == 200
    assert response.json()["role"] == "operator"


def test_signing_out_before_the_restart_still_holds_after_it(tmp_path, monkeypatch):
    """The other half. Durable state must not resurrect an ended session."""
    database = tmp_path / "restart.db"

    before = build_application(monkeypatch, database)
    make_account(before)
    first = TestClient(before)
    sign_in(first, "user@sgw.example", USER_PASSWORD)
    held_cookies = dict(first.cookies)
    first.delete("/api/v1/auth/session")
    before.state.db.close()

    after = build_application(monkeypatch, database)
    second = TestClient(after)
    for name, value in held_cookies.items():
        second.cookies.set(name, value)

    assert second.get("/api/v1/auth/session").status_code == 401
