"""ATEST-005 — REQ-F-004, AC-005. Defined in `03-tests/02-functional/acceptance-tests.md`.

**Given** a ranked list and a forecast change inside the scenario, **when** the change is
applied, **then** the list re-ranks and the previous order remains retrievable for comparison.

`test-specification.md` names the failure this test exists to catch in one line: *"a re-rank
destroying the order a decision was made against."* So the second half is asserted harder than
the first — an implementation that overwrote revision n in place would satisfy "the list
re-ranks" completely, and every screen would look right.

The fixture is built so the re-rank has exactly one cause. `SS-ALPHA` and `SS-BRAVO` are
**identical in every scored factor** — same type, same install year, same flood zone, same
condition rating on the same date — and differ only in which forecast grid cell they sit in. So
when they swap places, the forecast is the only thing that can have moved them, and a mutation
that ranks by anything else cannot produce the swap by accident.

Three forecasts, six hours apart:

    revision 0  2026-08-15T00:00Z   GC-A 120 mph, GC-B  70 mph   -> ALPHA above BRAVO
    revision 1  2026-08-15T06:00Z   GC-A  60 mph, GC-B 128 mph   -> BRAVO above ALPHA
    revision 2  2026-08-15T12:00Z   GC-A 132 mph, GC-B  55 mph   -> ALPHA above BRAVO again

Revision 2 carries rows for two cells only, so `GC-C`, `GC-D` and `GC-E` keep the value they
were last issued — which is asserted, with the `valid_time` that says the value is six hours
old rather than current.
"""

import sqlite3

import pytest
from conftest import build_application, fixture_files, sign_in
from fastapi.testclient import TestClient

FIXTURE = "storm-with-a-forecast-change"

ALPHA, BRAVO, CHARLIE, DELTA, ECHO = (
    "SS-ALPHA",
    "SS-BRAVO",
    "LN-CHARLIE",
    "PS-DELTA",
    "PL-ECHO",
)

REVISION_0_AT = "2026-08-15T00:00:00Z"
REVISION_1_AT = "2026-08-15T06:00:00Z"
REVISION_2_AT = "2026-08-15T12:00:00Z"


def load(client, accounts) -> str:
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Track shift", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files(FIXTURE).items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


def ranking(client, scenario_id, revision=None) -> dict:
    query = "" if revision is None else f"?forecast_revision={revision}"
    response = client.get(f"/api/v1/scenarios/{scenario_id}/risks{query}")
    assert response.status_code == 200, response.text
    return response.json()


def order(body) -> list[str]:
    """The codes, top to bottom. The unscored ones are in the list and carry no rank."""
    return [item["external_ids"][0] for item in body["items"]]


def find(body, code) -> dict:
    matched = [item for item in body["items"] if code in item["external_ids"]]
    assert len(matched) == 1, f"{code} appears {len(matched)} times in the ranking"
    return matched[0]


def apply_next(client, scenario_id):
    return client.post(f"/api/v1/scenarios/{scenario_id}/forecast-revisions")


def gust_of(item) -> dict:
    values = [value for value in item["values"] if value["name"] == "wind_gust_mph"]
    assert len(values) == 1
    return values[0]


def stored_scores(connection, scenario_id, revision) -> list[tuple]:
    return [
        tuple(row)
        for row in connection.execute(
            "select * from risk_scores where scenario_id = ? and forecast_revision = ?"
            " order by id",
            (scenario_id, revision),
        )
    ]


@pytest.fixture
def storm(client, accounts):
    return load(client, accounts)


# --- The first half: the list re-ranks ---------------------------------------------------


def test_applying_the_forecast_change_writes_the_next_revision(client, storm):
    before = ranking(client, storm)
    assert before["forecast_revision"] == 0

    applied = apply_next(client, storm)

    assert applied.status_code == 201, applied.text
    body = applied.json()
    assert body["forecast_revision"] == 1
    assert body["previous_forecast_revision"] == 0
    assert body["valid_time"] == REVISION_1_AT
    # Nobody is dropped by a re-rank. An asset missing from a ranking is the most dangerous
    # screen in this product, and a re-rank is the cheapest place to lose one.
    assert body["ranked"] + body["unscored"] == len(before["items"])


def test_the_list_reranks_and_the_forecast_is_what_moved_it(client, storm):
    """ALPHA and BRAVO differ in nothing but their grid cell, so this swap has one cause."""
    before = ranking(client, storm)
    assert order(before).index(ALPHA) < order(before).index(BRAVO)

    assert apply_next(client, storm).status_code == 201
    after = ranking(client, storm)

    assert after["forecast_revision"] == 1
    assert order(after).index(BRAVO) < order(after).index(ALPHA)
    # The same storm, re-ordered — not a different set of assets.
    assert sorted(order(after)) == sorted(order(before))


