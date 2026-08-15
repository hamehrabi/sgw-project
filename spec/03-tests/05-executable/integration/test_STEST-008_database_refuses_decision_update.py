"""STEST-008 — SEC-Z-004, REQ-R-002, BR-004. Defined in `security-tests.md`.
Also ATEST-008 — AC-008: a row is appended, and no path exists to edit or remove it.

Issue an `UPDATE` and a `DELETE` against `decision_records` **directly against the database**,
as the application runs. Both must be refused **by the database** — ADR-004's triggers — not by
the application. Row unchanged, byte for byte.

`executable-tests.md` names this test as sitting deliberately below the application, and says
why: it is easy to "fix" into an application-level check that passes and proves nothing. A
service-layer rule is removed by the first refactor with every functional test still green.
That is exactly what happened to BR-004's original enforcement when ADR-002 removed the role
system, and ADR-004 exists because of it.
"""

import sqlite3

import pytest
from conftest import fixture_files, sign_in


def loaded(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    scenario_id = created.json()["scenario_id"]
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")  # delivering appends a recommendation
    return scenario_id


def test_both_triggers_exist(client, application, accounts):
    loaded(client, accounts)

    triggers = {
        row["name"]
        for row in application.state.db.execute(
            "select name from sqlite_master where type = 'trigger'"
        )
    }

    assert {"decision_records_no_update", "decision_records_no_delete"} <= triggers


def test_the_database_refuses_an_update(client, application, accounts):
    loaded(client, accounts)
    connection = application.state.db
    before = connection.execute("select * from decision_records limit 1").fetchone()
    assert before is not None, "delivering a ranking must have appended a recommendation"

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "update decision_records set payload = '{\"tampered\":true}' where id = ?",
            (before["id"],),
        )
        connection.commit()

    after = connection.execute(
        "select * from decision_records where id = ?", (before["id"],)
    ).fetchone()
    assert dict(after) == dict(before), "the row must be unchanged, byte for byte"


def test_the_database_refuses_a_delete(client, application, accounts):
    loaded(client, accounts)
    connection = application.state.db
    before = connection.execute("select count(*) from decision_records").fetchone()[0]

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("delete from decision_records")
        connection.commit()

    assert connection.execute("select count(*) from decision_records").fetchone()[0] == before


def test_the_refusal_names_the_rule(client, application, accounts):
    """An operator or an engineer hitting this should be told which rule they met."""
    loaded(client, accounts)

    with pytest.raises(sqlite3.IntegrityError) as raised:
        application.state.db.execute("delete from decision_records")

    assert "append-only" in str(raised.value)
    assert "BR-004" in str(raised.value)


def test_no_role_may_edit_it_including_an_admin(client, application, accounts):
    """SEC-Z-004: the two rows in the RBAC table where the answer is no for *every* role.

    Enforced structurally rather than by a permission check — there is no endpoint to guard,
    because there is no code path that issues the statement.
    """
    loaded(client, accounts)

    with pytest.raises(sqlite3.IntegrityError):
        application.state.db.execute(
            "update decision_records set actor_user_id = ?", (accounts["admin"]["id"],)
        )
