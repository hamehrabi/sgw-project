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


def load_a_different_storm(client) -> str:
    """A second, genuinely different scenario. Re-uploading the same files resolves to the same
    storm (§5, replace in place), so a cross-storm test needs different bytes."""
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


# One insert, reused by every direct-against-the-database case below, so the refusals and the
# permitted cases differ in exactly the column the rule is about and in nothing else.
RIVAL_INSERT = (
    "insert into risk_scores (id, scenario_id, asset_id, forecast_revision, score, band,"
    " rank, reasons, unscored_reason, weight_set_version, computed_at)"
    " values (?, ?, ?, ?, 99.0, 'High', 1, '[\"rival\"]', null, 'x', '2026-08-16T00:00:00Z')"
)


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
    #
    # It writes to `assets` rather than to `scenarios.name`, which is what it used to do:
    # migration 013 fixes a loaded storm's identity at load (CHG-031), so a rename is now
    # refused too — and a haystack that has itself become a needle proves nothing about the
    # needle beside it.
    an_asset = connection.execute(
        "select id from assets where scenario_id = ? limit 1", (storm,)
    ).fetchone()
    assert an_asset is not None, "no asset to attempt a permitted write on"
    connection.execute(
        "update assets set name = ? where id = ?", ("Renamed", an_asset["id"])
    )
    connection.commit()
    assert connection.execute(
        "select name from assets where id = ?", (an_asset["id"],)
    ).fetchone()["name"] == "Renamed"


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

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(RIVAL_INSERT, ("RS-rival", storm, existing["asset_id"], 0))
        connection.commit()
    connection.rollback()

    # The haystack: the same statement at a revision the storm carries and nothing has ranked
    # is accepted, so the refusal above is the constraint rather than a malformed insert.
    connection.execute(RIVAL_INSERT, ("RS-rival", storm, existing["asset_id"], 1))
    connection.commit()


def test_the_database_refuses_a_ranking_at_a_revision_the_storm_does_not_carry(
    application, client, storm
):
    """CHG-028(b), and the invariant `scenario_forecast_cells` was given a migration before the
    table AC-005 is actually about.

    `risk_scores` carried no key at all on `(scenario_id, forecast_revision)`, so a ranking at
    revision 42 of a storm that carries three forecasts was accepted and served with a 200 —
    and `GET /scenarios/{id}` now reports which revisions have an order behind them (CHG-027),
    which makes a ranking of a forecast that does not exist an answer the screen believes.
    Issued directly against the database, with the permitted case beside it.

    The refusal is read out of the message rather than taken as any `IntegrityError`, because
    this insert also has a unique constraint and a foreign key it could plausibly trip: an
    assertion that cannot fail for the reason it claims is the shape this repository keeps
    finding, and CHG-026's own test was the fifth of them.
    """
    connection = application.state.db
    ranking(client, storm)
    asset_id = connection.execute(
        "select asset_id from risk_scores where scenario_id = ? limit 1", (storm,)
    ).fetchone()["asset_id"]

    with pytest.raises(sqlite3.IntegrityError) as refused:
        connection.execute(RIVAL_INSERT, ("RS-nowhere", storm, asset_id, 42))
        connection.commit()
    connection.rollback()
    assert "must name a forecast revision this storm carries" in str(refused.value)

    # The permitted case: revision 2 is a forecast this storm carries, so a row may name it.
    connection.execute(RIVAL_INSERT, ("RS-nowhere", storm, asset_id, 2))
    connection.commit()


