"""CHG-055 — the client's audit-trail proof, verbatim.

An accept, an adjust and a dismiss produce three decision records with the right actor,
time and reason; an UPDATE against any of them raises; and the activity feed renders all
three with no wording implying the system decided anything.
"""

import json
import sqlite3

import pytest
from conftest import fixture_files, sign_in


@pytest.fixture
def loaded(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Triage storm", "source_note": "prepared pack"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


def ranked_assets(client, scenario_id):
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    return [item for item in ranking["items"] if item["rank"] is not None]


def test_accept_adjust_and_dismiss_write_three_attributed_records(
    client, application, accounts, loaded
):
    assets = ranked_assets(client, loaded)
    actions = [
        {"asset_id": assets[0]["asset_id"], "action": "Accept", "note": None},
        {"asset_id": assets[1]["asset_id"], "action": "Adjust", "note": "gust figure is stale"},
        {"asset_id": assets[2]["asset_id"], "action": "Dismiss", "note": "decommissioned in May"},
    ]
    for action in actions:
        answered = client.post(
            f"/api/v1/scenarios/{loaded}/triage",
            json={**action, "forecast_revision": 0},
        )
        assert answered.status_code == 201, answered.text

    rows = application.state.db.execute(
        "select * from decision_records where subject_type = 'asset_ranking' order by seq"
    ).fetchall()
    assert len(rows) == 3
    assert [row["kind"] for row in rows] == ["accept", "change", "reject"]
    for row in rows:
        assert row["actor_user_id"] == accounts["admin"]["id"], "never anonymous"
        assert row["occurred_at"]
    # The why survives on the two that require one.
    assert json.loads(rows[1]["payload"])["note"] == "gust figure is stale"
    assert json.loads(rows[2]["payload"])["note"] == "decommissioned in May"

    # Append-only, proven by issuing the statement (ADR-004's discipline, FF-004's shape).
    with pytest.raises(sqlite3.IntegrityError):
        application.state.db.execute(
            "update decision_records set payload = '{}' where id = ?", (rows[0]["id"],)
        )


def test_adjust_and_dismiss_refuse_a_missing_note(client, loaded):
    asset = ranked_assets(client, loaded)[0]
    for action in ("Adjust", "Dismiss"):
        refused = client.post(
            f"/api/v1/scenarios/{loaded}/triage",
            json={"asset_id": asset["asset_id"], "forecast_revision": 0, "action": action},
        )
        assert refused.status_code == 400, action


def test_a_rank_nobody_was_shown_cannot_be_triaged(client, loaded):
    asset = ranked_assets(client, loaded)[0]
    refused = client.post(
        f"/api/v1/scenarios/{loaded}/triage",
        json={"asset_id": asset["asset_id"], "forecast_revision": 7, "action": "Accept"},
    )
    assert refused.status_code == 404, "no stored rank exists at revision 7"


def test_the_feed_renders_all_three_and_never_says_the_system_decided(
    client, loaded
):
    assets = ranked_assets(client, loaded)
    for asset, action, note in (
        (assets[0], "Accept", None),
        (assets[1], "Adjust", "condition rating disputed"),
        (assets[2], "Dismiss", "asset is offline for works"),
    ):
        client.post(
            f"/api/v1/scenarios/{loaded}/triage",
            json={
                "asset_id": asset["asset_id"],
                "forecast_revision": 0,
                "action": action,
                "note": note,
            },
        )

    feed = client.get(f"/api/v1/scenarios/{loaded}/activity").json()["items"]
    text = " ".join(entry["text"].lower() for entry in feed)
    assert "accepted the ranking for" in text
    assert "adjusted the ranking for" in text
    assert "dismissed the ranking for" in text
    for forbidden in ("auto-flagged", "system flagged", "sync", "auto-prioritised"):
        assert forbidden not in text


def test_triage_hides_nothing_from_the_ranking(client, loaded):
    """A Dismiss records disagreement with a rank. The asset stays on the list — an
    asset hidden by a click is the empty screen that reads as safety."""
    before = ranked_assets(client, loaded)
    client.post(
        f"/api/v1/scenarios/{loaded}/triage",
        json={
            "asset_id": before[0]["asset_id"],
            "forecast_revision": 0,
            "action": "Dismiss",
            "note": "testing that nothing hides",
        },
    )
    after = ranked_assets(client, loaded)
    assert [a["asset_id"] for a in after] == [a["asset_id"] for a in before]
