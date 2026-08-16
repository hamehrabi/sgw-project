"""ITEST-001 — REQ-F-001, REQ-F-002. Defined in `03-tests/02-functional/integration-tests.md`.

Upload a fixture carrying all seven defects, parse it, and rank it. Expect 201 on upload; the
scenario becomes rankable; every ranked item carries reasons. One scenario row; assets present
with `match_status`; risk scores at revision 0; **no second scenario**.

**The ranking half was skipped by name while TASK-003 did not exist**, rather than quietly
dropped — standing up a placeholder scorer would have anticipated the module TASK-002's *do not
change* list forbade touching. TASK-003 shipped the scorer, and the skip outlived the reason for
it by six tasks: `cicd-pipeline.md`'s own rule says *a test that is skipped to make the pipeline
pass is a finding, not a fix*, and a skip whose stated cause has been resolved is that finding
wearing an explanation. It is paid at the foot of this file, and the suite now has **no skipped
test at all**.
"""

import json

from conftest import fixture_files, sign_in


def upload(client, files=None):
    return client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[
            ("files", (name, content, "text/csv"))
            for name, content in (files or fixture_files()).items()
        ],
    )


def as_admin(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])


def test_the_upload_is_accepted(client, accounts):
    as_admin(client, accounts)

    assert upload(client).status_code == 201


def test_one_scenario_row_is_created_at_revision_zero(client, application, accounts):
    as_admin(client, accounts)

    upload(client)

    rows = application.state.db.execute("select * from scenarios").fetchall()
    assert len(rows) == 1
    assert rows[0]["forecast_revision"] == 0


def test_every_asset_is_stored_with_a_match_status(client, application, accounts):
    as_admin(client, accounts)

    upload(client)

    statuses = [
        row["match_status"] for row in application.state.db.execute("select * from assets")
    ]
    assert statuses
    assert set(statuses) <= {"matched", "needs_review"}
    assert "needs_review" in statuses, "the fixture's near-match must survive to the store"


def test_the_two_codes_for_one_substation_are_stored_as_one_asset(client, application, accounts):
    as_admin(client, accounts)

    upload(client)

    rows = application.state.db.execute(
        "select external_ids from assets where external_ids like '%SS-1042%'"
    ).fetchall()
    assert len(rows) == 1
    assert "TX-4471" in rows[0]["external_ids"]


def test_a_second_identical_upload_produces_no_second_scenario(client, application, accounts):
    """Idempotency (§5): identical content replaces in place rather than creating a rival."""
    as_admin(client, accounts)
    upload(client)

    second = upload(client)

    assert second.status_code == 200, "an identical re-load is a replacement, not a creation"
    assert application.state.db.execute("select count(*) from scenarios").fetchone()[0] == 1


def test_the_upload_is_recorded_as_ready_and_names_its_scenario(client, application, accounts):
    as_admin(client, accounts)

    upload(client)

    row = application.state.db.execute(
        "select status, scenario_id, failed_file from scenario_uploads"
    ).fetchone()
    assert row["status"] == "ready"
    assert row["scenario_id"]
    assert row["failed_file"] is None


def test_the_scenario_becomes_rankable_and_every_item_carries_reasons(
    client, application, accounts
):
    """Owed by TASK-003, and paid here — the skip is gone rather than re-explained.

    **Why this is not ATEST-003 again.** ATEST-003 reads the ranking out of the *response*.
    This is the integration test named in `integration-tests.md`, and its integration point is
    **load → parse → join → rank → store**, so it asserts the rows `risk_scores` holds after one
    pass over a fixture carrying all seven defects. `technical-spec.md` §6 makes that the
    difference that matters: every read is served from stored results, so a ranking that is
    correct in the response and absent from the table is a ranking that does not survive the
    next request.

    The haystack is named before anything is reported absent (`AGENT.md`, 2026-08-16): the
    number of stored rows is asserted against the number of assets, so *every row carries a
    reason* cannot be satisfied by a table with no rows in it.
    """
    as_admin(client, accounts)
    scenario_id = upload(client).json()["scenario_id"]

    client.get(f"/api/v1/scenarios/{scenario_id}/risks")

    rows = application.state.db.execute(
        "select * from risk_scores where scenario_id = ?", (scenario_id,)
    ).fetchall()
    assets = application.state.db.execute(
        "select count(*) from assets where scenario_id = ?", (scenario_id,)
    ).fetchone()[0]

    assert assets, "the fixture must have loaded, or nothing below means anything"
    assert len(rows) == assets, "every asset is IN the ranking, scorable or not"
    assert {row["forecast_revision"] for row in rows} == {0}

    scored = [row for row in rows if row["score"] is not None]
    unscored = [row for row in rows if row["score"] is None]

    assert scored, "a fixture that ranks nothing cannot prove a rank carries its reasons"
    assert unscored, "the fixture's unscorable asset must reach the store, not be dropped"

    for row in scored:
        assert json.loads(row["reasons"]), f"BR-002: {row['asset_id']} is ranked with no reason"
    for row in unscored:
        assert row["unscored_reason"], (
            f"{row['asset_id']} has no score and no reason for having none — "
            "an empty cell must never read as safety"
        )
