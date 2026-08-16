"""CHG-039 — migration 016 has an up and a down, and both were run.

Written to the shape `test_TASK-007-AC10_migration_012_up_and_down.py` and
`test_TASK-009-AC10_migration_013_up_and_down.py` already use, for the same two reasons:

- **The down migration.** `database-design.md` §8 requires one per migration and nothing else
  runs them. A rollback that fails is discovered during the incident it was meant to end.
- **Both `decision_records` triggers, at every point of the trip.** 016 replaces two ordinary
  triggers and re-asserts the append-only pair; it rebuilds no table. That is asserted here by
  issuing a real `UPDATE` and requiring the refusal — a trigger can be present and wrong, which
  is why FF-004 is written the way it is.

**And one thing these two files must do that a schema comparison cannot:** state, as data, what
the rollback puts back. 016's down restores the six-ASCII form verbatim, so a crew label of one
U+200B becomes storable again and a storm named U+00A0 becomes loadable again. A round trip that
changes nothing proves the migration matters only if the other state does something, so both
directions are exercised against the characters the entry is about.
"""

import pathlib
import sqlite3

import pytest
from app.store import blanks
from conftest import fixture_files, sign_in

MIGRATIONS = (
    pathlib.Path(__file__).resolve().parents[4] / "backend" / "app" / "store" / "migrations"
)
FIXTURE = "storm-for-the-planning-flow"
SIXTEEN = "016_one_alphabet_reaches_every_column"
APPEND_ONLY = ("decision_records_no_update", "decision_records_no_delete")
REPLACED = ("decision_records_placement_shape", "scenarios_identity_shape")

# The two no language strips for you, and the two the round trip is really about.
ZWSP = "​"
NBSP = " "


def load(client, accounts, *, name="Planning flow") -> str:
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": name, "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files(FIXTURE).items()],
    )
    assert created.status_code == 201, created.text
    scenario_id = created.json()["scenario_id"]
    # Delivering the ranking appends the `recommendation` row (FF-005), which is what makes the
    # UPDATE below a real statement rather than an empty one.
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    return scenario_id


def triggers(connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute("select name from sqlite_master where type = 'trigger'")
    }


def roll_back(connection) -> None:
    connection.executescript((MIGRATIONS / f"{SIXTEEN}.down.sql").read_text(encoding="utf-8"))
    connection.execute("delete from schema_migrations where name = ?", (f"{SIXTEEN}.up.sql",))
    connection.commit()


def roll_forward(connection) -> None:
    from app.store import migrate

    assert migrate.run(connection) == [f"{SIXTEEN}.up.sql"]


def append_only_still_refuses(connection) -> None:
    """Present **and** refusing. The two are different claims and only the second matters."""
    row = connection.execute("select id from decision_records limit 1").fetchone()
    assert row is not None, "no decision_records row exists to attempt an UPDATE on"
    for statement in (
        "update decision_records set payload = '{}' where id = ?",
        "delete from decision_records where id = ?",
    ):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(statement, (row["id"],))
            connection.commit()
        connection.rollback()


def place(connection, scenario_id, asset_id, *, crew, row_id):
    actor = connection.execute("select id from users limit 1").fetchone()["id"]
    connection.execute(
        "insert into decision_records"
        " (id, scenario_id, occurred_at, actor_user_id, kind, subject_type, subject_id, payload)"
        " values (?, ?, '2026-08-16T00:00:00Z', ?, 'placement', 'ranking', ?, ?)",
        (
            row_id,
            scenario_id,
            actor,
            f"{scenario_id}:0",
            '{"crew": "' + crew + '", "asset_ids": ["' + asset_id + '"],'
            ' "forecast_revision": 0, "recommendation_id": null, "note": null}',
        ),
    )
    connection.commit()


def a_ranked_asset(connection, scenario_id) -> str:
    row = connection.execute(
        "select asset_id from risk_scores where scenario_id = ? and forecast_revision = 0 limit 1",
        (scenario_id,),
    ).fetchone()
    assert row is not None, "the storm ranked nothing, so a placement has nothing to name"
    return row["asset_id"]


