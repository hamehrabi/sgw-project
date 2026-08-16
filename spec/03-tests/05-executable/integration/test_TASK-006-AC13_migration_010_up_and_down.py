"""TASK-006 done criterion 13 — migrations 010 and 011 have an up and a down, and both were run.

**Branches of the two migrations that no other test reaches**, written because `AGENT.md`'s last
lessons row is about exactly this: *the clause you never ran is the clause whose function you
assumed.*

- **The backfill.** Every test in this suite migrates an empty database, so the `insert … select`
  statements that give an already-loaded storm its revision 0 match zero rows every time. They
  are the branch that runs on the one database that matters — the one with data in it — and
  until this file nothing had ever executed them against a storm.
- **The down migrations.** `database-design.md` §8 requires one per migration and nothing runs
  them. A rollback that fails is discovered during the incident it was meant to end.
- **Their order.** 011's `risk_scores_names_a_forecast` reads `scenario_forecast_revisions`,
  which 010's down migration drops — so rolling 010 back **first** leaves a trigger standing
  behind a table that is gone and every later `insert into risk_scores` fails with *no such
  table*. Migrations roll back in reverse order for exactly this reason, and the round trip
  below walks both directions rather than asserting the rule in a comment.

**012 joined the stack for the same reason 011 is in it, and it is why this file changed under
TASK-007.** `decision_records_placement_shape` reads `risk_scores`, and 011 **rebuilds** that
table — `drop table` then `alter table … rename to`. Since SQLite 3.25 a rename reparses every
trigger in the schema to fix up its references, so with 012 still applied the rename lands in the
window where `risk_scores` does not exist and 011 fails outright, up or down. That is the
ordinary reverse-order rule reaching one migration further, and `test_TASK-007-AC10` asserts the
wrong order fails rather than leaving it to be met during an incident.

The backfill and the rollback are tested together because each is the other's setup: rolling the
pair back and forward again over a loaded storm is the whole trip, and it is also the closest
thing available to the real upgrade — a database that held storms before these migrations existed.

**Neither `decision_records` trigger may be missing at any point** (ADR-004, BR-004). Both
migrations re-assert both and neither down migration touches them, and that is asserted here
rather than read: a migration that removes BR-004's enforcement as a side effect is the failure
ADR-004 exists to prevent, and no functional test notices it.
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

TEN = "010_forecast_revisions"
ELEVEN = "011_risk_scores_belong_to_a_revision"
# Newer than both, and it has to come off before either of them: its trigger reads
# `risk_scores`, which 011 rebuilds by dropping and renaming.
TWELVE = "012_a_placement_is_traceable"

# The fixture's manifest says the advisory was issued at 21:00 on the 14th; its earliest
# forecast is valid from 00:00 on the 15th. **They are deliberately different strings**, and
# that is what lets the assertions below tell the loader's dating apart from the backfill's.
MANIFEST_ISSUED_AT = "2026-08-14T21:00:00Z"
EARLIEST_FORECAST_AT = "2026-08-15T00:00:00Z"


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


def roll_back(connection, name: str) -> None:
    """Apply one down migration and forget it ran, the way a rollback actually happens."""
    connection.executescript((MIGRATIONS / f"{name}.down.sql").read_text(encoding="utf-8"))
    connection.execute(
        "delete from schema_migrations where name = ?", (f"{name}.up.sql",)
    )
    connection.commit()


def roll_back_the_stack(connection) -> None:
    """**Newest first.** 011's insert guard reads a table 010 creates; taking 010 out from
    underneath it leaves the guard pointing at nothing, and the next ranking written to that
    database fails. 012's placement guard reads the table 011 **rebuilds**, so it has to come off
    before 011 for the rebuild's rename to resolve at all."""
    roll_back(connection, TWELVE)
    roll_back(connection, ELEVEN)
    roll_back(connection, TEN)


def roll_forward_the_stack(connection) -> None:
    from app.store import migrate

    assert migrate.run(connection) == [
        f"{TEN}.up.sql",
        f"{ELEVEN}.up.sql",
        f"{TWELVE}.up.sql",
    ]


def test_the_down_migrations_run_and_leave_both_append_only_triggers_in_place(
    client, accounts, application
):
    connection = application.state.db
    scenario_id = load(client, accounts)
    # Delivering the ranking is what appends the `recommendation` row (FF-005), and the row is
    # what makes the refusal below a real statement rather than an empty one.
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    assert TRIGGERS[0] in objects(connection, "trigger")

    roll_back_the_stack(connection)

    tables = objects(connection, "table")
    assert not [name for name in TABLES if name in tables]
    assert "risk_scores_no_update" not in objects(connection, "trigger")
    assert "risk_scores_no_delete" not in objects(connection, "trigger")
    # The whole point of the paragraph in each down migration that says it does not touch them.
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


