"""E2E-001 — REQ-F-002…006. Defined in `03-tests/02-functional/end-to-end-tests.md`.

    Flow name:    Place crews against the ranking
    Preconditions: signed in as a user; one scenario loaded at forecast revision 0; the
                   scenario's fixture carries all seven data defects on purpose

    1. Open the planning view.
    2. Read the ranked list. Open the reasons on the top-ranked asset.
    3. Apply the scenario's forecast change.
    4. Read the re-ranked list; open the previous order for comparison.
    5. Accept one recommendation and reject another, giving a note on the reject.
    6. Record a crew placement against the current ranking.

    Failure path: repeat step 6 with the store made to fail the write.
    Expected:     a clear message, THE TYPED PLACEMENT IS STILL ON SCREEN, no placement row.

**This file is the flow's API half and `frontend/e2e/E2E-001.spec.ts` is its browser half, and
the split is deliberate rather than duplication.** Two of the written expectations are about
rows and one is about a screen. *No placement row exists* after the failure path can only be
proven where the rows are, and it needs the **store** made to fail, which is what the wrapper
below does. *The typed placement is still on screen* can only be proven where the screen is, and
Playwright is where that lives. A run that asserted the second by reading `PlacementForm.tsx`
would be the fourth time in this repository a claim about a screen was satisfied by reading
source (`review-log.md`, TASK-006's fourth check).

**The fixture is `storm-for-the-planning-flow`, and it is new because no existing one satisfies
the preconditions as written.** E2E-001 wants all seven data defects *and* a forecast change:
`storm-with-seven-defects` carries one forecast time, so step 3 answers 409 against it, and
`storm-with-a-forecast-change` carries five clean assets. The new fixture is the seven-defect
storm with a second forecast time, listed **first** in the file so its file order and its
chronological order remain two different answers (CHG-025, and the reordering that turned 17
tests red at TASK-006's remediation).
"""

import logging

import pytest
from conftest import fixture_files, sign_in

FIXTURE = "storm-for-the-planning-flow"

# The two assets the forecast moves, named by their prepared-file codes rather than by the
# identifiers the loader mints. GC-04 goes 61 → 155 mph and GC-01 goes 96 → 40, and the two
# assets swap ends of the list — the forecast is the only thing that could have done it.
RISES = "SS-5566"
FALLS = "SS-1042"
# In the ranking and not ranked (FTEST-004): no weather row covers it. A crew may still be
# placed at it, which is criterion 6.
UNSCORED = "LN-8899"


def codes(items) -> list[str]:
    """The order as a reader sees it, by prepared-file code."""
    return [item["external_ids"][0] for item in items]


def position(items, code) -> int:
    order = codes(items)
    assert code in order, f"{code} is not in the ranking at all"
    return order.index(code)


def asset_id_of(items, code) -> str:
    return next(item["asset_id"] for item in items if code in item["external_ids"])


@pytest.fixture
def planning(client, accounts):
    """Signed in, one storm loaded, sitting at forecast revision 0.

    Signed in as the **user**, not the admin: `technical-spec.md` §7.2 gives both roles the
    placement, and REQ-R-001 gives the non-admin the planning view. Loading needs the admin, so
    the fixture loads and then hands the session over — which also proves the placement is not
    quietly privileged.
    """
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Planning flow", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files(FIXTURE).items()],
    )
    assert created.status_code == 201, created.text
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    return created.json()["scenario_id"]


