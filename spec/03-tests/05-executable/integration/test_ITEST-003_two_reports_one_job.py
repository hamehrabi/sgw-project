"""ITEST-003 — REQ-F-007. Defined in `integration-tests.md`.

*Two damage reports arrive for one location → 200; the board shows both, attached to one job.
Side effect to verify: exactly one `repair_jobs` row; both reports carry the same
`repair_job_id`.*

The status code is the weakest assertion here. The row count is the real one — and so is its
mirror image: **two reports at two locations must produce two jobs.** An implementation that
attaches every report to a single job would satisfy the first assertion perfectly and make the
board useless, which is the same shape as the fake defect checks `review-log.md` records for
TASK-002. A rule that cannot be absent is not detecting anything.

`database-design.md` §2 calls `damage_reports.repair_job_id` *the single nullable link that
makes AC-007 structural*. Structural means the database refuses the second job, so the last
test here issues that insert directly rather than through the endpoint.
"""

import sqlite3

import pytest
from conftest import fixture_files, sign_in


def loaded_storm(client, accounts, as_admin=True):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    scenario_id = created.json()["scenario_id"]
    if not as_admin:
        client.delete("/api/v1/auth/session")
        sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    return scenario_id


def report(client, scenario_id, neighbourhood, **extra):
    return client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports",
        json={"neighbourhood": neighbourhood, **extra},
    )


def test_two_reports_for_one_location_produce_one_job(client, application, accounts):
    scenario_id = loaded_storm(client, accounts)

    first = report(client, scenario_id, "Northgate")
    second = report(client, scenario_id, "Northgate")

    assert first.status_code == 201
    assert second.status_code == 201
    jobs = application.state.db.execute(
        "select * from repair_jobs where scenario_id = ?", (scenario_id,)
    ).fetchall()
    assert len(jobs) == 1, "two reports at one location are one job, never two"
    assert first.json()["repair_job_id"] == second.json()["repair_job_id"] == jobs[0]["id"]


def test_both_reports_carry_the_same_repair_job_id(client, application, accounts):
    """The side effect `integration-tests.md` names, read from the rows rather than the body."""
    scenario_id = loaded_storm(client, accounts)
    report(client, scenario_id, "Northgate")
    report(client, scenario_id, "Northgate")

    rows = application.state.db.execute(
        "select repair_job_id from damage_reports where scenario_id = ?", (scenario_id,)
    ).fetchall()

    assert len(rows) == 2
    assert len({row["repair_job_id"] for row in rows}) == 1
    assert rows[0]["repair_job_id"] is not None


def test_the_board_returns_200_and_shows_both_under_one_job(client, accounts):
    scenario_id = loaded_storm(client, accounts)
    first = report(client, scenario_id, "Northgate").json()
    second = report(client, scenario_id, "Northgate").json()

    board = client.get(f"/api/v1/scenarios/{scenario_id}/jobs")

    assert board.status_code == 200
    body = board.json()
    assert len(body["items"]) == 1
    shown = {entry["report_id"] for entry in body["items"][0]["reports"]}
    assert shown == {first["report_id"], second["report_id"]}


def test_two_locations_produce_two_jobs(client, application, accounts):
    """The silent case. Without it, "always one job" passes every assertion above."""
    scenario_id = loaded_storm(client, accounts)

    report(client, scenario_id, "Northgate")
    report(client, scenario_id, "Harbour West")

    jobs = application.state.db.execute(
        "select * from repair_jobs where scenario_id = ?", (scenario_id,)
    ).fetchall()
    assert len(jobs) == 2
    board = client.get(f"/api/v1/scenarios/{scenario_id}/jobs").json()
    assert {item["location"]["neighbourhood"] for item in board["items"]} == {
        "Northgate",
        "Harbour West",
    }


def test_the_same_place_written_differently_is_still_one_place(client, application, accounts):
    """A capital letter is not a second location, and two crews is what that costs."""
    scenario_id = loaded_storm(client, accounts)

    report(client, scenario_id, "Northgate")
    report(client, scenario_id, "  northgate ")

    assert application.state.db.execute(
        "select count(*) from repair_jobs where scenario_id = ?", (scenario_id,)
    ).fetchone()[0] == 1


