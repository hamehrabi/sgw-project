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


def a_second_storm(application, accounts, scenario_id="SC-second-storm"):
    application.state.db.execute(
        "insert into scenarios (id, name, source_note, loaded_by, loaded_at, forecast_revision)"
        " values (?, 'Second storm', 'other', ?, '2026-08-16T00:00:00Z', 0)",
        (scenario_id, accounts["admin"]["id"]),
    )
    application.state.db.commit()
    return scenario_id


def insert_report_directly(
    connection, *, scenario_id, asset_id=None, job_id=None, report_id="DR-direct"
):
    """Straight at the schema, past every line of service code. ADR-002's whole argument is
    that this is where the rule has to hold."""
    connection.execute(
        "insert into damage_reports"
        " (id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by,"
        " status, seq)"
        " values (?, ?, ?, ?, '{\"neighbourhood\": \"Northgate\"}',"
        " '2026-08-16T00:00:00Z', 'U-1', 'open',"
        " (select coalesce(max(seq), 0) + 1 from damage_reports))",
        (report_id, scenario_id, asset_id, job_id),
    )


def test_the_database_refuses_a_report_naming_an_asset_from_another_storm(
    client, application, accounts
):
    """**The finding this task was blocked on.** `asset_id references assets (id)` proves the
    asset exists; it never proved the asset is in the storm the report names. The only thing
    that did was an `if` in `api/dispatch.py` — a rule in the service layer that the store
    could refuse, which is `review-log.md`'s pre-declared Block condition and ADR-002's exact
    prohibition. Disabling that `if` left 248 tests green and nothing red.

    "Two storms blended into one ranking would look entirely plausible" (CLAUDE.md), and a
    crew sent to an asset that is not in this storm is that sentence with a van attached.
    """
    first_storm = loaded_storm(client, accounts)
    elsewhere = client.get(f"/api/v1/scenarios/{first_storm}/assets").json()["items"][0]
    second_storm = a_second_storm(application, accounts)

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        insert_report_directly(
            application.state.db, scenario_id=second_storm, asset_id=elsewhere["asset_id"]
        )
    application.state.db.rollback()


def test_the_database_refuses_a_report_hung_off_another_storms_repair_job(
    client, application, accounts
):
    """The same hole through the other foreign key: a report in storm B attached to storm A's
    job would put a neighbourhood from one storm on the other storm's board."""
    first_storm = loaded_storm(client, accounts)
    report(client, first_storm, "Northgate")
    elsewhere = application.state.db.execute(
        "select id from repair_jobs where scenario_id = ?", (first_storm,)
    ).fetchone()["id"]
    second_storm = a_second_storm(application, accounts)

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        insert_report_directly(
            application.state.db, scenario_id=second_storm, job_id=elsewhere
        )
    application.state.db.rollback()


def test_the_database_accepts_a_report_naming_an_asset_from_its_own_storm(
    client, application, accounts
):
    """The permitted case, so the two refusals above are refusing something rather than
    everything — and so an unattributable report is not caught in the same net."""
    scenario_id = loaded_storm(client, accounts)
    here = client.get(f"/api/v1/scenarios/{scenario_id}/assets").json()["items"][0]["asset_id"]

    insert_report_directly(application.state.db, scenario_id=scenario_id, asset_id=here)
    application.state.db.commit()

    stored = application.state.db.execute(
        "select asset_id from damage_reports where id = 'DR-direct'"
    ).fetchone()
    assert stored["asset_id"] == here
    # §4: a report naming no matching asset is still a report. A composite key with a null half
    # is satisfied, so nothing above forbids one.
    insert_report_directly(
        application.state.db, scenario_id=scenario_id, asset_id=None, report_id="DR-anonymous"
    )
    application.state.db.commit()
    assert application.state.db.execute(
        "select count(*) from damage_reports where asset_id is null"
    ).fetchone()[0] == 1


