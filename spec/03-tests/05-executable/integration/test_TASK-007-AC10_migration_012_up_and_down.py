"""TASK-007 done criterion 10 — migration 012 has an up and a down, and both were run.

Two branches nothing else reaches, for the reason TASK-006's equivalent file gives: *the clause
you never ran is the clause whose function you assumed.*

- **The down migration.** `database-design.md` §8 requires one per migration and nothing runs
  them. A rollback that fails is discovered during the incident it was meant to end.
- **Both `decision_records` triggers, at every point of the trip.** 012 adds a third trigger
  beside them and re-asserts both; its down migration removes only the one it added. That is
  asserted here by issuing a real `UPDATE` and requiring the refusal, not by reading two names
  out of `sqlite_master` — a trigger can be present and wrong, which is why FF-004 is written
  the way it is and why renaming one during a mutation check does not disable it.

**`decision_records` is deliberately not rebuilt by this migration**, and that is the fact this
file is really guarding. A `check` constraint on the payload would need the table recreated,
which means dropping both append-only triggers and creating them again — the one thing ADR-004
forbids and CLAUDE.md lists under *Never*. Migration 008 avoided the same rebuild for the same
reason and used `alter table … add column`; 012 avoids it by using a trigger. If a later run
"tidies" the rule into a check constraint, the rebuild it needs makes this file red.
"""

import pathlib
import sqlite3

import pytest
from conftest import fixture_files, sign_in

MIGRATIONS = (
    pathlib.Path(__file__).resolve().parents[4] / "backend" / "app" / "store" / "migrations"
)
FIXTURE = "storm-for-the-planning-flow"
TWELVE = "012_a_placement_is_traceable"
APPEND_ONLY = ("decision_records_no_update", "decision_records_no_delete")
PLACEMENT = "decision_records_placement_shape"


def load(client, accounts) -> str:
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Planning flow", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files(FIXTURE).items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


def triggers(connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute("select name from sqlite_master where type = 'trigger'")
    }


def roll_back(connection) -> None:
    connection.executescript((MIGRATIONS / f"{TWELVE}.down.sql").read_text(encoding="utf-8"))
    connection.execute("delete from schema_migrations where name = ?", (f"{TWELVE}.up.sql",))
    connection.commit()


def roll_forward(connection) -> None:
    from app.store import migrate

    assert migrate.run(connection) == [f"{TWELVE}.up.sql"]


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


def test_the_down_migration_removes_only_the_trigger_it_added(client, accounts, application):
    connection = application.state.db
    scenario_id = load(client, accounts)
    # Delivering the ranking is what appends the `recommendation` row (FF-005), and the row is
    # what makes the refusal above a real statement rather than an empty one.
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    assert PLACEMENT in triggers(connection)
    assert set(APPEND_ONLY) <= triggers(connection)

    roll_back(connection)

    assert PLACEMENT not in triggers(connection)
    assert set(APPEND_ONLY) <= triggers(connection)
    append_only_still_refuses(connection)