def test_the_round_trip_keeps_every_stored_ranking_and_the_wrong_order_does_not(
    client, accounts, application
):
    """The order the two down migrations run in, asserted as data rather than as a comment.

    Rolled back newest-first and forward again, the trip is lossless: a rollback that emptied the
    ranking would be the screen CLAUDE.md forbids reading as safety, arriving by way of an ops
    procedure. Rolled back in the wrong order it is not lossless — 011's insert guard is left
    reading a table 010 has just dropped, and the next storm loaded into that database fails
    outright. Both halves are here because the first is worth nothing without the second: a trip
    that changes nothing proves the order matters only if the other order does something.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    before = connection.execute("select count(*) from risk_scores").fetchone()[0]
    assert before, "no rankings are stored, so 'kept' would be vacuous"

    roll_back_the_stack(connection)
    assert connection.execute("select count(*) from risk_scores").fetchone()[0] == before
    roll_forward_the_stack(connection)
    assert connection.execute("select count(*) from risk_scores").fetchone()[0] == before
    # And the database is still one a ranking can be written to, not merely read from — a whole
    # storm loaded after the trip, series and ranking, through the guard 011 puts in front of
    # every insert. (This storm's own later forecasts do not come back; that is the backfill's
    # documented limit and the test two below is entirely about it.)
    assert client.get(f"/api/v1/scenarios/{scenario_id}/risks").status_code == 200
    second = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    assert second.status_code == 201, second.text
    assert connection.execute("select count(*) from risk_scores").fetchone()[0] > before

    # The wrong order. 010 alone, with 011 still applied.
    roll_back(connection, TEN)

    with pytest.raises(sqlite3.OperationalError) as broken:
        connection.execute(
            "insert into risk_scores (id, scenario_id, asset_id, forecast_revision, score, band,"
            " rank, reasons, unscored_reason, weight_set_version, computed_at)"
            " select 'RS-after', scenario_id, asset_id, 7, 1.0, 'Low', 1, '[\"x\"]', null, 'x',"
            " 'now' from risk_scores limit 1"
        )
        connection.commit()
    connection.rollback()
    assert "scenario_forecast_revisions" in str(broken.value)


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

    roll_back_the_stack(connection)
    roll_forward_the_stack(connection)

    backfilled = connection.execute(
        "select forecast_revision, valid_time from scenario_forecast_revisions"
        " where scenario_id = ?",
        (scenario_id,),
    ).fetchall()
    assert [row["forecast_revision"] for row in backfilled] == [0]
    assert {
        row["grid_cell_id"]: row["wind_gust_mph"]
        for row in connection.execute(
            "select grid_cell_id, wind_gust_mph from scenario_forecast_cells"
            " where scenario_id = ? and forecast_revision = 0",
            (scenario_id,),
        )
    } == cells_before
    # The ranking still reads the same *order*, gusts and all — the backfill is what the join
    # needs. Only the age beside each gust moves, which the next test is entirely about.
    after = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()["items"]
    assert [item["asset_id"] for item in after] == [item["asset_id"] for item in ranked_before]
    assert [item["score"] for item in after] == [item["score"] for item in ranked_before]


def test_the_backfill_dates_revision_zero_from_the_manifest_and_the_loader_does_not(
    client, accounts, application
):
    """An honest limit of the backfill, made loud instead of left silent.

    The loader dates revision 0 from the **earliest `valid_time` in `weather.csv`**; the backfill
    has no such column to read — `assets` carries the gust and never the time it was issued for —
    so it uses `coalesce(scenarios.forecast_issued_at, loaded_at)`, the manifest's issue time.
    For a storm whose advisory was issued before its first forecast is valid, those are two
    different strings, and a rollback-and-forward round trip therefore **re-dates** every gust in
    the joined asset view and in revision 0's ranking.

    This test exists because the review found the old assertion could not tell the two apart: the
    fixture's manifest issue time and its first forecast time were the same string, so *"the
    backfill takes the wrong date"* was a mutation nothing could catch. The fixture now differs by
    three hours, both dates are named, and the consequence is asserted on the value BR-003 puts
    the age beside — because a value that is quietly re-dated is exactly the wrongness REQ-NF-003
    exists to prevent, and the honest answer is to know it happens rather than to discover it.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    assert MANIFEST_ISSUED_AT != EARLIEST_FORECAST_AT

    at_load = connection.execute(
        "select valid_time from scenario_forecast_revisions"
        " where scenario_id = ? and forecast_revision = 0",
        (scenario_id,),
    ).fetchone()["valid_time"]
    assert at_load == EARLIEST_FORECAST_AT
    assert (
        client.get(f"/api/v1/scenarios/{scenario_id}").json()["forecast_issued_at"]
        == MANIFEST_ISSUED_AT
    )

    roll_back_the_stack(connection)
    roll_forward_the_stack(connection)

    after = connection.execute(
        "select valid_time from scenario_forecast_revisions"
        " where scenario_id = ? and forecast_revision = 0",
        (scenario_id,),
    ).fetchone()["valid_time"]
    assert after == MANIFEST_ISSUED_AT, (
        "the backfill's only stored source is the manifest's issue time; if this changes, say "
        "where the new source came from"
    )
    # And it travels: BR-003 puts the age beside the value, so the gust an operator reads after
    # a round trip claims the advisory's time rather than the forecast's. Recovering the real
    # one needs the prepared file, which is what re-uploading the storm does.
    gust = [
        value
        for value in client.get(f"/api/v1/scenarios/{scenario_id}/assets").json()["items"][0][
            "values"
        ]
        if value["name"] == "wind_gust_mph"
    ][0]
    assert gust["observed_at"] == MANIFEST_ISSUED_AT
    assert client.get(f"/api/v1/scenarios/{scenario_id}").json()["forecast_revisions"] == [
        {"forecast_revision": 0, "valid_time": MANIFEST_ISSUED_AT, "ranked": True}
    ]


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

    roll_back_the_stack(connection)
    roll_forward_the_stack(connection)

    scenario = client.get(f"/api/v1/scenarios/{scenario_id}").json()
    assert scenario["forecast_revisions"] == [
        {"forecast_revision": 0, "valid_time": MANIFEST_ISSUED_AT, "ranked": True}
    ]
    assert scenario["next_forecast_revision"] is None

    refused = client.post(f"/api/v1/scenarios/{scenario_id}/forecast-revisions")
    assert refused.status_code == 409
    assert refused.json()["code"] == "no_further_forecast"