def test_the_database_refuses_a_ranking_that_names_another_storms_asset(
    application, client, accounts, storm
):
    """CHG-019's remaining instance, recorded in that entry as knowingly unfixed and closed by
    the rebuild CHG-028 was doing anyway.

    `references assets (id)` proves an asset exists *somewhere*. CLAUDE.md calls a missing scope
    *"a correctness bug — two storms blended into one ranking would look entirely plausible"*,
    and this is the ranking table.
    """
    connection = application.state.db
    ranking(client, storm)
    other = load_a_different_storm(client)
    assert other != storm
    foreign_asset = connection.execute(
        "select id from assets where scenario_id = ? limit 1", (other,)
    ).fetchone()["id"]

    with pytest.raises(sqlite3.IntegrityError) as refused:
        connection.execute(RIVAL_INSERT, ("RS-crossed", storm, foreign_asset, 1))
        connection.commit()
    connection.rollback()
    assert "FOREIGN KEY" in str(refused.value)

    # The same statement against an asset that IS in this storm is accepted.
    own_asset = connection.execute(
        "select id from assets where scenario_id = ? limit 1", (storm,)
    ).fetchone()["id"]
    connection.execute(RIVAL_INSERT, ("RS-crossed", storm, own_asset, 1))
    connection.commit()


def test_the_database_refuses_a_delete_and_reinsert_of_an_earlier_revision(
    application, client, storm
):
    """The half of *never rewrites n* that was not in the schema (CHG-028(a)).

    TASK-006's own Constraints say *"not by `UPDATE`, not by delete-and-reinsert"*, and 010 held
    only the first: `delete from risk_scores where forecast_revision = 0` was accepted, one
    re-insert rewrote revision 0 into a one-row list, and `GET /risks?forecast_revision=0`
    served it with a 200. The order a crew was placed against, changed underneath the decision
    that names it.
    """
    connection = application.state.db
    assert apply_next(client, storm).status_code == 201
    before = stored_scores(connection, storm, 0)
    assert before, "no revision-0 rows exist, so the refusal below would be vacuous"

    with pytest.raises(sqlite3.IntegrityError) as refused:
        connection.execute(
            "delete from risk_scores where scenario_id = ? and forecast_revision = 0", (storm,)
        )
        connection.commit()
    connection.rollback()

    assert "never rewritten" in str(refused.value), (
        f"refused by something else: {refused.value}"
    )
    assert stored_scores(connection, storm, 0) == before
    # And the endpoint still serves the whole of it, which is the shape the review's mutation
    # broke: one re-insert turned revision 0 into a one-row list served with a 200.
    assert len(ranking(client, storm, revision=0)["items"]) == len(before)


def test_deleting_a_whole_storm_still_works_and_takes_its_rankings_with_it(
    application, client, storm
):
    """The operation the delete guard must not break — `technical-spec.md` §7.2's *delete or
    replace a scenario*, and the reason 010 declined an unconditional `before delete` twin.

    A cascade removes the parent row before applying the action to its children, so inside one
    the guard's `when` clause is false and the rows go. **Asserted rather than reasoned about**,
    because an ordering SQLite does not promise is exactly the kind of thing a test should hold
    down: if a future version changes it, this turns red here instead of §7.2 turning red during
    the incident it was meant to end.

    **§7.2 is not built, and two other tables already stand in front of it** — both by decisions
    older than this migration, and both named here so the setup below reads as deliberate rather
    than as convenience. `decision_records.scenario_id` is `references scenarios (id)` with **no**
    cascade (migration 006: *an audit row outlives the storm it describes*), so a storm whose
    ranking has been **delivered** cannot be deleted at all; and `scenario_uploads` carries
    `check (status <> 'ready' or scenario_id is not null)`, so the upload row has to go first.
    Neither is the rule under test. What is under test is that CHG-028's trigger does not become
    a third obstacle, and it is asserted on the narrowest state where the question is only that.
    """
    connection = application.state.db
    assert apply_next(client, storm).status_code == 201
    assert connection.execute(
        "select count(*) from risk_scores where scenario_id = ?", (storm,)
    ).fetchone()[0] > 0

    connection.execute("delete from scenario_uploads where scenario_id = ?", (storm,))
    connection.execute("delete from scenarios where id = ?", (storm,))
    connection.commit()

    for table in (
        "risk_scores",
        "assets",
        "scenario_forecast_revisions",
        "scenario_forecast_cells",
    ):
        assert connection.execute(
            f"select count(*) from {table} where scenario_id = ?", (storm,)
        ).fetchone()[0] == 0, f"{table} kept rows for a deleted storm"


