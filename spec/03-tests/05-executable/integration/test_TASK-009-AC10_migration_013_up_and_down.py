"""TASK-009 done criterion 10 — migration 013 has an up and a down, and both were run.

Two branches nothing else reaches, for the reason TASK-006's and TASK-007's equivalent files
give: *the clause you never ran is the clause whose function you assumed.*

- **The down migration.** `database-design.md` §8 requires one per migration and nothing runs
  them. A rollback that fails is discovered during the incident it was meant to end — and this
  one has more to undo than its predecessors, because rolling it back has to put the content
  digest back in `source_note` where the pre-013 code looks for it.
- **Both `decision_records` triggers, at every point of the trip.** 013 adds two triggers to a
  different table and re-asserts both append-only ones; its down migration removes only what it
  added. That is asserted here by issuing a real `UPDATE` and requiring the refusal, not by
  reading two names out of `sqlite_master` — a trigger can be present and wrong, which is why
  FF-004 is written the way it is.

**`scenarios` is deliberately not rebuilt, and that is the fact this file is really guarding.**
Six tables reference it with `on delete cascade`, so the standard SQLite rebuild — create,
copy, `drop table scenarios`, rename — would delete every asset, ranking, damage report, repair
job and decision record in the database on the way past. A check constraint is therefore
unavailable and the rules are triggers, which is CHG-026, CHG-028(b) and CHG-029's argument
reused. If a later run "tidies" them into check constraints, the rebuild it needs makes this
file red.
"""

import pathlib
import sqlite3

import pytest
from conftest import fixture_files, sign_in

MIGRATIONS = (
    pathlib.Path(__file__).resolve().parents[4] / "backend" / "app" / "store" / "migrations"
)
THIRTEEN = "013_a_storm_is_identified_by_its_content"
APPEND_ONLY = ("decision_records_no_update", "decision_records_no_delete")
IDENTITY = ("scenarios_identity_shape", "scenarios_identity_is_fixed")


def load(client, accounts, *, name="Helene replay", source_note="NOAA 2024 replay pack") -> str:
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": name, "source_note": source_note},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


def triggers(connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute("select name from sqlite_master where type = 'trigger'")
    }


def columns(connection, table) -> set[str]:
    return {row[1] for row in connection.execute(f"pragma table_info({table})")}


def roll_back(connection) -> None:
    connection.executescript((MIGRATIONS / f"{THIRTEEN}.down.sql").read_text(encoding="utf-8"))
    connection.execute("delete from schema_migrations where name = ?", (f"{THIRTEEN}.up.sql",))
    connection.commit()


def roll_forward(connection) -> None:
    from app.store import migrate

    assert migrate.run(connection) == [f"{THIRTEEN}.up.sql"]


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
    load(client, accounts)
    client.get("/api/v1/scenarios")  # nothing to write; only to prove the endpoint is reachable
    scenario_id = connection.execute("select id from scenarios").fetchone()["id"]
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")  # FF-005's recommendation row
    assert set(IDENTITY) <= triggers(connection)
    assert set(APPEND_ONLY) <= triggers(connection)

    roll_back(connection)

    assert not (set(IDENTITY) & triggers(connection))
    assert set(APPEND_ONLY) <= triggers(connection)
    append_only_still_refuses(connection)


def test_the_rollback_puts_the_digest_back_where_the_older_code_looks_for_it(
    client, accounts, application
):
    """The half a rollback of this migration has that its predecessors did not.

    Before 013, `find_by_content_key` selected `where source_note = ?` — the digest lived in the
    column meant for the admin's note (CHG-031). Rolling 013 back without moving it there leaves
    the older code unable to recognise an identical re-load at all, so the next upload of a
    storm already loaded creates **a second copy with its own ranking**. The rollback restores
    the older shape rather than leaving the newer data in it.
    """
    connection = application.state.db
    load(client, accounts, source_note="NOAA 2024 replay pack")
    stored = connection.execute("select content_key, source_note from scenarios").fetchone()
    digest = stored["content_key"]
    assert len(digest) == 64
    assert stored["source_note"] == "NOAA 2024 replay pack"

    roll_back(connection)

    after = connection.execute("select source_note from scenarios").fetchone()
    assert after["source_note"] == digest
    assert "content_key" not in columns(connection, "scenarios")
    assert "seq" not in columns(connection, "scenarios")