def test_the_database_refuses_a_second_job_for_one_location(client, application, accounts):
    """ADR-002: the constraint lives in the schema, so a service that forgot to look first
    cannot create the second job either."""
    scenario_id = loaded_storm(client, accounts)
    report(client, scenario_id, "Northgate")
    existing = application.state.db.execute(
        "select * from repair_jobs where scenario_id = ?", (scenario_id,)
    ).fetchone()

    with pytest.raises(sqlite3.IntegrityError):
        application.state.db.execute(
            "insert into repair_jobs"
            " (id, scenario_id, status, location_key, created_at, updated_at)"
            " values ('RJ-duplicate', ?, 'pending', ?, '2026-08-16T00:00:00Z',"
            " '2026-08-16T00:00:00Z')",
            (scenario_id, existing["location_key"]),
        )
    application.state.db.rollback()


def test_a_report_belongs_to_at_most_one_job_by_construction(application):
    """§2: *the single nullable link that makes AC-007 structural.* One nullable column, and
    no association table — a report has nowhere to record a second job."""
    columns = {
        row["name"]
        for row in application.state.db.execute("pragma table_info(damage_reports)")
    }
    tables = {
        row["name"]
        for row in application.state.db.execute(
            "select name from sqlite_master where type = 'table'"
        )
    }

    # Both absence checks below are guarded by a positive one first. An enumeration that
    # quietly stops returning anything turns "nothing matches" into a test that cannot fail.
    assert "repair_job_id" in columns
    assert "damage_reports" in tables and "repair_jobs" in tables
    assert not [
        name for name in columns if name.startswith("repair_job") and name != "repair_job_id"
    ]
    assert not [name for name in tables if "report" in name and "job" in name]


def test_two_storms_never_share_a_job(client, application, accounts):
    """The scoping bug that would look entirely plausible: one neighbourhood, two storms."""
    first_storm = loaded_storm(client, accounts)
    second_storm = f"SC-{'b' * 12}"
    application.state.db.execute(
        "insert into scenarios (id, name, source_note, loaded_by, loaded_at, forecast_revision)"
        " values (?, 'Second storm', 'other', ?, '2026-08-16T00:00:00Z', 0)",
        (second_storm, accounts["admin"]["id"]),
    )
    application.state.db.commit()

    report(client, first_storm, "Northgate")
    report(client, second_storm, "Northgate")

    assert application.state.db.execute("select count(*) from repair_jobs").fetchone()[0] == 2
    board = client.get(f"/api/v1/scenarios/{second_storm}/jobs").json()
    assert len(board["items"]) == 1
    assert board["items"][0]["report_count"] == 1


def test_filing_a_report_writes_nothing_to_the_decision_record(client, application, accounts):
    """`decision_records.kind` has no value for a damage report, and that is deliberate: the
    audit table holds decisions about recommendations (CHG-015's reasoning, reused)."""
    scenario_id = loaded_storm(client, accounts)
    before = application.state.db.execute("select count(*) from decision_records").fetchone()[0]

    report(client, scenario_id, "Northgate")

    after = application.state.db.execute("select count(*) from decision_records").fetchone()[0]
    assert after == before


def test_filing_a_report_is_not_privileged(client, accounts):
    """The dispatcher holds the `user` role. The board is their screen, not an admin's."""
    scenario_id = loaded_storm(client, accounts, as_admin=False)

    assert report(client, scenario_id, "Northgate").status_code == 201
    assert client.get(f"/api/v1/scenarios/{scenario_id}/jobs").status_code == 200


def test_an_unknown_storm_is_404_rather_than_a_new_board(client, accounts):
    loaded_storm(client, accounts)

    assert report(client, "SC-nothing-here", "Northgate").status_code == 404
    assert client.get("/api/v1/scenarios/SC-nothing-here/jobs").status_code == 404
