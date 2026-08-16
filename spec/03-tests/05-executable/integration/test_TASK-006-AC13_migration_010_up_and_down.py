"""TASK-006 done criterion 13 — migration 010 has an up and a down, and both were run.

**Two branches of 010 that no other test reaches**, written because `AGENT.md`'s last lessons
row is about exactly this: *the clause you never ran is the clause whose function you assumed.*

- **The backfill.** Every test in this suite migrates an empty database, so the two
  `insert … select` statements that give an already-loaded storm its revision 0 match zero rows
  every time. They are the branch that runs on the one database that matters — the one with
  data in it — and until this file nothing had ever executed them against a storm.
- **The down migration.** `database-design.md` §8 requires one and nothing runs it. A rollback
  that fails is discovered during the incident it was meant to end.

The two are tested together because each is the other's setup: rolling 010 back and forward
again over a loaded storm is the whole round trip, and it is also the closest thing available to
the real upgrade — a database that held storms before this migration existed.

**Neither `decision_records` trigger may be missing at any point** (ADR-004, BR-004). 010
re-asserts both and its down migration deliberately does not touch them, and that is asserted
here rather than read: a migration that removes BR-004's enforcement as a side effect is the
failure ADR-004 exists to prevent, and no functional test notices it.
"""

import pathlib
import sqlite3

import pytest
from conftest import fixture_files, sign_in

MIGRATIONS = (
    pathlib.Path(__file__).resolve().parents[4] / "backend" / "app" / "store" / "migrations"
)
FIXTURE = "storm-with-a-forecast-change"
TABLES = ("scenario_forecast_revisions", "scenario_forecast_cells")
TRIGGERS = ("decision_records_no_update", "decision_records_no_delete")


def load(client, accounts) -> str:
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Track shift", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files(FIXTURE).items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


def objects(connection, kind: str) -> set[str]:
    return {
        row[0]
        for row in connection.execute("select name from sqlite_master where type = ?", (kind,))
    }


def roll_back_010(connection) -> None:
    """Apply the down migration and forget it ran, the way a rollback actually happens."""
    connection.executescript(
        (MIGRATIONS / "010_forecast_revisions.down.sql").read_text(encoding="utf-8")
    )
    connection.execute(
        "delete from schema_migrations where name = '010_forecast_revisions.up.sql'"
    )
    connection.commit()


def roll_forward_010(connection) -> None:
    from app.store import migrate

    assert migrate.run(connection) == ["010_forecast_revisions.up.sql"]


def test_the_down_migration_runs_and_leaves_both_append_only_triggers_in_place(
    client, accounts, application
):
    connection = application.state.db
    scenario_id = load(client, accounts)
    # Delivering the ranking is what appends the `recommendation` row (FF-005), and the row is
    # what makes the refusal below a real statement rather than an empty one.
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    assert TRIGGERS[0] in objects(connection, "trigger")

    roll_back_010(connection)

    tables = objects(connection, "table")
    assert not [name for name in TABLES if name in tables]
    assert "risk_scores_no_update" not in objects(connection, "trigger")
    # The whole point of the paragraph in the down migration that says it does not touch them.
    assert set(TRIGGERS) <= objects(connection, "trigger")
    # And still refusing, rather than merely present — a trigger can be there and wrong.
    row = connection.execute("select id from decision_records limit 1").fetchone()
    assert row is not None, "no decision_records row exists to attempt an UPDATE on"
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "update decision_records set payload = '{}' where id = ?", (row["id"],)
        )
        connection.commit()
    connection.rollback()


def test_a_storm_loaded_before_the_migration_gets_its_revision_zero_backfilled(
    client, accounts, application
):
    """The `insert … select` branch, run against a database that holds a storm.

    Derived entirely from stored rows — no source file is reopened, because a lost file must
    leave the picture correct (CHG-013) — so the backfilled grid has to equal the gusts the
    loader already wrote onto `assets`.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    ranked_before = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()["items"]
    cells_before = {
        row["grid_cell_id"]: row["wind_gust_mph"]
        for row in connection.execute(
            "select grid_cell_id, wind_gust_mph from scenario_forecast_cells"
            " where scenario_id = ? and forecast_revision = 0",
            (scenario_id,),
        )
    }
    assert cells_before, "revision 0 carries no cells, so the comparison below is vacuous"

    roll_back_010(connection)
    roll_forward_010(connection)

    backfilled = connection.execute(
        "select forecast_revision, valid_time from scenario_forecast_revisions"
        " where scenario_id = ?",
        (scenario_id,),
    ).fetchall()
    assert [row["forecast_revision"] for row in backfilled] == [0]
    assert backfilled[0]["valid_time"] == "2026-08-15T00:00:00Z"  # the manifest's issue time
    assert {
        row["grid_cell_id"]: row["wind_gust_mph"]
        for row in connection.execute(
            "select grid_cell_id, wind_gust_mph from scenario_forecast_cells"
            " where scenario_id = ? and forecast_revision = 0",
            (scenario_id,),
        )
    } == cells_before
    # The ranking still reads the same, gusts and all — the backfill is what the join needs.
    assert client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()["items"] == ranked_before


def test_the_later_forecasts_do_not_come_back_and_the_endpoint_says_so(
    client, accounts, application
):
    """The honest limit of a backfill, asserted rather than left to be discovered.

    Revisions 1 and 2 were parsed out of `weather.csv`; the backfill derives from `assets`,
    which carries revision 0 and nothing else. So a storm loaded *before* 010 has one forecast
    afterwards, and applying a change answers **409** rather than inventing a second one. The
    storm is re-uploaded to get its series back, which is a fact worth having in writing.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)

    roll_back_010(connection)
    roll_forward_010(connection)

    scenario = client.get(f"/api/v1/scenarios/{scenario_id}").json()
    assert scenario["forecast_revisions"] == [
        {"forecast_revision": 0, "valid_time": "2026-08-15T00:00:00Z"}
    ]
    assert scenario["next_forecast_revision"] is None

    refused = client.post(f"/api/v1/scenarios/{scenario_id}/forecast-revisions")
    assert refused.status_code == 409
    assert refused.json()["code"] == "no_further_forecast"


def test_the_stored_ranking_is_rewritable_again_once_010_is_rolled_back(
    client, accounts, application
):
    """The defect the down migration reinstates knowingly, stated as a test rather than only
    as a comment: after a rollback, AC-005's *"the previous order remains retrievable"* is back
    to resting on no code happening to issue an `UPDATE`."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    scored = connection.execute(
        "select id from risk_scores where scenario_id = ? and score is not null limit 1",
        (scenario_id,),
    ).fetchone()
    assert scored is not None
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("update risk_scores set rank = 1 where id = ?", (scored["id"],))
        connection.commit()
    connection.rollback()

    roll_back_010(connection)

    connection.execute("update risk_scores set rank = 1 where id = ?", (scored["id"],))
    connection.commit()
    assert (
        connection.execute(
            "select rank from risk_scores where id = ?", (scored["id"],)
        ).fetchone()["rank"]
        == 1
    )