def test_both_triggers_are_replaced_and_neither_append_only_one_is_touched(
    client, accounts, application
):
    connection = application.state.db
    load(client, accounts)

    assert set(REPLACED) <= triggers(connection)
    assert set(APPEND_ONLY) <= triggers(connection)
    append_only_still_refuses(connection)

    roll_back(connection)

    # The down restores both, under the same names — 016 replaces triggers rather than adding
    # one, so *absent after the rollback* would be a broken down migration, not a correct one.
    assert set(REPLACED) <= triggers(connection)
    assert set(APPEND_ONLY) <= triggers(connection)
    append_only_still_refuses(connection)

    roll_forward(connection)

    assert set(REPLACED) <= triggers(connection)
    assert set(APPEND_ONLY) <= triggers(connection)
    append_only_still_refuses(connection)


def test_the_invisible_crew_label_comes_back_on_the_rollback_and_goes_again(
    client, accounts, application
):
    """Both directions, because a trip that changes nothing proves nothing.

    Before: the store refuses a crew of one zero-width space. Rolled back: it accepts it, and
    the row is in the table BR-004 forbids correcting. Rolled forward: refused again.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    asset_id = a_ranked_asset(connection, scenario_id)

    with pytest.raises(sqlite3.IntegrityError, match="crew display label"):
        place(connection, scenario_id, asset_id, crew=ZWSP, row_id="DR-before")
    connection.rollback()

    roll_back(connection)
    place(connection, scenario_id, asset_id, crew=ZWSP, row_id="DR-during")
    assert (
        connection.execute(
            "select count(*) from decision_records where id = 'DR-during'"
        ).fetchone()[0]
        == 1
    ), "the rollback was supposed to reinstate the hole and did not, so the up fixed nothing"

    roll_forward(connection)
    with pytest.raises(sqlite3.IntegrityError, match="crew display label"):
        place(connection, scenario_id, asset_id, crew=ZWSP, row_id="DR-after")
    connection.rollback()


def test_the_invisible_storm_name_comes_back_on_the_rollback_and_goes_again(
    client, accounts, application
):
    connection = application.state.db
    load(client, accounts)
    actor = connection.execute("select id from users limit 1").fetchone()["id"]
    statement = (
        "insert into scenarios (id, name, source_note, content_key, loaded_by, loaded_at,"
        " forecast_revision, seq) values (?, ?, 'a note', ?, ?, '2026-08-16T00:00:00Z', 0, ?)"
    )

    with pytest.raises(sqlite3.IntegrityError, match="picks it out by"):
        connection.execute(statement, ("SC-before", NBSP, "a" * 64, actor, 9001))
        connection.commit()
    connection.rollback()

    roll_back(connection)
    connection.execute(statement, ("SC-during", NBSP, "b" * 64, actor, 9002))
    connection.commit()
    assert (
        connection.execute("select name from scenarios where id = 'SC-during'").fetchone()["name"]
        == NBSP
    ), "the rollback was supposed to reinstate the hole and did not"
    connection.execute("delete from scenarios where id = 'SC-during'")
    connection.commit()

    roll_forward(connection)
    with pytest.raises(sqlite3.IntegrityError, match="picks it out by"):
        connection.execute(statement, ("SC-after", NBSP, "c" * 64, actor, 9003))
        connection.commit()
    connection.rollback()


def test_the_up_and_the_down_hold_different_alphabets_and_both_are_deliberate(application):
    """A down that is byte-identical to the up would mean the migration changed nothing.

    Read out of the files rather than out of `sqlite_master`, because what is asserted is that
    the *rollback target* is migration 012's and 013's own text — the state the version before
    016 shipped, and not a third state no migration produced and no test covers.
    """
    up = (MIGRATIONS / f"{SIXTEEN}.up.sql").read_text(encoding="utf-8")
    down = (MIGRATIONS / f"{SIXTEEN}.down.sql").read_text(encoding="utf-8")

    # The haystack: both files must actually contain the two triggers before anything is said
    # about how they differ.
    for name in REPLACED:
        assert f"create trigger {name}" in up, f"{name} is not created by the up migration"
        assert f"create trigger {name}" in down, f"{name} is not restored by the down migration"

    assert str(max(blanks.BLANK_CODEPOINTS)) in up, "the up does not carry the widened alphabet"
    assert str(max(blanks.BLANK_CODEPOINTS)) not in down, (
        "the down carries the widened alphabet, so the rollback target is a state no earlier "
        "migration produced"
    )
    for name in APPEND_ONLY:
        assert f"create trigger if not exists {name}" in up
        assert f"create trigger if not exists {name}" in down