def test_the_reranked_scores_move_in_the_direction_the_forecast_did(client, storm):
    before = ranking(client, storm)
    assert apply_next(client, storm).status_code == 201
    after = ranking(client, storm)

    assert find(after, BRAVO)["score"] > find(before, BRAVO)["score"]
    assert find(after, ALPHA)["score"] < find(before, ALPHA)["score"]


# --- The second half, and the one the risk note names ------------------------------------


def test_the_previous_order_stays_retrievable_for_comparison(client, storm):
    """AC-005's *retrievable for comparison*: the earlier ranking comes back whole."""
    before = ranking(client, storm)

    assert apply_next(client, storm).status_code == 201
    recalled = ranking(client, storm, revision=0)

    assert recalled["forecast_revision"] == 0
    assert recalled["items"] == before["items"]
    assert recalled["computed_at"] == before["computed_at"]
    # A comparison needs two different things to compare, or the assertion above holds
    # because nothing happened.
    assert order(ranking(client, storm)) != order(recalled)


def test_the_earlier_revisions_stored_rows_are_never_rewritten(client, storm, application):
    """Asserted against the stored rows, not the response: a handler that re-read the rows it
    had just overwritten would satisfy every assertion above."""
    connection = application.state.db
    ranking(client, storm)
    before = stored_scores(connection, storm, 0)
    assert before, "no revision-0 rows exist, so 'unchanged' would be vacuous"

    assert apply_next(client, storm).status_code == 201

    assert stored_scores(connection, storm, 0) == before
    assert stored_scores(connection, storm, 1), "revision 1 was not written"


def test_the_database_refuses_an_update_to_a_stored_ranking(client, storm, application):
    """CHG-026, and this is the store-level half of *never rewrites n*.

    The rule is asserted the way STEST-008 asserts BR-004 — by issuing the statement against
    the database and requiring the refusal — because a service that declines to write is a
    service that can be refactored. Every constraint the store can express belongs to the
    store (ADR-002).

    **This test was wrong when it was first written, and the mutation is what said so.** It
    set `score = 0.0` across the whole revision, which includes the UNSCORED row — and that
    is refused by BR-002's `json_array_length(reasons) >= 1 or score is null` whether this
    trigger exists or not. With the trigger removed the statement still raised, still an
    `IntegrityError`, and the test still passed: an assertion that could not fail for the
    reason it claimed. So it now names a **scored** row, and requires the refusal to be
    *this* rule by reading it out of the message.
    """
    connection = application.state.db
    ranking(client, storm)
    assert apply_next(client, storm).status_code == 201
    before = stored_scores(connection, storm, 0)
    assert before

    scored = connection.execute(
        "select id from risk_scores where scenario_id = ? and forecast_revision = 0"
        " and score is not null limit 1",
        (storm,),
    ).fetchone()
    assert scored is not None, "no scored row to attempt an UPDATE on"

    with pytest.raises(sqlite3.IntegrityError) as refused:
        connection.execute("update risk_scores set rank = 1 where id = ?", (scored["id"],))
        connection.commit()
    connection.rollback()

    assert "never rewritten" in str(refused.value), (
        f"refused by something else: {refused.value}"
    )
    assert stored_scores(connection, storm, 0) == before
    # The haystack: this connection can write, and it is `risk_scores` in particular that it
    # cannot rewrite. Without this the refusal above could be a read-only database.
    connection.execute("update scenarios set name = ? where id = ?", ("Renamed", storm))
    connection.commit()
    assert client.get(f"/api/v1/scenarios/{storm}").json()["name"] == "Renamed"


def test_the_database_refuses_a_second_ranking_for_one_revision(application, client, storm):
    """`unique (scenario_id, asset_id, forecast_revision)` is the rule `database-design.md` §3
    puts against REQ-F-004, so a re-run cannot produce two rankings for one revision
    (`reliability-specification.md`). Issued directly, not through the endpoint."""
    connection = application.state.db
    ranking(client, storm)
    existing = connection.execute(
        "select * from risk_scores where scenario_id = ? and forecast_revision = 0 limit 1",
        (storm,),
    ).fetchone()
    assert existing is not None

    insert = (
        "insert into risk_scores (id, scenario_id, asset_id, forecast_revision, score, band,"
        " rank, reasons, unscored_reason, weight_set_version, computed_at)"
        " values (?, ?, ?, ?, 99.0, 'High', 1, '[\"rival\"]', null, 'x', '2026-08-16T00:00:00Z')"
    )

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(insert, ("RS-rival", storm, existing["asset_id"], 0))
        connection.commit()
    connection.rollback()

    # The haystack: the same statement at a revision nothing has claimed is accepted, so the
    # refusal above is the constraint rather than a malformed insert.
    connection.execute(insert, ("RS-rival", storm, existing["asset_id"], 99))
    connection.commit()