def test_the_whole_flow_reaches_a_recorded_placement(client, planning, accounts):
    """Steps 1 to 6, and each of the written *expected visible results* in turn."""
    scenario_id = planning

    # 1. Open the planning view.
    scenario = client.get(f"/api/v1/scenarios/{scenario_id}").json()
    assert scenario["forecast_revision"] == 0
    # AC-010: the age is stated rather than inferred, before the manager acts on it.
    assert scenario["data_age_hours"] is not None

    # 2. Read the ranked list, with the reasons already beside every rank (BR-002, AC-004 —
    #    "never behind a separate request").
    first = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    assert first["forecast_revision"] == 0
    for item in first["items"]:
        if item["score"] is None:
            # Present, and not ranked low. An empty screen must never read as safety.
            assert item["unscored_reason"], f"{item['external_ids']} is unscored and silent"
        else:
            assert item["reasons"], f"{item['external_ids']} has a rank and no reasons"
    assert UNSCORED in codes(first["items"])
    before = codes(first["items"])

    # 3. Apply the scenario's forecast change.
    applied = client.post(f"/api/v1/scenarios/{scenario_id}/forecast-revisions")
    assert applied.status_code == 201, applied.text
    assert applied.json()["forecast_revision"] == 1

    # 4. The re-ranked list, and the previous order still readable beside it (AC-005).
    second = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    assert codes(second["items"]) != before
    assert position(second["items"], RISES) < position(first["items"], RISES)
    assert position(second["items"], FALLS) > position(first["items"], FALLS)
    recalled = client.get(
        f"/api/v1/scenarios/{scenario_id}/risks", params={"forecast_revision": 0}
    ).json()
    assert codes(recalled["items"]) == before

    # 5. Accept one recommendation and reject another, with a note on the reject. Each
    #    revision carries its own recommendation row (FF-005), which is what makes "another"
    #    reachable at all.
    accepted = client.post(
        f"/api/v1/recommendations/{second['recommendation_id']}/decision",
        json={"decision": "accept", "note": None},
    )
    assert accepted.status_code == 201, accepted.text
    rejected = client.post(
        f"/api/v1/recommendations/{recalled['recommendation_id']}/decision",
        json={"decision": "reject", "note": "the earlier order missed the coastal plant"},
    )
    assert rejected.status_code == 201, rejected.text

    # 6. Record a crew placement against the current ranking.
    placed = client.post(
        f"/api/v1/scenarios/{scenario_id}/placements",
        json={
            "crew": "North crew",
            "asset_ids": [
                asset_id_of(second["items"], RISES),
                asset_id_of(second["items"], UNSCORED),
            ],
            "forecast_revision": second["forecast_revision"],
            "note": "staged at the depot until the gust passes",
        },
    )
    assert placed.status_code == 201, placed.text
    body = placed.json()
    # "The placement is saved and shows which revision it was made against."
    assert body["forecast_revision"] == 1
    assert body["recommendation_id"] == second["recommendation_id"]
    assert body["crew"] == "North crew"
    assert body["actor_user_id"] == accounts["user"]["id"]
    assert body["asset_ids"] == [
        asset_id_of(second["items"], RISES),
        asset_id_of(second["items"], UNSCORED),
    ]


def test_the_placement_is_in_the_decision_record_and_traceable_to_its_ranking(
    client, planning, application, accounts
):
    """*Traceable to the ranking and forecast revision it was made against* (`product-spec.md`
    §10), read back out of the append-only record rather than out of the response that wrote it.

    The `subject_id` is deliberately the same value the `recommendation` row for that ranking
    carries, so one lookup on `decision_records_by_subject` answers *what was recommended here,
    and what did people decide about it*.
    """
    scenario_id = planning
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    asset_id = ranking["items"][0]["asset_id"]

    placed = client.post(
        f"/api/v1/scenarios/{scenario_id}/placements",
        json={"crew": "South crew", "asset_ids": [asset_id]},
    )
    assert placed.status_code == 201, placed.text

    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    record = client.get(f"/api/v1/scenarios/{scenario_id}/decisions").json()["items"]
    placements = [row for row in record if row["kind"] == "placement"]
    recommendations = [row for row in record if row["kind"] == "recommendation"]

    assert len(placements) == 1
    assert len(recommendations) == 1, "no recommendation row, so 'same subject' proves nothing"
    row = placements[0]
    assert row["subject_type"] == "ranking"
    assert row["subject_id"] == recommendations[0]["subject_id"]
    assert row["subject_id"] == f"{scenario_id}:0"
    assert row["actor_user_id"] == accounts["user"]["id"]
    assert row["payload"] == {
        "crew": "South crew",
        "asset_ids": [asset_id],
        "forecast_revision": 0,
        "recommendation_id": ranking["recommendation_id"],
        "note": None,
    }


def test_a_placement_records_the_revision_it_was_made_against_not_the_current_one(
    client, planning
):
    """Done criterion 2, and the mutation it exists to catch.

    A manager comparing orders is looking at revision 0 while the storm is current at revision 1.
    Recording the pointer instead of the revision they named would attach the placement to a list
    they were not reading — the same class of wrongness as a re-rank rewriting the order a
    decision was made against, arriving from the other end.
    """
    scenario_id = planning
    earlier = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    assert client.post(f"/api/v1/scenarios/{scenario_id}/forecast-revisions").status_code == 201
    current = client.get(f"/api/v1/scenarios/{scenario_id}").json()["forecast_revision"]
    assert current == 1, "the pointer did not move, so the two answers are the same answer"

    placed = client.post(
        f"/api/v1/scenarios/{scenario_id}/placements",
        json={
            "crew": "Night crew",
            "asset_ids": [earlier["items"][0]["asset_id"]],
            "forecast_revision": 0,
        },
    )

    assert placed.status_code == 201, placed.text
    assert placed.json()["forecast_revision"] == 0
    assert placed.json()["recommendation_id"] == earlier["recommendation_id"]


