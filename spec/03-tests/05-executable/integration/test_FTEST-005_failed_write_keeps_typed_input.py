"""FTEST-005 — REQ-F-005, REQ-F-006. Defined in `03-tests/04-failure/failure-tests.md`.

Force the database write to fail on a decision **or a placement**. Expect: **no success shown,
no row written**, and the operator's typed note or placement still on screen. Log event
`DB_WRITE_FAILED`.

The note is the part that is easy to lose and expensive to lose. An operator types a reason for
rejecting a recommendation during a storm; if a failed write clears the field, they have to
remember and retype it — and the realistic outcome is that the second attempt says less than the
first. The API's half of "the note survives" is that it never claims success; the screen's half
is `RecommendationDecision` keeping the field populated.

**The row has always named two writes and only one of them was ever tested.** REQ-F-005 is in
this row's requirement list and `edge-cases-and-failures.md` states the case in its own words —
*"the store fails the write as a placement is saved"*, risk *"a placement lost mid-storm"*.
Until TASK-007 there was no placement to lose. The second half of this file is that case; the
screen half of it is `frontend/e2e/E2E-001.spec.ts`, and *no placement row exists* is asserted
against the table in `test_E2E-001_place_crews_against_ranking.py`.
"""

import logging

from conftest import fixture_files, sign_in


def loaded_with_recommendation(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    scenario_id = created.json()["scenario_id"]
    return client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()["recommendation_id"]


DECISION_KINDS = ("accept", "change", "reject")


class FailsWritingDecisions:
    """Delegates everything and dies on the *decision* insert, not the recommendation one.

    Matched on the `kind` parameter rather than on the SQL text. The first version of this
    checked that "recommendation" was absent from the arguments — but a decision row carries
    `subject_type='recommendation'`, so the guard skipped exactly the write it existed to
    break, and the test asserted a 500 against a 201.
    """

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def execute(self, sql, *args, **kwargs):
        if "insert into decision_records" in sql and args:
            kind = args[0][4] if len(args[0]) > 4 else None
            if kind in DECISION_KINDS:
                raise RuntimeError("simulated write failure")
        return self._real.execute(sql, *args, **kwargs)


def test_a_failed_write_shows_no_success(client, application, accounts):
    recommendation_id = loaded_with_recommendation(client, accounts)
    real = application.state.db
    application.state.db = FailsWritingDecisions(real)
    try:
        response = client.post(
            f"/api/v1/recommendations/{recommendation_id}/decision",
            json={"decision": "reject", "note": "the ranking misses the coastal feeders"},
        )
    finally:
        application.state.db = real

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"


def test_a_failed_write_leaves_no_row(client, application, accounts):
    recommendation_id = loaded_with_recommendation(client, accounts)
    real = application.state.db
    before = real.execute("select count(*) from decision_records").fetchone()[0]

    application.state.db = FailsWritingDecisions(real)
    try:
        client.post(
            f"/api/v1/recommendations/{recommendation_id}/decision",
            json={"decision": "reject", "note": "the ranking misses the coastal feeders"},
        )
    finally:
        application.state.db = real

    assert real.execute("select count(*) from decision_records").fetchone()[0] == before


def test_the_failure_is_logged_without_the_note(client, application, accounts, caplog):
    """The note is an operator's words about a live storm. It belongs on screen, not in a log."""
    caplog.set_level(logging.DEBUG)
    recommendation_id = loaded_with_recommendation(client, accounts)
    real = application.state.db

    application.state.db = FailsWritingDecisions(real)
    try:
        client.post(
            f"/api/v1/recommendations/{recommendation_id}/decision",
            json={"decision": "reject", "note": "the ranking misses the coastal feeders"},
        )
    finally:
        application.state.db = real

    logged = "\n".join(record.getMessage() + str(record.__dict__) for record in caplog.records)
    assert "DB_WRITE_FAILED" in logged
    assert "coastal feeders" not in logged


def test_the_recommendation_can_still_be_decided_afterwards(client, application, accounts):
    """A failed attempt must not consume the one decision the recommendation is allowed."""
    recommendation_id = loaded_with_recommendation(client, accounts)
    real = application.state.db
    application.state.db = FailsWritingDecisions(real)
    try:
        client.post(
            f"/api/v1/recommendations/{recommendation_id}/decision",
            json={"decision": "reject", "note": "first attempt"},
        )
    finally:
        application.state.db = real

    retry = client.post(
        f"/api/v1/recommendations/{recommendation_id}/decision",
        json={"decision": "reject", "note": "second attempt"},
    )

    assert retry.status_code == 201


class FailsWritingPlacements(FailsWritingDecisions):
    """The same wrapper, aimed at the other write this row has always named."""

    def execute(self, sql, *args, **kwargs):
        if "insert into decision_records" in sql and args:
            kind = args[0][4] if len(args[0]) > 4 else None
            if kind == "placement":
                raise RuntimeError("simulated write failure")
        return self._real.execute(sql, *args, **kwargs)


def loaded_with_a_ranking(client, accounts) -> tuple[str, str]:
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    scenario_id = created.json()["scenario_id"]
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    return scenario_id, ranking["items"][0]["asset_id"]


def test_a_failed_placement_write_shows_no_success_and_writes_no_row(
    client, application, accounts
):
    """*A placement lost mid-storm* — the risk `edge-cases-and-failures.md` names for this row.

    The failure has to be visible as a failure. A placement that quietly did not save is worse
    than an error message, because the manager walks away believing the crew is accounted for.
    """
    scenario_id, asset_id = loaded_with_a_ranking(client, accounts)
    real = application.state.db
    before = real.execute(
        "select count(*) from decision_records where kind = 'placement'"
    ).fetchone()[0]

    application.state.db = FailsWritingPlacements(real)
    try:
        response = client.post(
            f"/api/v1/scenarios/{scenario_id}/placements",
            json={"crew": "North crew", "asset_ids": [asset_id], "note": "hold at the depot"},
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


def test_the_placement_failure_is_logged_without_the_crew_or_the_note(
    client, application, accounts, caplog
):
    """The crew label and the note are what a person typed about a live storm. `DB_WRITE_FAILED`
    says a placement write failed and who was doing it; it does not repeat their words back into
    a log file, and CON-003 has a further opinion about crew data specifically."""
    caplog.set_level(logging.DEBUG)
    scenario_id, asset_id = loaded_with_a_ranking(client, accounts)
    real = application.state.db

    application.state.db = FailsWritingPlacements(real)
    try:
        client.post(
            f"/api/v1/scenarios/{scenario_id}/placements",
            json={
                "crew": "Okonkwo line crew",
                "asset_ids": [asset_id],
                "note": "hold at the depot",
            },
        )
    finally:
        application.state.db = real

    logged = "\n".join(record.getMessage() + str(record.__dict__) for record in caplog.records)
    assert "DB_WRITE_FAILED" in logged
    assert "placement" in logged, "the log does not say which write failed"
    assert "Okonkwo" not in logged
    assert "hold at the depot" not in logged