def test_the_rule_is_gone_after_the_rollback_and_back_after_the_roll_forward(
    client, accounts, application
):
    """The defect the down migration reinstates knowingly, stated as data rather than only as a
    comment: without 012 a placement naming an asset from nowhere is accepted, and
    `product-spec.md` §10's *traceable* is back to resting on the endpoint remembering to look.

    Both halves are here because the first is worth nothing without the second — a trip that
    changes nothing proves the migration matters only if the other state does something.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    row = (
        "insert into decision_records"
        " (id, scenario_id, occurred_at, actor_user_id, kind, subject_type, subject_id, payload)"
        " values (?, ?, '2026-08-16T00:00:00Z', ?, 'placement', 'ranking', ?, ?)"
    )
    actor = connection.execute("select id from users limit 1").fetchone()["id"]
    untraceable = (
        '{"crew": "North crew", "asset_ids": ["AS-invented"], "forecast_revision": 0,'
        ' "recommendation_id": null, "note": null}'
    )

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(row, ("DR-before", scenario_id, actor, f"{scenario_id}:0", untraceable))
        connection.commit()
    connection.rollback()

    roll_back(connection)
    connection.execute(row, ("DR-during", scenario_id, actor, f"{scenario_id}:0", untraceable))
    connection.commit()
    assert connection.execute(
        "select count(*) from decision_records where id = 'DR-during'"
    ).fetchone()[0] == 1

    roll_forward(connection)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(row, ("DR-after", scenario_id, actor, f"{scenario_id}:0", untraceable))
        connection.commit()
    connection.rollback()
    append_only_still_refuses(connection)


def test_rolling_eleven_back_underneath_this_migration_fails_loudly(
    client, accounts, application
):
    """The reverse-order rule, asserted as data rather than left as a comment — the same shape
    `test_TASK-006-AC13` uses for 011-before-010, one migration further out.

    `decision_records_placement_shape` reads `risk_scores`, and 011 **rebuilds** that table:
    `drop table risk_scores` then `alter table risk_scores_old rename to risk_scores`. Since
    SQLite 3.25 a rename reparses every trigger in the schema to fix up its references, and in
    the window between those two statements `risk_scores` does not exist — so with 012 still
    applied, 011's rollback aborts before it can finish.

    That is the correct behaviour and the reason it is a test rather than a paragraph: a loud
    failure inside a transaction that rolls back whole is a rollback somebody retries in the
    right order, and a silent one is a database with no rankings in it. Both halves are here —
    the wrong order fails, and the right order does not — because the first proves nothing
    without the second.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    # The `recommendation` row FF-005 appends, so `append_only_still_refuses` has a real
    # statement to be refused rather than an empty table to pass over.
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    eleven = (
        MIGRATIONS / "011_risk_scores_belong_to_a_revision.down.sql"
    ).read_text(encoding="utf-8")
    before = connection.execute("select count(*) from risk_scores").fetchone()[0]
    assert before, "no rankings are stored, so 'nothing was lost' would be vacuous"

    with pytest.raises(sqlite3.OperationalError) as broken:
        connection.executescript(eleven)
    connection.rollback()

    assert "decision_records_placement_shape" in str(broken.value)
    assert "risk_scores" in str(broken.value)
    # The failed rollback took nothing with it: the table, its rows, and the guard are all
    # still there, and the operator can now do it in the right order.
    assert connection.execute("select count(*) from risk_scores").fetchone()[0] == before
    assert PLACEMENT in triggers(connection)
    append_only_still_refuses(connection)

    roll_back(connection)
    connection.executescript(eleven)
    connection.commit()
    assert connection.execute("select count(*) from risk_scores").fetchone()[0] == before
    assert set(APPEND_ONLY) <= triggers(connection)


def test_the_round_trip_keeps_every_row_and_the_endpoint_still_works(
    client, accounts, application
):
    """A rollback that silently emptied the audit table would be BR-004 undone by an ops
    procedure. And the database is still one a placement can be written to afterwards, not
    merely read from."""
    connection = application.state.db
    scenario_id = load(client, accounts)
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    assert (
        client.post(
            f"/api/v1/scenarios/{scenario_id}/placements",
            json={"crew": "North crew", "asset_ids": [ranking["items"][0]["asset_id"]]},
        ).status_code
        == 201
    )
    before = connection.execute("select count(*) from decision_records").fetchone()[0]
    assert before, "no decision records are stored, so 'kept' would be vacuous"

    roll_back(connection)
    assert connection.execute("select count(*) from decision_records").fetchone()[0] == before
    roll_forward(connection)
    assert connection.execute("select count(*) from decision_records").fetchone()[0] == before

    placed = client.post(
        f"/api/v1/scenarios/{scenario_id}/placements",
        json={"crew": "South crew", "asset_ids": [ranking["items"][1]["asset_id"]]},
    )
    assert placed.status_code == 201, placed.text