def test_the_endpoint_still_refuses_a_cross_storm_asset_legibly(client, application, accounts):
    """The store is the enforcement; this is the readable 400 in front of it. Both, because a
    caller deserves a sentence and the rule deserves a constraint."""
    first_storm = loaded_storm(client, accounts)
    elsewhere = client.get(f"/api/v1/scenarios/{first_storm}/assets").json()["items"][0]
    second_storm = a_second_storm(application, accounts)

    refused = report(client, second_storm, "Northgate", asset_id=elsewhere["asset_id"])

    assert refused.status_code == 400
    assert application.state.db.execute(
        "select count(*) from damage_reports where scenario_id = ?", (second_storm,)
    ).fetchone()[0] == 0


def dismiss_directly(connection, report_id, dismissed_by):
    """TASK-008's write, issued here because migration 007 already carries the columns and the
    schema permits the state today. A state the board can reach is a state the board must
    render, whether or not the endpoint that produces it has been built."""
    connection.execute(
        "update damage_reports set status = 'dismissed', dismissed_by = ?,"
        " dismissed_reason = 'called it in twice by mistake' where id = ?",
        (dismissed_by, report_id),
    )
    connection.commit()


def test_a_job_whose_only_report_is_dismissed_keeps_its_location(
    client, application, accounts
):
    """Dismissal hides a report from the working list. It does not unsay where the job is.

    The board used to derive a job's neighbourhood from its first **open** report, so this
    state produced `location: {"neighbourhood": null}` with `report_count: 0` — work on a
    shared dispatcher's board with no location and nothing behind it. CHG-017 declined a
    display column on `repair_jobs` because "the board derives a job's neighbourhood from its
    first report"; the derivation now reads the first report *filed*, which is what that
    sentence says (CHG-020).
    """
    scenario_id = loaded_storm(client, accounts)
    filed = report(client, scenario_id, "Saltmarsh").json()

    dismiss_directly(application.state.db, filed["report_id"], accounts["admin"]["id"])
    board = client.get(f"/api/v1/scenarios/{scenario_id}/jobs").json()

    job = board["items"][0]
    assert job["location"] == {"neighbourhood": "Saltmarsh"}, "a job on the board has a place"
    assert job["report_count"] == 0, "and nothing open behind it"
    assert job["dismissed_report_count"] == 1, "which is explained rather than merely empty"
    assert job["reports"] == [], "a dismissed false alarm leaves the working list"


def test_a_dismissed_report_does_not_take_its_neighbours_location_with_it(
    client, application, accounts
):
    """The silent case for the test above: with a second, still-open report at the same
    location, `location` is right whichever report it is read from — so that test would pass
    against an implementation that only ever reads the *last* report. Here the dismissed one
    is first and the open one is somewhere else entirely."""
    scenario_id = loaded_storm(client, accounts)
    first = report(client, scenario_id, "Saltmarsh").json()
    report(client, scenario_id, "Harbour West")

    dismiss_directly(application.state.db, first["report_id"], accounts["admin"]["id"])
    board = client.get(f"/api/v1/scenarios/{scenario_id}/jobs").json()

    by_place = {item["location"]["neighbourhood"]: item for item in board["items"]}
    assert set(by_place) == {"Saltmarsh", "Harbour West"}
    assert by_place["Saltmarsh"]["report_count"] == 0
    assert by_place["Harbour West"]["report_count"] == 1
    assert board["report_count"] == 1
    assert board["dismissed_report_count"] == 1


def test_a_duplicate_report_stays_on_the_board_and_says_so(client, application, accounts):
    """`damage_reports.status` has permitted `duplicate` since migration 007 and nothing read
    it: the board's filter was `status <> 'dismissed'`, so a repeat call rendered as ordinary
    open work. It stays visible — losing a radio call is the failure AC-007's second half
    exists to prevent — and it carries its status, so the screen can badge it (CHG-021).
    """
    scenario_id = loaded_storm(client, accounts)
    report(client, scenario_id, "Northgate")
    repeat = report(client, scenario_id, "Northgate").json()
    application.state.db.execute(
        "update damage_reports set status = 'duplicate' where id = ?", (repeat["report_id"],)
    )
    application.state.db.commit()

    job = client.get(f"/api/v1/scenarios/{scenario_id}/jobs").json()["items"][0]

    assert job["report_count"] == 2, "both calls are still on the board"
    assert [entry["status"] for entry in job["reports"]] == ["open", "duplicate"]
    assert job["dismissed_report_count"] == 0


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