# --- More than one change, and the end of the series -------------------------------------


def test_a_second_change_writes_a_third_revision_and_both_earlier_orders_survive(client, storm):
    at_zero = order(ranking(client, storm))

    assert apply_next(client, storm).status_code == 201
    at_one = order(ranking(client, storm))
    applied = apply_next(client, storm)

    assert applied.status_code == 201, applied.text
    assert applied.json()["forecast_revision"] == 2
    assert applied.json()["valid_time"] == REVISION_2_AT

    assert order(ranking(client, storm, revision=0)) == at_zero
    assert order(ranking(client, storm, revision=1)) == at_one
    at_two = order(ranking(client, storm, revision=2))
    assert at_two.index(ALPHA) < at_two.index(BRAVO)
    assert at_two != at_one


def test_applying_when_the_storm_carries_no_further_forecast_is_refused(
    client, storm, application
):
    """Three forecasts, so the third apply has nothing to apply. Refused, and nothing written —
    not a fourth revision that repeats the third, which would be a ranking nobody's data
    supports."""
    connection = application.state.db
    for _ in range(2):
        assert apply_next(client, storm).status_code == 201
    rows_before = connection.execute("select count(*) from risk_scores").fetchone()[0]

    refused = apply_next(client, storm)

    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "no_further_forecast"
    assert "2" in refused.json()["message"]
    assert connection.execute("select count(*) from risk_scores").fetchone()[0] == rows_before
    assert client.get(f"/api/v1/scenarios/{storm}").json()["forecast_revision"] == 2


def test_an_unknown_storm_is_a_404_from_this_endpoint(client, accounts):
    """The body is asserted, not only the status: an endpoint that does not exist also answers
    404, with FastAPI's `{"detail": ...}`, and this test would pass against nothing at all."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])

    response = apply_next(client, "SC-nothing")

    assert response.status_code == 404
    assert set(response.json()) == {"code", "message"}
    assert response.json()["code"] == "not_found"


def test_either_role_may_apply_a_forecast_change(client, accounts):
    """`technical-spec.md` §7.2 and `security-specification.md` §2 both allow it to both roles.
    Re-ranking is the product, not an administrative action."""
    scenario_id = load(client, accounts)
    client.delete("/api/v1/auth/session")
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])

    assert apply_next(client, scenario_id).status_code == 201


# --- What each revision says about itself -------------------------------------------------


def test_each_revision_shows_the_forecast_it_was_computed_from(client, storm):
    """BR-003, at the place it is easiest to break: a rank that moved while the number beside
    it did not is a screen that cannot be questioned."""
    at_zero = ranking(client, storm)
    alpha_at_zero = gust_of(find(at_zero, ALPHA))
    assert alpha_at_zero["value"] == 120
    assert alpha_at_zero["observed_at"] == REVISION_0_AT
    assert find(at_zero, ALPHA)["reasons"][0]["detail"].startswith(
        "Forecast winds of 120 mph come close to the 130 mph"
    )

    assert apply_next(client, storm).status_code == 201
    at_one = ranking(client, storm)

    bravo_at_one = gust_of(find(at_one, BRAVO))
    assert bravo_at_one["value"] == 128
    assert bravo_at_one["observed_at"] == REVISION_1_AT
    assert find(at_one, BRAVO)["reasons"][0]["detail"].startswith(
        "Forecast winds of 128 mph come close to the 130 mph"
    )
    # And the earlier revision still says what it always said.
    assert gust_of(find(ranking(client, storm, revision=0), ALPHA))["value"] == 120


def test_a_cell_with_no_new_row_keeps_its_last_forecast_and_says_how_old_it_is(client, storm):
    """Revision 2 carries `GC-A` and `GC-B` only. `GC-C` is not blanked — a forecast grid that
    goes quiet has not stopped forecasting — and it does not silently claim to be current
    either: the value keeps the `valid_time` it was issued at."""
    for _ in range(2):
        assert apply_next(client, storm).status_code == 201

    charlie = find(ranking(client, storm, revision=2), CHARLIE)

    assert charlie["score"] is not None
    assert gust_of(charlie)["value"] == 60
    assert gust_of(charlie)["observed_at"] == REVISION_1_AT
    assert gust_of(find(ranking(client, storm, revision=2), ALPHA))["observed_at"] == REVISION_2_AT


def test_an_unscorable_asset_stays_present_and_unranked_at_every_revision(client, storm):
    """A re-rank is the cheapest place to quietly drop the asset nobody can score."""
    for revision in (0, 1, 2):
        if revision:
            assert apply_next(client, storm).status_code == 201
        echo = find(ranking(client, storm, revision=revision), ECHO)
        assert echo["score"] is None
        assert echo["rank"] is None
        assert echo["unscored_reason"]
        assert order(ranking(client, storm, revision=revision))[-1] == ECHO


def test_every_asset_is_ranked_again_rather_than_only_the_ones_whose_cell_moved(client, storm):
    """`GC-D`'s gust also changes between revision 0 and revision 1, and DELTA's score has to
    move with it — a re-rank that only rewrote the two cells someone was looking at would pass
    every ALPHA/BRAVO assertion above."""
    before = ranking(client, storm)
    assert apply_next(client, storm).status_code == 201
    after = ranking(client, storm)

    assert find(after, DELTA)["score"] != find(before, DELTA)["score"]
    assert find(after, CHARLIE)["score"] != find(before, CHARLIE)["score"]
    assert len(after["items"]) == len(before["items"])


def test_each_delivered_revision_is_recorded_as_its_own_recommendation(
    client, storm, application
):
    """REQ-F-009 across a re-rank: what was shown at each revision must be reconstructable, so
    a decision taken against revision 0 keeps pointing at revision 0's list (FF-005)."""
    connection = application.state.db
    first = ranking(client, storm)["recommendation_id"]

    assert apply_next(client, storm).status_code == 201
    second = ranking(client, storm)["recommendation_id"]
    # Re-reading is the same recommendation, not a new one.
    assert ranking(client, storm, revision=0)["recommendation_id"] == first

    assert first != second
    subjects = [
        row["subject_id"]
        for row in connection.execute(
            "select subject_id from decision_records where scenario_id = ?"
            " and kind = 'recommendation' order by seq",
            (storm,),
        )
    ]
    assert subjects == [f"{storm}:0", f"{storm}:1"]


