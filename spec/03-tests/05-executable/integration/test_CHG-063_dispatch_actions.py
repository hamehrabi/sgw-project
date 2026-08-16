"""CHG-063 — assign, restore, reopen: records about a job, appended and phrased.

Each action moves `repair_jobs` through its status machine and appends a row to
`dispatch_actions`, which is append-only the way the decision record is — by trigger,
proven here by issuing the UPDATE. Nothing is dispatched: the platform has no path out.
"""

import sqlite3

import pytest
from conftest import fixture_files, sign_in


@pytest.fixture
def job(client, accounts):
    """A loaded storm with one repair job, created the only way one is — by a report."""
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Dispatch storm", "source_note": "prepared pack"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    assert created.status_code == 201, created.text
    scenario_id = created.json()["scenario_id"]
    filed = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports",
        json={"neighbourhood": "Northgate", "asset_id": None, "customers_out": 1200},
    )
    assert filed.status_code == 201, filed.text
    return {"scenario_id": scenario_id, "job_id": filed.json()["repair_job_id"]}


def board_job(client, scenario_id, job_id):
    body = client.get(f"/api/v1/scenarios/{scenario_id}/jobs").json()
    return next(item for item in body["items"] if item["job_id"] == job_id)


def test_assign_restore_and_reopen_walk_the_status_machine(client, job):
    assigned = client.post(
        f"/api/v1/repair-jobs/{job['job_id']}/assign", json={"crew": "Line crew 2"}
    )
    assert assigned.status_code == 200, assigned.text
    row = board_job(client, job["scenario_id"], job["job_id"])
    assert row["assigned_to"] == "Line crew 2"
    assert row["status"] == "in_progress"

    restored = client.post(f"/api/v1/repair-jobs/{job['job_id']}/restore", json={})
    assert restored.status_code == 200, restored.text
    assert board_job(client, job["scenario_id"], job["job_id"])["status"] == "done"

    # Restoring what is restored is a conflict, not a repeat.
    assert client.post(
        f"/api/v1/repair-jobs/{job['job_id']}/restore", json={}
    ).status_code == 409

    reopened = client.post(f"/api/v1/repair-jobs/{job['job_id']}/reopen", json={})
    assert reopened.status_code == 200, reopened.text
    # The crew note survives the reopen, so the job returns to in_progress, not pending.
    row = board_job(client, job["scenario_id"], job["job_id"])
    assert row["status"] == "in_progress"
    assert row["assigned_to"] == "Line crew 2"

    # Reopening what is open is the same conflict from the other side.
    assert client.post(
        f"/api/v1/repair-jobs/{job['job_id']}/reopen", json={}
    ).status_code == 409


def test_a_blank_crew_in_the_wide_alphabet_is_refused(client, job):
    for crew in ("", " ", "​"):  # the last is one zero-width space (CHG-023's alphabet)
        refused = client.post(
            f"/api/v1/repair-jobs/{job['job_id']}/assign", json={"crew": crew}
        )
        assert refused.status_code in (400, 422), repr(crew)


def test_an_unknown_job_is_a_404(client, job):
    for action in ("assign", "restore", "reopen"):
        body = {"crew": "Line crew 2"} if action == "assign" else {}
        refused = client.post(f"/api/v1/repair-jobs/RJ-does-not-exist/{action}", json=body)
        assert refused.status_code == 404, action


def test_every_action_is_appended_and_the_append_only_wall_holds(
    client, application, job
):
    client.post(f"/api/v1/repair-jobs/{job['job_id']}/assign", json={"crew": "Night crew"})
    client.post(f"/api/v1/repair-jobs/{job['job_id']}/restore", json={})
    client.post(f"/api/v1/repair-jobs/{job['job_id']}/reopen", json={})

    rows = application.state.db.execute(
        "select * from dispatch_actions where scenario_id = ? order by seq",
        (job["scenario_id"],),
    ).fetchall()
    assert [row["action"] for row in rows] == ["assign", "restore", "reopen"]
    assert rows[0]["crew"] == "Night crew"
    for row in rows:
        assert row["actor_user_id"], "never anonymous"
        assert row["occurred_at"]

    # Append-only by trigger, proven by issuing the statement (ADR-004's discipline).
    with pytest.raises(sqlite3.IntegrityError):
        application.state.db.execute(
            "update dispatch_actions set crew = 'rewritten' where id = ?", (rows[0]["id"],)
        )
    with pytest.raises(sqlite3.IntegrityError):
        application.state.db.execute(
            "delete from dispatch_actions where id = ?", (rows[0]["id"],)
        )


def test_the_feed_phrases_the_actions_as_human_acts(client, job):
    client.post(f"/api/v1/repair-jobs/{job['job_id']}/assign", json={"crew": "Line crew 4"})
    client.post(f"/api/v1/repair-jobs/{job['job_id']}/restore", json={})

    feed = client.get(f"/api/v1/scenarios/{job['scenario_id']}/activity").json()["items"]
    text = " ".join(entry["text"].lower() for entry in feed)
    assert "assigned line crew 4" in text
    assert "restored" in text
    for forbidden in ("auto-", "generated", "system decided", "ai briefing"):
        assert forbidden not in text, forbidden
    # And the actions are attributed entries, not system noise.
    kinds = {entry["kind"] for entry in feed if "line crew 4" in entry["text"].lower()}
    assert kinds == {"human"}