def test_a_placement_may_name_an_asset_that_could_not_be_scored(client, planning):
    """Done criterion 6. An UNSCORED asset is in the ranking and is not ranked, and the whole
    reason it is on the list is so a person can plan around it. Refusing to let anyone place a
    crew at it would be the same failure as omitting it — the review log's first pre-declared
    Block condition, one step further out."""
    scenario_id = planning
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    unscored = next(item for item in ranking["items"] if item["score"] is None)
    assert unscored["rank"] is None

    placed = client.post(
        f"/api/v1/scenarios/{scenario_id}/placements",
        json={"crew": "Survey crew", "asset_ids": [unscored["asset_id"]]},
    )

    assert placed.status_code == 201, placed.text
    assert placed.json()["asset_ids"] == [unscored["asset_id"]]


def test_recording_a_placement_moves_nothing_and_creates_nothing_else(
    client, planning, application
):
    """BR-001, asserted as the whole database rather than as a promise.

    A placement is the feature in this product whose *name* sounds most like an instruction. The
    check is deliberately not "no repair job was created" — it is that every table except the one
    the audit row lands in has exactly the row count it had before.
    """
    scenario_id = planning
    connection = application.state.db
    client.get(f"/api/v1/scenarios/{scenario_id}/risks")

    tables = sorted(
        row[0]
        for row in connection.execute(
            "select name from sqlite_master where type = 'table' and name not like 'sqlite_%'"
        )
    )
    # The haystack: an enumeration that returned nothing would make every difference below
    # vacuous, and "nothing changed" is worth nothing without "these tables exist".
    assert {"repair_jobs", "damage_reports", "risk_scores", "decision_records"} <= set(tables)

    def counts() -> dict[str, int]:
        return {
            name: connection.execute(f"select count(*) from {name}").fetchone()[0]  # noqa: S608
            for name in tables
        }

    before = counts()
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    placed = client.post(
        f"/api/v1/scenarios/{scenario_id}/placements",
        json={"crew": "Coastal crew", "asset_ids": [ranking["items"][0]["asset_id"]]},
    )
    assert placed.status_code == 201, placed.text

    after = counts()
    assert after["decision_records"] == before["decision_records"] + 1
    assert {name: n for name, n in after.items() if name != "decision_records"} == {
        name: n for name, n in before.items() if name != "decision_records"
    }


class FailsWritingPlacements:
    """Delegates everything and dies on the *placement* insert.

    Matched on the `kind` parameter, the way `FTEST-005`'s wrapper is, and for the reason that
    file records: matching on the SQL text catches the recommendation row this flow also writes
    and the test then asserts a 500 against a 201.
    """

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def execute(self, sql, *args, **kwargs):
        if "insert into decision_records" in sql and args:
            kind = args[0][4] if len(args[0]) > 4 else None
            if kind == "placement":
                raise RuntimeError("simulated write failure")
        return self._real.execute(sql, *args, **kwargs)


def test_the_failure_path_shows_no_success_and_leaves_the_placements_table_empty(
    client, planning, application, caplog
):
    """The written failure path, and the piece of it only the store can answer:
    *no placement row exists*.

    The evidence E2E-001 asks to capture is "the empty placements table after the failure path",
    and this is it — counted at the row, with the count before it so an empty table for the wrong
    reason cannot pass.
    """
    caplog.set_level(logging.DEBUG)
    scenario_id = planning
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    real = application.state.db
    before = real.execute(
        "select count(*) from decision_records where kind = 'placement'"
    ).fetchone()[0]

    application.state.db = FailsWritingPlacements(real)
    try:
        response = client.post(
            f"/api/v1/scenarios/{scenario_id}/placements",
            json={
                "crew": "North crew",
                "asset_ids": [ranking["items"][0]["asset_id"]],
                "note": "hold at the depot",
            },
        )
    finally:
        application.state.db = real

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert (
        real.execute("select count(*) from decision_records where kind = 'placement'").fetchone()[
            0
        ]
        == before
    )

    logged = "\n".join(record.getMessage() + str(record.__dict__) for record in caplog.records)
    assert "DB_WRITE_FAILED" in logged
    # The crew label and the note are the operator's words about a live storm. They belong on
    # their screen, not in a log (CON-003 on crew data; FTEST-005's rule on the note).
    assert "North crew" not in logged
    assert "hold at the depot" not in logged


def test_a_placement_after_a_failed_one_still_works(client, planning, application):
    """A failed attempt consumes nothing. Unlike a decision, a ranking may carry any number of
    placements — several crews wait in several places — so there is no 409 here and a retry is
    an ordinary write."""
    scenario_id = planning
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    real = application.state.db
    application.state.db = FailsWritingPlacements(real)
    try:
        client.post(
            f"/api/v1/scenarios/{scenario_id}/placements",
            json={"crew": "North crew", "asset_ids": [ranking["items"][0]["asset_id"]]},
        )
    finally:
        application.state.db = real

    retry = client.post(
        f"/api/v1/scenarios/{scenario_id}/placements",
        json={"crew": "North crew", "asset_ids": [ranking["items"][0]["asset_id"]]},
    )
    second = client.post(
        f"/api/v1/scenarios/{scenario_id}/placements",
        json={"crew": "South crew", "asset_ids": [ranking["items"][1]["asset_id"]]},
    )

    assert retry.status_code == 201, retry.text
    assert second.status_code == 201, second.text
    assert (
        real.execute("select count(*) from decision_records where kind = 'placement'").fetchone()[
            0
        ]
        == 2
    )


