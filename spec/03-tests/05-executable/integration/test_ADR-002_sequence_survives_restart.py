"""ADR-002 — "the database owns everything durable. Nothing that matters lives in process
memory, so a restart is not an incident." CHG-018, TASK-005 done criterion 12.

**The order the board is read in is durable state, and nothing was asserting it across a
restart.** CHG-018 gave `repair_jobs`, `damage_reports` and `decision_records` a monotonic
`unique` `seq` and made every chronological read order by it, and `store/dispatch.py` calls
that history *"the order it happened, not a view of it"*. Every test that asserted the order
built **one** application.

The mutation that found the gap: hold the sequence beside the connection —
`_SEQ[(id(connection), table)] += 1` — instead of taking it from the table inside the insert.
That is the obvious way to write a counter, it is indistinguishable inside one process, and
**all 264 tests passed with it in place**. A second application over the same database file
then cannot file a damage report at all: the counter restarts at 1, `unique (seq)` refuses the
row, and the dispatcher gets `500 internal_error` for the first thing they type after a
restart — during the storm, on the screen this task exists to provide.

`AGENT.md`'s second lessons row already said what was owed here, and `conftest.build_application`
was written for it at TASK-001's review. This file is that row applied to the state TASK-005
introduced. Nothing in it is about sessions; that half is
`test_ADR-002_session_survives_restart.py`.
"""

import hashlib

from conftest import USER_PASSWORD, build_application, sign_in
from fastapi.testclient import TestClient


def an_account(application):
    """Created once, on the first application. The second one finds it in the same file, which
    is the property under test wearing its smallest coat."""
    from app.store import users

    existing = application.state.db.execute(
        "select id from users where email = 'user@sgw.example'"
    ).fetchone()
    if existing:
        return existing["id"]
    return users.create_user(
        application.state.db,
        name="Dispatcher",
        email="user@sgw.example",
        password=USER_PASSWORD,
        role="operator",
    )


def signed_in_client(application):
    an_account(application)
    client = TestClient(application)
    assert sign_in(client, "user@sgw.example", USER_PASSWORD).status_code == 201
    return client


def a_storm(application, scenario_id="SC-restart"):
    application.state.db.execute(
        # `content_key` and `seq` are required by migration 013: a storm is identified by what
        # it was loaded from, and has a place in the order storms are listed in (CHG-031,
        # CHG-032). A direct insert has to satisfy the store like any other. The key is derived
        # from the id so that a second application over the same file finds the same storm
        # rather than a rival copy — which is this file's whole subject, one table over.
        "insert into scenarios (id, name, source_note, content_key, loaded_by, loaded_at,"
        " forecast_revision, seq)"
        " values (?, 'Restart storm', 'restart', ?, ?, '2026-08-16T00:00:00Z', 0, 900)",
        (scenario_id, hashlib.sha256(scenario_id.encode()).hexdigest(), an_account(application)),
    )
    application.state.db.commit()
    return scenario_id


def file_report(client, scenario_id, neighbourhood):
    return client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": neighbourhood}
    )


def test_a_damage_report_can_still_be_filed_after_a_restart(tmp_path, monkeypatch):
    """The failure the mutation produces, asserted as the dispatcher would meet it: the first
    thing typed after the service comes back."""
    database = tmp_path / "sequence.db"

    before = build_application(monkeypatch, database)
    first = signed_in_client(before)
    scenario_id = a_storm(before)
    assert file_report(first, scenario_id, "Northgate").status_code == 201
    before.state.db.close()  # the restart

    after = build_application(monkeypatch, database)
    second = signed_in_client(after)

    filed = file_report(second, scenario_id, "Harbour West")

    assert filed.status_code == 201, filed.text
    assert after.state.db.execute(
        "select count(*) from damage_reports where scenario_id = ?", (scenario_id,)
    ).fetchone()[0] == 2


def test_the_board_order_is_the_order_it_happened_across_the_restart(tmp_path, monkeypatch):
    """`seq` is the history, so work filed before the restart stays above work filed after it —
    and the sequence carries on rather than starting again."""
    database = tmp_path / "sequence.db"
    before_places = ["Northgate", "Harbour West", "Saltmarsh"]
    after_places = ["Old Quay", "Fen End"]

    before = build_application(monkeypatch, database)
    first = signed_in_client(before)
    scenario_id = a_storm(before)
    for place in before_places:
        assert file_report(first, scenario_id, place).status_code == 201
    highest = before.state.db.execute("select max(seq) from repair_jobs").fetchone()[0]
    before.state.db.close()

    after = build_application(monkeypatch, database)
    second = signed_in_client(after)
    for place in after_places:
        assert file_report(second, scenario_id, place).status_code == 201

    board = second.get(f"/api/v1/scenarios/{scenario_id}/jobs").json()

    assert [item["location"]["neighbourhood"] for item in board["items"]] == (
        before_places + after_places
    )
    # The guard beside it: the numbers themselves kept going up rather than the list merely
    # happening to come back in insertion order.
    assert after.state.db.execute("select min(seq) from repair_jobs").fetchone()[0] == 1
    assert after.state.db.execute("select max(seq) from repair_jobs").fetchone()[0] == highest + 2
    assert after.state.db.execute(
        "select count(distinct seq) from damage_reports"
    ).fetchone()[0] == len(before_places) + len(after_places)


def test_the_decision_record_sequence_survives_the_restart_too(tmp_path, monkeypatch):
    """The older half of CHG-018, and the one that carries regulatory evidence.
    `decision_records.read_all` claims *"the order **is** the history, not a view of it"* — a
    claim about a durable table, asserted here across two processes.

    `store/decisions.py` takes its sequence the same way `store/dispatch.py` does, so the same
    mutation breaks both; this is the table where a wrong order records a decision against a
    recommendation nobody was shown.
    """
    from app.store import decisions

    database = tmp_path / "sequence.db"

    before = build_application(monkeypatch, database)
    a_storm(before)
    for revision in (0, 1):
        decisions.append_recommendation(
            before.state.db,
            scenario_id="SC-restart",
            forecast_revision=revision,
            payload={"revision": revision},
        )
    before.state.db.close()

    after = build_application(monkeypatch, database)
    for revision in (2, 3):
        decisions.append_recommendation(
            after.state.db,
            scenario_id="SC-restart",
            forecast_revision=revision,
            payload={"revision": revision},
        )

    rows = decisions.read_all(after.state.db, "SC-restart")

    assert [row["payload"] for row in rows] == [
        '{"revision": 0}',
        '{"revision": 1}',
        '{"revision": 2}',
        '{"revision": 3}',
    ]
    assert [row["seq"] for row in rows] == [1, 2, 3, 4]
