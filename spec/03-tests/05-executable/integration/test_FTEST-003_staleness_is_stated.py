"""FTEST-003 — REQ-NF-003(a). Defined in `03-tests/04-failure/failure-tests.md`.
Also ATEST-010 / AC-010: the staleness and the age are **stated**, never inferred.

Advance the clock past the last good load. Every screen states that it is stale and how old
it is; the banner is not dismissible.

`SCENARIO_STALE_AFTER_HOURS` is 6 (CHG-013), from the National Hurricane Center's 6-hourly
full advisories: older than that and a newer forecast almost certainly exists and is not on
screen. **One test below configures 1 hour instead**, because every other test here uses the
shipped 6 and a hard-coded 6 would satisfy all of them — the first row of `AGENT.md`'s
lessons table.
"""

from datetime import UTC, datetime, timedelta

from conftest import fixture_files, sign_in


def load(client, accounts, issued_at=None):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    files = fixture_files()
    if issued_at is not None:
        import json

        manifest = json.loads(files["manifest.json"])
        manifest["forecast_issued_at"] = issued_at
        files["manifest.json"] = json.dumps(manifest).encode()
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in files.items()],
    )
    return created.json()["scenario_id"]


def hours_ago(hours):
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def test_the_age_is_stated_even_when_the_data_is_fresh(client, accounts):
    """AC-010 is unconditional: stated, not inferred. Fresh data still says how fresh."""
    scenario_id = load(client, accounts, issued_at=hours_ago(1))

    body = client.get(f"/api/v1/scenarios/{scenario_id}").json()

    assert body["forecast_issued_at"]
    assert body["data_age_hours"] is not None
    assert body["stale"] is False


def test_data_older_than_the_limit_is_marked_stale(client, accounts):
    scenario_id = load(client, accounts, issued_at=hours_ago(7))

    body = client.get(f"/api/v1/scenarios/{scenario_id}").json()

    assert body["stale"] is True
    assert body["data_age_hours"] >= 6


def test_data_inside_the_limit_is_not_marked_stale(client, accounts):
    scenario_id = load(client, accounts, issued_at=hours_ago(5))

    assert client.get(f"/api/v1/scenarios/{scenario_id}").json()["stale"] is False


def test_the_threshold_is_whatever_configuration_says(tmp_path, monkeypatch):
    """Configured 1 hour, not the shipped 6. A hard-coded 6 fails only this test."""
    from conftest import ADMIN_PASSWORD, build_application
    from fastapi.testclient import TestClient

    application = build_application(
        monkeypatch, tmp_path / "stale.db", SCENARIO_STALE_AFTER_HOURS=1
    )
    from app.store import users

    users.create_user(
        application.state.db,
        name="Ops",
        email="admin@sgw.example",
        password=ADMIN_PASSWORD,
        role="admin",
    )
    client = TestClient(application)
    accounts = {"admin": {"email": "admin@sgw.example", "password": ADMIN_PASSWORD}}

    scenario_id = load(client, accounts, issued_at=hours_ago(2))

    body = client.get(f"/api/v1/scenarios/{scenario_id}").json()
    assert body["stale"] is True, "2 hours must exceed a 1-hour limit"


def test_the_staleness_limit_is_reported_so_a_screen_can_explain_itself(client, accounts):
    """A banner that says 'stale' without saying stale-by-what-rule is an assertion."""
    scenario_id = load(client, accounts, issued_at=hours_ago(7))

    body = client.get(f"/api/v1/scenarios/{scenario_id}").json()

    assert body["stale_after_hours"] == 6
