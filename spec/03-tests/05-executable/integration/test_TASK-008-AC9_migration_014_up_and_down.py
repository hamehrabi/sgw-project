"""TASK-008 done criterion 9 — migration 014 has an up and a down, and both were run.

Two branches nothing else reaches, for the reason TASK-006's, TASK-007's and TASK-009's
equivalent files give: *the clause you never ran is the clause whose function you assumed.*

- **The down migration.** `database-design.md` §8 requires one per migration and nothing runs
  them. A rollback that fails is discovered during the incident it was meant to end. This one
  rebuilds `damage_reports`, which every damage report and every repair-job grouping hangs off,
  so a rollback that quietly lost rows would be an ops procedure undoing the dispatch board.
- **Both `decision_records` triggers, at every point of the trip.** 014 adds a trigger to that
  table and re-asserts both append-only ones; its down migration removes only what it added.
  Asserted by issuing a real `UPDATE` and requiring the refusal, not by reading two names out of
  `sqlite_master` — a trigger can be present and wrong, which is why FF-004 is written the way
  it is.

**The upgrade path over data written while 014 was rolled back is the interesting half.** The
older shape accepts a dismissal whose reason is `''` — that is the defect CHG-033 closes — and
the rebuild cannot hold such a row. It **aborts loudly** rather than inventing a reason or
dropping the report: deciding what somebody's reason was is not a migration's decision to take,
which is migration 010's loud-backfill rule and 013's refusal to pick between two storms.
"""

import pathlib
import sqlite3

import pytest
from conftest import fixture_files, sign_in

MIGRATIONS = (
    pathlib.Path(__file__).resolve().parents[4] / "backend" / "app" / "store" / "migrations"
)
FOURTEEN = "014_a_dismissal_is_never_anonymous"
APPEND_ONLY = ("decision_records_no_update", "decision_records_no_delete")
ADDED = ("damage_reports_dismissal_is_final", "decision_records_dismiss_shape")
A_REASON = "Tree was already cleared - no damage to the line"


def load(client, accounts) -> str:
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "NOAA 2024 replay pack"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


def a_dismissed_report(client, scenario_id) -> str:
    filed = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Northgate"}
    )
    assert filed.status_code == 201, filed.text
    report_id = filed.json()["report_id"]
    dismissed = client.post(
        f"/api/v1/damage-reports/{report_id}/dismiss", json={"reason": A_REASON}
    )
    assert dismissed.status_code == 201, dismissed.text
    return report_id


def triggers(connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute("select name from sqlite_master where type = 'trigger'")
    }


def table_sql(connection, table) -> str:
    return connection.execute(
        "select sql from sqlite_master where type = 'table' and name = ?", (table,)
    ).fetchone()["sql"]


def roll_back(connection) -> None:
    connection.executescript((MIGRATIONS / f"{FOURTEEN}.down.sql").read_text(encoding="utf-8"))
    connection.execute("delete from schema_migrations where name = ?", (f"{FOURTEEN}.up.sql",))
    connection.commit()


def roll_forward(connection) -> None:
    from app.store import migrate

    assert migrate.run(connection) == [f"{FOURTEEN}.up.sql"]


def append_only_still_refuses(connection) -> None:
    """Present **and** refusing. The two are different claims and only the second matters."""
    row = connection.execute("select id from decision_records limit 1").fetchone()
    assert row is not None, "no decision_records row exists to attempt an UPDATE on"
    for statement in (
        "update decision_records set payload = '{}' where id = ?",
        "delete from decision_records where id = ?",
    ):
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(statement, (row["id"],))
            connection.commit()
        connection.rollback()


def test_the_down_migration_removes_only_what_this_migration_added(client, accounts, application):
    connection = application.state.db
    scenario_id = load(client, accounts)
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")  # FF-005's recommendation row
    a_dismissed_report(client, scenario_id)
    assert set(ADDED) <= triggers(connection)
    assert set(APPEND_ONLY) <= triggers(connection)

    roll_back(connection)

    assert not (set(ADDED) & triggers(connection))
    assert set(APPEND_ONLY) <= triggers(connection)
    append_only_still_refuses(connection)