def test_the_endpoint_refuses_what_the_contract_says_it_refuses(client, planning):
    """The legible 400s, in front of the store's own refusals.

    Each is a caller mistake and must be answered as one. A `500` here says the platform broke,
    which during a storm sends the operator to the wrong person — the failure UTEST-012 found
    one column over, when a service constant and a schema bound disagreed.
    """
    scenario_id = planning
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    asset_id = ranking["items"][0]["asset_id"]

    cases = {
        "no crew": {"crew": "   ", "asset_ids": [asset_id]},
        "no assets": {"crew": "North crew", "asset_ids": []},
        "the same asset twice": {"crew": "North crew", "asset_ids": [asset_id, asset_id]},
        "an over-long crew label": {"crew": "N" * 500, "asset_ids": [asset_id]},
        "a crew label with a newline": {"crew": "North\ncrew", "asset_ids": [asset_id]},
        "an asset that is not in this storm": {"crew": "North crew", "asset_ids": ["AS-nope"]},
    }
    for name, body in cases.items():
        response = client.post(f"/api/v1/scenarios/{scenario_id}/placements", json=body)
        assert response.status_code == 400, f"{name}: {response.status_code} {response.text}"
        assert response.json()["code"] == "validation_error", name

    # A revision the storm has never ranked is a 404 and never a silent fall back to the
    # current one (`technical-spec.md` §7.3), the same rule `GET /risks` follows.
    missing = client.post(
        f"/api/v1/scenarios/{scenario_id}/placements",
        json={"crew": "North crew", "asset_ids": [asset_id], "forecast_revision": 9},
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"
    assert "revision 9" in missing.json()["message"]

    unknown_storm = client.post(
        "/api/v1/scenarios/SC-nothing/placements",
        json={"crew": "North crew", "asset_ids": [asset_id]},
    )
    assert unknown_storm.status_code == 404
    # **Read out of the message, not off the status**, and the mutation is what said so. An
    # endpoint that does not exist answers 404, and so does an unknown storm that got past the
    # scenario lookup and was refused three checks later for having no ranking — removing the
    # lookup altogether left this assertion green until it named which refusal it wanted.
    assert unknown_storm.json()["code"] == "not_found"
    assert "storm could not be found" in unknown_storm.json()["message"]


def test_a_premise_level_field_is_refused_rather_than_dropped(client, planning, application):
    """CON-003 at the API boundary. Dropping an unknown field silently teaches the caller it was
    accepted, and the next caller stores it somewhere else — `api/dispatch.py`'s reasoning,
    reused, because a placement is the other place a location could arrive."""
    scenario_id = planning
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    asset_id = ranking["items"][0]["asset_id"]

    for field, value in (
        ("address", "14 Harbour Street"),
        ("meter_id", "MTR-99183"),
        ("lat", 33.7701),
        ("household", "Okonkwo"),
        ("phone", "+1-555-0100"),
    ):
        response = client.post(
            f"/api/v1/scenarios/{scenario_id}/placements",
            json={"crew": "North crew", "asset_ids": [asset_id], field: value},
        )
        assert response.status_code == 400, f"{field}: {response.status_code}"

    stored = "\n".join(
        row[0]
        for row in application.state.db.execute(
            "select payload from decision_records where kind = 'placement'"
        )
    )
    assert "Harbour Street" not in stored
    assert "MTR-99183" not in stored


def test_both_roles_may_place_a_crew_and_a_signed_out_caller_may_not(
    client, planning, accounts
):
    """SEC-Z-001, and the deny path beside the allow path — `AGENT.md` predicts building one
    without the other, and this is the third task where the pair is reachable."""
    scenario_id = planning
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    body = {"crew": "North crew", "asset_ids": [ranking["items"][0]["asset_id"]]}

    as_user = client.post(f"/api/v1/scenarios/{scenario_id}/placements", json=body)
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    as_admin = client.post(f"/api/v1/scenarios/{scenario_id}/placements", json=body)
    client.delete("/api/v1/auth/session")
    signed_out = client.post(f"/api/v1/scenarios/{scenario_id}/placements", json=body)

    assert as_user.status_code == 201, as_user.text
    assert as_admin.status_code == 201, as_admin.text
    assert signed_out.status_code == 401
    assert set(signed_out.json()) == {"code", "message"}