def test_the_stored_ranking_is_rewritable_again_once_the_pair_is_rolled_back(
    client, accounts, application
):
    """The defect the down migrations reinstate knowingly, stated as a test rather than only as
    a comment: after a rollback, AC-005's *"the previous order remains retrievable"* is back to
    resting on no code happening to issue an `UPDATE`."""
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

    roll_back_the_stack(connection)

    connection.execute("update risk_scores set rank = 1 where id = ?", (scored["id"],))
    connection.commit()
    assert (
        connection.execute(
            "select rank from risk_scores where id = ?", (scored["id"],)
        ).fetchone()["rank"]
        == 1
    )


def test_rolling_eleven_back_alone_reinstates_only_its_own_guarantees(
    client, accounts, application
):
    """011's down migration on its own: `risk_scores_no_update` stays (010 owns it), and the
    three invariants 011 added go — no more and no fewer.

    Asserted because a down migration that removes more than its up migration added is the same
    class of failure as one that removes a `decision_records` trigger — it is just quieter.

    012 comes off first, because it is newer and because 011 rebuilds the table its trigger
    reads. What that rollback removes is asserted by `test_TASK-007-AC10`, not here; taking it
    off is the reverse-order rule and nothing more.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    asset_id = connection.execute(
        "select asset_id from risk_scores where scenario_id = ? limit 1", (scenario_id,)
    ).fetchone()["asset_id"]

    roll_back(connection, TWELVE)
    roll_back(connection, ELEVEN)

    assert "risk_scores_no_update" in objects(connection, "trigger")
    assert "risk_scores_no_delete" not in objects(connection, "trigger")
    assert "risk_scores_names_a_forecast" not in objects(connection, "trigger")
    assert set(TRIGGERS) <= objects(connection, "trigger")
    # The invariants CHG-028 added, gone with it: a ranking of a forecast that does not exist,
    # and a delete-and-reinsert of a live one.
    connection.execute(
        "insert into risk_scores (id, scenario_id, asset_id, forecast_revision, score, band,"
        " rank, reasons, unscored_reason, weight_set_version, computed_at)"
        " values ('RS-back', ?, ?, 42, 1.0, 'Low', 1, '[\"x\"]', null, 'x', 'now')",
        (scenario_id, asset_id),
    )
    connection.execute(
        "delete from risk_scores where scenario_id = ? and forecast_revision = 0", (scenario_id,)
    )
    connection.commit()
    # And the guarantee 010 owns is still there, which is what "only its own" means.
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("update risk_scores set rank = 2 where id = 'RS-back'")
        connection.commit()
    connection.rollback()
