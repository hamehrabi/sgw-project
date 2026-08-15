"""STEST-002 — SEC-A-002. Defined in `03-tests/03-non-functional/security-tests.md`.

Present a session the server has expired, and one the user has signed out of. Expect 401 in
both cases, checked on the **server**, even though the browser still holds the value.

Also covers TASK-001 acceptance criterion 5.

Both of ADR-006's limits are relative to the current time, so neither can be a database
constraint — `database-design.md` §3 names this test as the one that fails if the API
layer's session check stops enforcing them. The tests age the stored row rather than
waiting four hours, which exercises the real comparison against the real column.
"""

from datetime import UTC, datetime, timedelta

from conftest import USER_PASSWORD, build_application, sign_in
from fastapi.testclient import TestClient

PROTECTED = "/api/v1/auth/session"


def age_session(conn, *, created_at=None, last_seen_at=None):
    """Move the stored timestamps back. The browser's cookie is untouched."""
    sets, values = [], []
    if created_at is not None:
        sets.append("created_at = ?")
        values.append(created_at.isoformat())
    if last_seen_at is not None:
        sets.append("last_seen_at = ?")
        values.append(last_seen_at.isoformat())
    conn.execute(f"update sessions set {', '.join(sets)}", values)
    conn.commit()


def test_a_live_session_reaches_a_protected_route(client, accounts):
    """The control. Without it, the three refusals below could pass for the wrong reason."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])

    assert client.get(PROTECTED).status_code == 200


def test_a_signed_out_session_is_refused_server_side(client, accounts):
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    held_cookies = dict(client.cookies)

    client.delete(PROTECTED)

    # Put the value back exactly as a browser that never dropped it would send it.
    for name, value in held_cookies.items():
        client.cookies.set(name, value)

    assert client.get(PROTECTED).status_code == 401


def test_a_session_idle_past_the_limit_is_refused(client, application, accounts):
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    now = datetime.now(UTC)

    age_session(application.state.db, last_seen_at=now - timedelta(minutes=241))

    assert client.get(PROTECTED).status_code == 401


def test_a_session_past_the_absolute_cap_is_refused_however_active(client, application, accounts):
    """Idle time is fresh; the session is simply older than one shift."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    now = datetime.now(UTC)

    age_session(application.state.db, created_at=now - timedelta(hours=13), last_seen_at=now)

    assert client.get(PROTECTED).status_code == 401


def signed_in_client_with(monkeypatch, db_path, **overrides):
    """An application configured differently from the shipped values, already signed in."""
    from app.store import users

    application = build_application(monkeypatch, db_path, **overrides)
    users.create_user(
        application.state.db,
        name="Dispatcher",
        email="user@sgw.example",
        password=USER_PASSWORD,
        role="user",
    )
    client = TestClient(application)
    sign_in(client, "user@sgw.example", USER_PASSWORD)
    return application, client


def test_the_idle_limit_is_whatever_configuration_says(tmp_path, monkeypatch):
    """Raised as a check during the TASK-001 review.

    Every other test in this file uses ADR-006's shipped 240 minutes, so a hard-coded 240
    would satisfy all of them and nothing would notice. This one configures 30.
    """
    application, client = signed_in_client_with(
        monkeypatch, tmp_path / "idle.db", SESSION_IDLE_TIMEOUT_MINUTES=30
    )
    now = datetime.now(UTC)

    age_session(application.state.db, last_seen_at=now - timedelta(minutes=31))
    assert client.get(PROTECTED).status_code == 401, "31 minutes idle must exceed a 30-minute limit"


def test_a_short_configured_idle_limit_still_permits_activity_inside_it(tmp_path, monkeypatch):
    application, client = signed_in_client_with(
        monkeypatch, tmp_path / "idle.db", SESSION_IDLE_TIMEOUT_MINUTES=30
    )
    now = datetime.now(UTC)

    age_session(application.state.db, last_seen_at=now - timedelta(minutes=29))
    assert client.get(PROTECTED).status_code == 200


def test_the_absolute_cap_is_whatever_configuration_says(tmp_path, monkeypatch):
    """Same argument for the second of ADR-006's two numbers. Configured 2 hours, not 12."""
    application, client = signed_in_client_with(
        monkeypatch, tmp_path / "absolute.db", SESSION_ABSOLUTE_MAX_HOURS=2
    )
    now = datetime.now(UTC)

    age_session(application.state.db, created_at=now - timedelta(hours=3), last_seen_at=now)
    assert client.get(PROTECTED).status_code == 401, "3 hours must exceed a 2-hour cap"


def test_activity_inside_the_idle_window_keeps_the_session_alive(client, application, accounts):
    """The idle limit is measured from last use, not from sign-in.

    An operator who put down a radio 239 minutes ago is still signed in — which is the
    safety argument ADR-006 chose 240 minutes for.
    """
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    now = datetime.now(UTC)

    age_session(application.state.db, last_seen_at=now - timedelta(minutes=239))

    assert client.get(PROTECTED).status_code == 200