def test_the_rule_is_gone_after_the_rollback_and_back_after_the_roll_forward(
    client, accounts, application
):
    """The defect the down migration reinstates knowingly, stated as data rather than only as a
    comment: without 013, §5's *identical content replaces in place* goes back to resting on a
    `select` in front of an `insert`, and two rows for one storm are accepted.

    Both halves are here because the first is worth nothing without the second — a trip that
    changes nothing proves the migration matters only if the other state does something.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    # FF-005's `recommendation` row, so `append_only_still_refuses` has a real statement to be
    # refused rather than an empty table to pass over.
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    actor = connection.execute("select id from users limit 1").fetchone()["id"]
    digest = connection.execute("select content_key from scenarios").fetchone()["content_key"]
    with_key = (
        "insert into scenarios"
        " (id, name, source_note, content_key, loaded_by, loaded_at, forecast_revision, seq)"
        " values (?, 'A rival copy', 'note', ?, ?, '2026-08-16T00:00:00Z', 0, 9001)"
    )
    without_key = (
        "insert into scenarios (id, name, source_note, loaded_by, loaded_at, forecast_revision)"
        " values (?, 'A rival copy', ?, ?, '2026-08-16T00:00:00Z', 0)"
    )

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(with_key, ("SC-before", digest, actor))
        connection.commit()
    connection.rollback()

    roll_back(connection)
    connection.execute(without_key, ("SC-during", digest, actor))
    connection.commit()
    assert connection.execute(
        "select count(*) from scenarios where source_note = ?", (digest,)
    ).fetchone()[0] == 2

    # The rival copy has to go before 013 can be re-applied — which is itself the point: the
    # unique index is what the older shape had no way to hold.
    connection.execute("delete from scenarios where id = 'SC-during'")
    connection.commit()
    roll_forward(connection)

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(with_key, ("SC-after", digest, actor))
        connection.commit()
    connection.rollback()
    append_only_still_refuses(connection)


def test_the_roll_forward_refuses_to_leave_two_copies_of_one_storm_behind(
    client, accounts, application
):
    """The upgrade path over data written while 013 was rolled back. Two rows for one storm
    cannot both satisfy `unique (content_key)`, and the migration **aborts loudly** rather than
    picking one — deciding which of two rankings to destroy is not a migration's decision to
    take. Migration 010's backfill dating was made loud for the same reason."""
    connection = application.state.db
    load(client, accounts)
    actor = connection.execute("select id from users limit 1").fetchone()["id"]
    digest = connection.execute("select content_key from scenarios").fetchone()["content_key"]

    roll_back(connection)
    connection.execute(
        "insert into scenarios (id, name, source_note, loaded_by, loaded_at, forecast_revision)"
        " values ('SC-rival', 'A rival copy', ?, ?, '2026-08-16T00:00:00Z', 0)",
        (digest, actor),
    )
    connection.commit()

    with pytest.raises(sqlite3.Error) as aborted:
        roll_forward(connection)
    connection.rollback()

    assert "content_key" in str(aborted.value) or "unique" in str(aborted.value).lower()
    # Nothing was lost by the refusal: both storms are still there for a person to choose
    # between, which is the only place that decision belongs.
    assert connection.execute("select count(*) from scenarios").fetchone()[0] == 2


def test_the_round_trip_keeps_every_row_and_the_endpoint_still_works(
    client, accounts, application
):
    """A rollback that silently emptied a table would be an ops procedure undoing the product.
    And the database is still one a storm can be loaded into afterwards, not merely read from.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    counted = {
        table: connection.execute(f"select count(*) from {table}").fetchone()[0]
        for table in ("scenarios", "assets", "risk_scores", "decision_records")
    }
    assert all(counted.values()), f"a table is empty, so 'nothing was lost' is vacuous: {counted}"

    roll_back(connection)
    roll_forward(connection)

    assert {
        table: connection.execute(f"select count(*) from {table}").fetchone()[0]
        for table in counted
    } == counted
    assert set(IDENTITY) <= triggers(connection)
    append_only_still_refuses(connection)
    listed = client.get("/api/v1/scenarios")
    assert listed.status_code == 200, listed.text
    assert [item["source_note"] for item in listed.json()["items"]] == ["NOAA 2024 replay pack"]