def test_applying_a_forecast_change_records_no_decision_and_moves_no_crew(
    client, storm, application
):
    """BR-001. Applying a revision is a ranking, and a ranking is advice.

    It is deliberately **not** a `decision_records` row: `kind` is a closed enumeration and
    none of its six values is this one, the ranking it produces gets its `recommendation` row
    when it is delivered, and inventing a seventh kind would be a schema decision this task
    does not own.
    """
    connection = application.state.db
    ranking(client, storm)
    before = connection.execute("select count(*) from decision_records").fetchone()[0]
    assert before == 1

    assert apply_next(client, storm).status_code == 201

    assert connection.execute("select count(*) from decision_records").fetchone()[0] == before
    assert connection.execute("select count(*) from repair_jobs").fetchone()[0] == 0
    assert connection.execute("select count(*) from damage_reports").fetchone()[0] == 0


# --- The durable half -----------------------------------------------------------------------


def test_the_revision_and_its_forecasts_survive_a_restart(tmp_path, monkeypatch):
    """`AGENT.md`: when a task introduces durable state, the restart test is part of the task.

    The forecast series and the revision pointer are that state. A series held in process
    memory, or a pointer counted up from zero, is indistinguishable inside one process and
    re-applies revision 1 over the top of itself after a restart.
    """
    from app.store import users

    database = tmp_path / "forecasts.db"

    before = build_application(monkeypatch, database)
    users.create_user(
        before.state.db,
        name="Ops Manager",
        email="admin@sgw.example",
        password="correct-horse-battery-staple",
        role="admin",
    )
    first = TestClient(before)
    sign_in(first, "admin@sgw.example", "correct-horse-battery-staple")
    created = first.post(
        "/api/v1/scenarios",
        data={"name": "Track shift", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files(FIXTURE).items()],
    )
    scenario_id = created.json()["scenario_id"]
    at_zero = order(ranking(first, scenario_id))
    assert apply_next(first, scenario_id).status_code == 201
    at_one = order(ranking(first, scenario_id))
    before.state.db.close()  # the restart

    after = build_application(monkeypatch, database)
    second = TestClient(after)
    sign_in(second, "admin@sgw.example", "correct-horse-battery-staple")

    assert order(ranking(second, scenario_id, revision=0)) == at_zero
    assert order(ranking(second, scenario_id, revision=1)) == at_one
    # The pointer carried on rather than starting again: the next apply is revision 2.
    applied = apply_next(second, scenario_id)
    assert applied.status_code == 201, applied.text
    assert applied.json()["forecast_revision"] == 2
    assert applied.json()["previous_forecast_revision"] == 1
