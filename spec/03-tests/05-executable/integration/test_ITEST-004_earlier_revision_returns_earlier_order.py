"""ITEST-004 — REQ-F-004. Defined in `03-tests/02-functional/integration-tests.md`.

    Integration point:  API + database
    Scenario:           request `forecast_revision=0` after revision 1 has been written
    Expected result:    200, returning the revision-0 order unchanged
    Side effect:        **no write of any kind**; revision 1 still current

`test-specification.md` names the failure: *"a silent fallback to the current revision."* That
is the dangerous one — it shows one ranking to a reader who believes they are looking at
another — so the unknown-revision case is here beside the known one.

**The side-effect assertion is a dump of every row of every table**, before and after the read,
rather than a count of the two tables the author happened to think of. `integration-tests.md`
is explicit that the side effect is the assertion that catches a handler which returns the
right status after it has already written.

**One column is excluded, and naming it is the point of doing so.** `sessions.last_seen_at` is
written by every authenticated request: ADR-006 measures the 240-minute idle limit from it, and
a read that did not touch it would be a session that expired while somebody was using it. So
this test asserts *no write except the session heartbeat every request performs by design*, and
`test_the_dump_notices_a_write_when_one_happens` is the positive assertion beside it — without
that, a dump that had stopped returning rows would satisfy every comparison here.
"""

from conftest import fixture_files, sign_in

FIXTURE = "storm-with-a-forecast-change"

# Written by every authenticated request, by design (ADR-006). Excluded by name, not by a
# blanket, so a table that starts moving for a different reason still fails this test.
HEARTBEAT_TABLE = "sessions"


def load(client, accounts) -> str:
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Track shift", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files(FIXTURE).items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


def dump(connection) -> dict[str, list[tuple]]:
    """Every row of every table. "Nothing was written" is a claim about the database."""
    names = [
        row["name"]
        for row in connection.execute(
            "select name from sqlite_master where type = 'table'"
            " and name not like 'sqlite_%' order by name"
        )
    ]
    return {
        name: [tuple(row) for row in connection.execute(f"select * from {name}")]
        for name in names
    }


def assert_only_the_heartbeat_moved(before, after) -> None:
    assert set(before) == set(after), "a table appeared or vanished"
    for table, rows in before.items():
        if table == HEARTBEAT_TABLE:
            continue
        assert after[table] == rows, f"{table} was written to"


def at_revision_one(client, accounts):
    """The realistic flow: read the ranking, apply the change, read the new ranking. Both
    deliveries have already recorded their `recommendation` row (FF-005) by the time the
    comparison below happens, which is what makes *no write of any kind* exact rather than
    approximately true."""
    scenario_id = load(client, accounts)
    before = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    applied = client.post(f"/api/v1/scenarios/{scenario_id}/forecast-revisions")
    assert applied.status_code == 201, applied.text
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")
    return scenario_id, before


def test_the_earlier_revision_returns_the_earlier_order_unchanged(client, accounts):
    scenario_id, before = at_revision_one(client, accounts)

    recalled = client.get(f"/api/v1/scenarios/{scenario_id}/risks?forecast_revision=0")

    assert recalled.status_code == 200, recalled.text
    body = recalled.json()
    assert body["forecast_revision"] == 0
    assert body["items"] == before["items"]
    assert body["total"] == before["total"]
    assert body["computed_at"] == before["computed_at"]
    assert body["recommendation_id"] == before["recommendation_id"]


def test_reading_the_earlier_revision_writes_nothing(client, accounts, application):
    scenario_id, _ = at_revision_one(client, accounts)
    connection = application.state.db
    before = dump(connection)
    # The haystack, before anything is said about the needle.
    assert before["risk_scores"], "no rankings are stored, so 'unchanged' proves nothing"
    assert before["decision_records"], "no recommendation is stored"
    assert {"scenarios", "assets", "risk_scores", "decision_records"} <= set(before)

    read = client.get(f"/api/v1/scenarios/{scenario_id}/risks?forecast_revision=0")

    assert read.status_code == 200
    assert_only_the_heartbeat_moved(before, dump(connection))


def test_the_dump_notices_a_write_when_one_happens(client, accounts, application):
    """The positive assertion beside the negative one: an enumeration that returned nothing
    would satisfy the comparison above and prove nothing at all."""
    scenario_id, _ = at_revision_one(client, accounts)
    connection = application.state.db
    before = dump(connection)

    filed = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Northgate"}
    )

    assert filed.status_code == 201, filed.text
    after = dump(connection)
    assert after != before
    assert len(after["damage_reports"]) == len(before["damage_reports"]) + 1


def test_revision_one_is_still_current_after_the_earlier_one_is_read(client, accounts):
    scenario_id, _ = at_revision_one(client, accounts)

    client.get(f"/api/v1/scenarios/{scenario_id}/risks?forecast_revision=0")

    scenario = client.get(f"/api/v1/scenarios/{scenario_id}").json()
    assert scenario["forecast_revision"] == 1
    # And the default read — no parameter — is still the current revision, not the one just
    # asked for. A handler that remembered would be the silent fallback wearing a cache.
    assert client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()["forecast_revision"] == 1