def test_deleting_one_asset_still_works_and_takes_only_its_ranks_with_it(
    application, client, storm
):
    """The second cascade the guard must not break, and the narrower one.

    `risk_scores.asset_id` cascades from `assets`, so the same `when` clause has to be false
    when an asset is removed on its own while its storm stays. Nothing in `backend/` issues this
    statement today — CHG-024 says so — which is precisely why the schema, not the absence of a
    caller, is what has to allow it.
    """
    connection = application.state.db
    assert apply_next(client, storm).status_code == 201
    doomed = connection.execute(
        "select id from assets where scenario_id = ? limit 1", (storm,)
    ).fetchone()["id"]
    total = connection.execute(
        "select count(*) from risk_scores where scenario_id = ?", (storm,)
    ).fetchone()[0]

    connection.execute("delete from assets where id = ?", (doomed,))
    connection.commit()

    assert connection.execute(
        "select count(*) from risk_scores where asset_id = ?", (doomed,)
    ).fetchone()[0] == 0
    # Two revisions' rows for that one asset, and nobody else's.
    assert connection.execute(
        "select count(*) from risk_scores where scenario_id = ?", (storm,)
    ).fetchone()[0] == total - 2


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
    # CHG-064: the board starts seeded from the dataset's outage rows. The claim here is
    # that APPLYING A FORECAST creates none of any of it — counts unchanged, not zero.
    jobs_before = connection.execute("select count(*) from repair_jobs").fetchone()[0]
    reports_before = connection.execute("select count(*) from damage_reports").fetchone()[0]

    assert apply_next(client, storm).status_code == 201

    assert connection.execute("select count(*) from decision_records").fetchone()[0] == before
    assert connection.execute("select count(*) from repair_jobs").fetchone()[0] == jobs_before
    assert (
        connection.execute("select count(*) from damage_reports").fetchone()[0]
        == reports_before
    )


# --- The durable half -----------------------------------------------------------------------


RESTART_PASSWORD = "correct-horse-battery-staple"


def gusts_by_code(body) -> dict[str, tuple]:
    """Every asset's gust and the time it was issued, keyed by code.

    This is the half of a ranking that comes out of `scenario_forecast_cells` rather than out
    of `risk_scores`: `read_ranking` left-joins the cells, so a series that did not survive a
    restart makes every one of these `(None, None)` while the stored order is untouched.
    """
    return {
        item["external_ids"][0]: (gust_of(item)["value"], gust_of(item)["observed_at"])
        for item in body["items"]
    }


def restartable_storm(tmp_path, monkeypatch):
    from app.store import users

    database = tmp_path / "forecasts.db"
    application = build_application(monkeypatch, database)
    users.create_user(
        application.state.db,
        name="Ops Manager",
        email="admin@sgw.example",
        password=RESTART_PASSWORD,
        role="admin",
    )
    client = TestClient(application)
    sign_in(client, "admin@sgw.example", RESTART_PASSWORD)
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Track shift", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files(FIXTURE).items()],
    )
    assert created.status_code == 201, created.text
    return database, application, client, created.json()["scenario_id"]


def restart(monkeypatch, database, application):
    application.state.db.close()
    restarted = build_application(monkeypatch, database)
    client = TestClient(restarted)
    sign_in(client, "admin@sgw.example", RESTART_PASSWORD)
    return restarted, client


