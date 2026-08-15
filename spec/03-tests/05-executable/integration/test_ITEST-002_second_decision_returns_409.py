"""ITEST-002 — REQ-F-006, BR-004. Defined in `integration-tests.md`.
Also ATEST-006 (AC-006) and STEST-007 (SEC-Z-003).

Post a second decision on a recommendation that already has one → 409, naming the existing
decision. **The first row is byte-identical afterwards, and no second row exists.**

`integration-tests.md` says why this one is the whole point of BR-004: *a handler that returns
409 after updating the row satisfies the status code and breaks the rule.* So the status is the
weakest assertion here, and the row comparison is the real one.
"""

from conftest import fixture_files, sign_in


def loaded_with_recommendation(client, accounts, as_admin=True):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    scenario_id = created.json()["scenario_id"]
    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()
    if not as_admin:
        client.delete("/api/v1/auth/session")
        sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    return scenario_id, ranking["recommendation_id"]


def decide(client, recommendation_id, decision, note=None, change=None):
    body = {"decision": decision}
    if note is not None:
        body["note"] = note
    if change is not None:
        body["change"] = change
    return client.post(f"/api/v1/recommendations/{recommendation_id}/decision", json=body)


def test_delivering_a_ranking_appends_exactly_one_recommendation(client, application, accounts):
    """FF-005's rule, and what gives a decision something to reference."""
    loaded_with_recommendation(client, accounts)

    rows = application.state.db.execute(
        "select * from decision_records where kind = 'recommendation'"
    ).fetchall()

    assert len(rows) == 1
    assert rows[0]["actor_user_id"] is None, "the system recommended; nobody decided yet"


def test_a_decision_is_recorded_with_its_actor_and_time(client, application, accounts):
    _, recommendation_id = loaded_with_recommendation(client, accounts)

    response = decide(client, recommendation_id, "accept")

    assert response.status_code == 201
    row = application.state.db.execute(
        "select * from decision_records where kind = 'accept'"
    ).fetchone()
    assert row["actor_user_id"] == accounts["admin"]["id"]
    assert row["occurred_at"]
    assert row["subject_id"] == recommendation_id


def test_a_second_decision_returns_409_and_names_the_first(client, accounts):
    _, recommendation_id = loaded_with_recommendation(client, accounts)
    decide(client, recommendation_id, "accept")

    second = decide(client, recommendation_id, "reject", note="changed my mind")

    assert second.status_code == 409
    assert "accept" in second.json()["message"]


def test_the_first_row_is_byte_identical_afterwards(client, application, accounts):
    """The assertion that matters. A handler returning 409 *after* writing passes on status."""
    _, recommendation_id = loaded_with_recommendation(client, accounts)
    decide(client, recommendation_id, "accept")
    before = dict(
        application.state.db.execute(
            "select * from decision_records where kind = 'accept'"
        ).fetchone()
    )

    decide(client, recommendation_id, "reject", note="changed my mind")

    rows = application.state.db.execute(
        "select * from decision_records where kind in ('accept','reject')"
    ).fetchall()
    assert len(rows) == 1, "no second decision row may exist"
    assert dict(rows[0]) == before


def test_change_and_reject_require_a_note(client, accounts):
    _, recommendation_id = loaded_with_recommendation(client, accounts)

    assert decide(client, recommendation_id, "reject").status_code == 400
    assert decide(client, recommendation_id, "change").status_code == 400
    # And the refusals wrote nothing, so a valid decision still succeeds.
    assert decide(client, recommendation_id, "accept").status_code == 201


def test_an_unknown_decision_value_is_refused(client, accounts):
    _, recommendation_id = loaded_with_recommendation(client, accounts)

    assert decide(client, recommendation_id, "escalate", note="x").status_code == 400


def test_deciding_is_not_privileged(client, accounts):
    """"Deciding is the whole point of the product and is not a privileged action.\""""
    _, recommendation_id = loaded_with_recommendation(client, accounts, as_admin=False)

    assert decide(client, recommendation_id, "accept").status_code == 201


def test_a_user_may_not_read_the_decision_record(client, accounts):
    """STEST-007 — SEC-Z-003. Reading the record is admin-only; deciding is not."""
    scenario_id, recommendation_id = loaded_with_recommendation(client, accounts, as_admin=False)
    decide(client, recommendation_id, "accept")

    response = client.get(f"/api/v1/scenarios/{scenario_id}/decisions")

    assert response.status_code == 403
    assert "rows" not in response.json()


def test_an_admin_may_read_the_decision_record(client, accounts):
    scenario_id, recommendation_id = loaded_with_recommendation(client, accounts)
    decide(client, recommendation_id, "change", note="send to Northgate first", change={"a": 1})

    body = client.get(f"/api/v1/scenarios/{scenario_id}/decisions").json()

    kinds = [row["kind"] for row in body["items"]]
    assert kinds == ["recommendation", "change"], "ordered by when they happened"


def test_the_decision_moves_nothing(client, application, accounts):
    """BR-001. The response is a record, never an action."""
    _, recommendation_id = loaded_with_recommendation(client, accounts)

    body = decide(client, recommendation_id, "accept").json()

    assert set(body) == {
        "decision_record_id",
        "recommendation_id",
        "decision",
        "actor_user_id",
        "occurred_at",
    }
    # Nothing was created beyond the audit row itself: the recommendation and the accept, and
    # no third row representing an action the platform took on its own.
    assert application.state.db.execute(
        "select count(*) from decision_records"
    ).fetchone()[0] == 2