def test_an_unknown_revision_is_refused_rather_than_silently_replaced(
    client, accounts, application
):
    """The failure this test exists for. A 200 carrying revision 1's list would look correct
    on every screen and be a different storm's advice."""
    scenario_id, _ = at_revision_one(client, accounts)
    connection = application.state.db
    before = dump(connection)

    response = client.get(f"/api/v1/scenarios/{scenario_id}/risks?forecast_revision=9")

    assert response.status_code == 404
    assert set(response.json()) == {"code", "message"}
    assert_only_the_heartbeat_moved(before, dump(connection))


def test_a_non_integer_revision_is_a_validation_error(client, accounts):
    """`technical-spec.md` §7.3: `400` for a non-integer, `404` for an unknown revision."""
    scenario_id, _ = at_revision_one(client, accounts)

    response = client.get(f"/api/v1/scenarios/{scenario_id}/risks?forecast_revision=soon")

    assert response.status_code == 400
    assert set(response.json()) == {"code", "message"}


def test_the_scenario_lists_the_revisions_that_exist(client, accounts):
    """`ForecastRevisionControl` needs *current and available revisions*, and a control that
    guessed the range would offer a revision the storm does not carry."""
    scenario_id, _ = at_revision_one(client, accounts)

    scenario = client.get(f"/api/v1/scenarios/{scenario_id}").json()

    assert [entry["forecast_revision"] for entry in scenario["forecast_revisions"]] == [0, 1, 2]
    assert scenario["forecast_revisions"][1]["valid_time"] == "2026-08-15T06:00:00Z"
    assert scenario["next_forecast_revision"] == 2


def test_a_forecast_the_file_carries_is_not_the_same_as_a_revision_that_can_be_read(
    client, accounts
):
    """CHG-027, and the defect it was raised for.

    The series is a property of the prepared **file** and is complete the moment the storm is
    loaded; a ranking exists only where somebody has applied one. Nothing in this response
    distinguished the two, so `ForecastRevisionControl` drew one selectable button per entry —
    and pressing an unapplied one asked `GET /risks?forecast_revision=2` for a ranking that had
    never been computed. The 404 below is *correct* (§7.3 forbids a silent fallback), which is
    exactly why the control must not offer the action: the screen it produced showed no ranking,
    no asset table, and accept / change / reject beside a list that was not there.

    **Both halves are asserted, and the pair is the point** — a response that reported every
    revision as unranked would satisfy the negative half on its own.
    """
    scenario_id = load(client, accounts)

    fresh = client.get(f"/api/v1/scenarios/{scenario_id}").json()["forecast_revisions"]
    assert [entry["forecast_revision"] for entry in fresh] == [0, 1, 2]
    assert [entry["ranked"] for entry in fresh] == [True, False, False]
    # And the entries that say `false` say it truthfully: reading one is a 404.
    unranked = client.get(f"/api/v1/scenarios/{scenario_id}/risks?forecast_revision=2")
    assert unranked.status_code == 404
    # The haystack: the entry that says `true` is readable, so `false` means something.
    readable = client.get(f"/api/v1/scenarios/{scenario_id}/risks?forecast_revision=0")
    assert readable.status_code == 200

    applied = client.post(f"/api/v1/scenarios/{scenario_id}/forecast-revisions")
    assert applied.status_code == 201, applied.text

    after = client.get(f"/api/v1/scenarios/{scenario_id}").json()["forecast_revisions"]
    assert [entry["ranked"] for entry in after] == [True, True, False]
    assert client.get(
        f"/api/v1/scenarios/{scenario_id}/risks?forecast_revision=1"
    ).status_code == 200


def test_ranked_is_read_from_the_stored_rankings_and_not_from_the_pointer(
    client, accounts, application
):
    """The pointer is one number; the rankings are the fact, and the two can disagree.

    A `forecast_revision` moved directly to a revision nothing ranked leaves the default
    `GET /risks` answering 404 while the scenario response still reads *current*. Deriving
    `ranked` from `scenario_id`'s pointer — `entry <= current`, the cheap implementation —
    would have the control offer that revision and every one below it. Asserted against a state
    reached by a **direct** statement, because that is the only way to make the two disagree.
    """
    connection = application.state.db
    scenario_id = load(client, accounts)
    connection.execute(
        "update scenarios set forecast_revision = 2 where id = ?", (scenario_id,)
    )
    connection.commit()

    entries = client.get(f"/api/v1/scenarios/{scenario_id}").json()["forecast_revisions"]

    assert [entry["ranked"] for entry in entries] == [True, False, False]
    assert client.get(f"/api/v1/scenarios/{scenario_id}/risks").status_code == 404
