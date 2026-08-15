"""ITEST-001 — REQ-F-001, REQ-F-002. Defined in `03-tests/02-functional/integration-tests.md`.

Upload a fixture carrying all seven defects, parse it, and rank it. Expect 201 on upload; the
scenario becomes rankable; every ranked item carries reasons. One scenario row; assets present
with `match_status`; risk scores at revision 0; **no second scenario**.

**The ranking half belongs to TASK-003 and is skipped by name below**, not quietly dropped.
Standing up a placeholder scorer to satisfy it would anticipate the module TASK-002's *do not
change* list forbids touching, and ADR-005 would have to tear it out again. What this file
asserts today is everything up to the boundary: upload, parse, join, and one scenario.
"""

import pytest
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


@pytest.mark.skip(reason="ranking is TASK-003, behind ADR-005's boundary; see the docstring")
def test_the_scenario_becomes_rankable_and_every_item_carries_reasons():
    """Owed by TASK-003: risk scores at revision 0, every one with at least one reason."""
