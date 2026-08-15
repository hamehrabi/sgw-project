"""FTEST-005 — REQ-F-005, REQ-F-006. Defined in `03-tests/04-failure/failure-tests.md`.

Force the database write to fail on a decision. Expect: **no success shown, no row written**,
and the operator's typed note still on screen. Log event `DB_WRITE_FAILED`.

The note is the part that is easy to lose and expensive to lose. An operator types a reason for
rejecting a recommendation during a storm; if a failed write clears the field, they have to
remember and retype it — and the realistic outcome is that the second attempt says less than the
first. The API's half of "the note survives" is that it never claims success; the screen's half
is `RecommendationDecision` keeping the field populated.
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