def test_the_revision_and_its_forecasts_survive_a_restart(tmp_path, monkeypatch):
    """`AGENT.md`: when a task introduces durable state, the restart test is part of the task.

    Done criterion 11 is *"the revision pointer **and the forecast series** survive a restart"*,
    and the second half is the half that carries data. **This test used to assert only the two
    earlier orders and the next revision number** — both served from stored `risk_scores` rows
    that no restart could lose — so a series held anywhere but the database passed it. The
    review's mutation was a `create temp table scenario_forecast_cells`, which shadows the real
    one for every unqualified read: indistinguishable inside one process, and a second
    application over the same file then re-ranks the whole storm to `ranked: 0, unscored: 5`
    with every asset carrying *"no forecast covers this asset"* — still 201, still revision 2,
    still green. **A restart that silently makes every asset unrankable is the screen CLAUDE.md
    forbids reading as safety**, and this is the criterion that exists to catch it.

    So the comparison is the **whole ranking**, values and all, not the order. The gust and its
    `valid_time` come out of `scenario_forecast_cells` by a left join; if the cells are gone the
    join misses and every one of them is null, whatever the stored order says.
    """
    database, application, first, scenario_id = restartable_storm(tmp_path, monkeypatch)

    at_zero = ranking(first, scenario_id)
    assert apply_next(first, scenario_id).status_code == 201
    at_one = ranking(first, scenario_id)
    # The haystack: there are forecast values to lose. Without this the comparisons below hold
    # just as well between two rankings that both say nothing.
    assert gusts_by_code(at_zero)[ALPHA] == (120, REVISION_0_AT)
    assert gusts_by_code(at_one)[BRAVO] == (128, REVISION_1_AT)
    assert all(gust != (None, None) for gust in gusts_by_code(at_one).values())

    restarted, second = restart(monkeypatch, database, application)

    # Whole items, not just the order — the order is `risk_scores.rank` and survives anything.
    assert ranking(second, scenario_id, revision=0)["items"] == at_zero["items"]
    assert ranking(second, scenario_id, revision=1)["items"] == at_one["items"]
    assert gusts_by_code(ranking(second, scenario_id, revision=0))[ALPHA] == (120, REVISION_0_AT)

    # The pointer carried on rather than starting again: the next apply is revision 2.
    applied = apply_next(second, scenario_id)
    assert applied.status_code == 201, applied.text
    assert applied.json()["forecast_revision"] == 2
    assert applied.json()["previous_forecast_revision"] == 1
    # And it re-ranked against a forecast that is still there. `ranked: 0, unscored: 5` is the
    # shape of a storm whose series did not survive, and it answers 201 exactly like this one.
    assert (applied.json()["ranked"], applied.json()["unscored"]) == (4, 1)
    at_two = ranking(second, scenario_id, revision=2)
    assert gusts_by_code(at_two)[ALPHA] == (132, REVISION_2_AT)
    assert gusts_by_code(at_two)[CHARLIE] == (60, REVISION_1_AT)
    assert find(at_two, ECHO)["score"] is None

    restarted.state.db.close()


def test_the_forecast_series_is_in_the_database_and_not_in_the_process(tmp_path, monkeypatch):
    """The same property, asserted against the store rather than through the API.

    Two applications, two connections, one file. Whatever the first process held in memory is
    gone; what the second can read is what was actually written (ADR-002 — *a restart is not an
    incident*). Asserted directly because it is the store's claim, and because a read served
    from a cache the API happens to keep would satisfy the test above and not this one.
    """
    from app.store import forecasts

    database, application, first, scenario_id = restartable_storm(tmp_path, monkeypatch)
    for _ in range(2):
        assert apply_next(first, scenario_id).status_code == 201

    restarted, _ = restart(monkeypatch, database, application)
    connection = restarted.state.db

    assert [
        (row["forecast_revision"], row["valid_time"])
        for row in forecasts.revisions(connection, scenario_id)
    ] == [(0, REVISION_0_AT), (1, REVISION_1_AT), (2, REVISION_2_AT)]
    stored = {
        (row["forecast_revision"], row["grid_cell_id"]): (
            row["wind_gust_mph"],
            row["valid_time"],
        )
        for row in connection.execute(
            "select forecast_revision, grid_cell_id, wind_gust_mph, valid_time"
            " from scenario_forecast_cells where scenario_id = ?",
            (scenario_id,),
        )
    }
    # Five cells at each of three revisions — every revision is a complete grid (CHG-025).
    assert len(stored) == 15
    assert stored[(0, "GC-A")] == (120.0, REVISION_0_AT)
    assert stored[(1, "GC-B")] == (128.0, REVISION_1_AT)
    assert stored[(2, "GC-A")] == (132.0, REVISION_2_AT)
    # Carried forward, and still saying how old it is rather than claiming the revision's time.
    assert stored[(2, "GC-C")] == (60.0, REVISION_1_AT)

    restarted.state.db.close()