def test_the_rule_is_gone_after_the_rollback_and_back_after_the_roll_forward(
    client, accounts, application
):
    """The defect the down migration reinstates knowingly, stated as data rather than only as a
    comment: without 014, *never anonymous* goes back to `dismissed_reason is not null`, and an
    empty string satisfies it.

    Both halves are here because the first is worth nothing without the second — a trip that
    changes nothing proves the migration matters only if the other state does something.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    a_dismissed_report(client, scenario_id)
    actor = connection.execute("select id from users limit 1").fetchone()["id"]
    second = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Saltmarsh"}
    ).json()["report_id"]
    blank = (
        "update damage_reports set status = 'dismissed', dismissed_by = ?, dismissed_reason = ''"
        " where id = ?"
    )

    with pytest.raises(sqlite3.IntegrityError, match="damage_reports_dismissal_is_attributed"):
        connection.execute(blank, (actor, second))
        connection.commit()
    connection.rollback()

    roll_back(connection)
    connection.execute(blank, (actor, second))
    connection.commit()
    assert connection.execute(
        "select dismissed_reason from damage_reports where id = ?", (second,)
    ).fetchone()["dismissed_reason"] == ""

    # The anonymous row has to go before 014 can be re-applied, which is itself the point.
    connection.execute(
        "update damage_reports set status = 'open', dismissed_by = null,"
        " dismissed_reason = null where id = ?",
        (second,),
    )
    connection.commit()
    roll_forward(connection)

    with pytest.raises(sqlite3.IntegrityError, match="damage_reports_dismissal_is_attributed"):
        connection.execute(blank, (actor, second))
        connection.commit()
    connection.rollback()
    append_only_still_refuses(connection)


def test_the_roll_forward_refuses_to_invent_a_reason_for_an_anonymous_dismissal(
    client, accounts, application
):
    """The upgrade path over data the older shape allowed. A dismissal with an empty reason
    cannot satisfy the rebuilt table, and the migration **aborts** rather than guessing what the
    dispatcher meant or dropping the report — the same refusal migration 013 makes when two
    storms cannot both be kept, and the same rule migration 010's loud backfill follows."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    report_id = a_dismissed_report(client, scenario_id)

    roll_back(connection)
    connection.execute(
        "update damage_reports set dismissed_reason = '' where id = ?", (report_id,)
    )
    connection.commit()

    with pytest.raises(sqlite3.Error) as aborted:
        roll_forward(connection)
    connection.rollback()

    assert "CHECK" in str(aborted.value) or "constraint" in str(aborted.value).lower()
    # Nothing was lost by the refusal: the report is still there for a person to look at, which
    # is the only place that decision belongs.
    assert connection.execute(
        "select count(*) from damage_reports where id = ?", (report_id,)
    ).fetchone()[0] == 1


def test_the_round_trip_keeps_every_row_and_the_board_still_works(client, accounts, application):
    """A rollback that silently emptied `damage_reports` would take the dispatch board with it.
    And the database is still one a report can be filed into afterwards, not merely read from.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    report_id = a_dismissed_report(client, scenario_id)
    counted = {
        table: connection.execute(f"select count(*) from {table}").fetchone()[0]
        for table in ("scenarios", "assets", "damage_reports", "repair_jobs", "decision_records")
    }
    assert all(counted.values()), f"a table is empty, so 'nothing was lost' is vacuous: {counted}"

    roll_back(connection)
    roll_forward(connection)

    assert {
        table: connection.execute(f"select count(*) from {table}").fetchone()[0]
        for table in counted
    } == counted
    assert set(ADDED) <= triggers(connection)
    append_only_still_refuses(connection)
    dismissed = connection.execute(
        "select * from damage_reports where id = ?", (report_id,)
    ).fetchone()
    assert (dismissed["status"], dismissed["dismissed_reason"]) == ("dismissed", A_REASON)

    board = client.get(f"/api/v1/scenarios/{scenario_id}/jobs")
    assert board.status_code == 200, board.text
    assert board.json()["dismissed_report_count"] == 1
    filed = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Old Quay"}
    )
    assert filed.status_code == 201, filed.text


def test_the_indexes_the_board_is_measured_against_survive_the_round_trip(
    client, accounts, application
):
    """PTEST-002 names `damage_reports_scenario_status_job` and asserts the board's query plan
    against it. A rebuild that re-created the table and forgot an index leaves every functional
    test green and the board scanning — which is the failure mode the performance file's first
    risk row describes, arriving through an ops procedure instead of through code."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    a_dismissed_report(client, scenario_id)
    expected = {
        row[0]
        for row in connection.execute(
            "select name from sqlite_master where type = 'index' and tbl_name = 'damage_reports'"
            " and name not like 'sqlite_autoindex%'"
        )
    }
    assert {"damage_reports_scenario_status_job", "damage_reports_seq"} <= expected

    roll_back(connection)
    roll_forward(connection)

    assert {
        row[0]
        for row in connection.execute(
            "select name from sqlite_master where type = 'index' and tbl_name = 'damage_reports'"
            " and name not like 'sqlite_autoindex%'"
        )
    } == expected
