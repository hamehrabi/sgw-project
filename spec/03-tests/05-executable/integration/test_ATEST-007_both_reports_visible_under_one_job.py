"""ATEST-007 — REQ-F-007, AC-007. Defined in `acceptance-tests.md`.

    Given  two damage reports for the same location
    When   the dispatcher opens the board
    Then   both are visible and linked to one repair job, not two

ITEST-003 asserts the rows. This asserts what the dispatcher *sees*, and the two halves of
AC-007 pull against each other on purpose: **one job** is the de-duplication, **both visible**
is the refusal to throw the second report away. An implementation that discards the duplicate
satisfies "one job" and loses a report — which during a storm means a second call about the
same street that nobody can find any record of.

`frontend-component-spec.md` fixes the empty state in the same row: *"no damage reported",
never "all clear"*. An empty board is one of the three screens in this product that look like
good news when blank.
"""

from conftest import fixture_files, sign_in


def dispatcher_with_a_storm(client, accounts):
    """The dispatcher holds `user`. An admin loads the storm; the dispatcher works it."""
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    scenario_id = created.json()["scenario_id"]
    client.delete("/api/v1/auth/session")
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    return scenario_id


def report(client, scenario_id, neighbourhood, **extra):
    return client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports",
        json={"neighbourhood": neighbourhood, **extra},
    ).json()


def board_of(client, scenario_id):
    return client.get(f"/api/v1/scenarios/{scenario_id}/jobs").json()


def test_both_reports_are_visible_and_linked_to_one_job(client, accounts):
    scenario_id = dispatcher_with_a_storm(client, accounts)
    first = report(client, scenario_id, "Northgate")
    second = report(client, scenario_id, "Northgate")

    board = board_of(client, scenario_id)

    assert board["job_count"] == 1, "one location is one job"
    assert board["report_count"] == 2, "and neither report was thrown away"
    job = board["items"][0]
    assert [entry["report_id"] for entry in job["reports"]] == [
        first["report_id"],
        second["report_id"],
    ], "in the order they were called in — the queue is the history"


def test_the_second_report_is_not_silently_dropped(client, accounts):
    """The half a de-duplicating implementation loses. A report nobody can find is a radio
    call nobody can answer."""
    scenario_id = dispatcher_with_a_storm(client, accounts)
    report(client, scenario_id, "Northgate")
    second = report(client, scenario_id, "Northgate")

    board = board_of(client, scenario_id)

    assert second["report_id"] in {
        entry["report_id"] for job in board["items"] for entry in job["reports"]
    }
    assert second["status"] == "open", "the duplicate location is not a dismissed report"


def test_the_empty_board_is_no_damage_reported_rather_than_an_error(client, accounts):
    """It must render as an empty list, not a 404 and not a failure — and the count is
    stated, so "nothing reported" is a fact rather than a silence."""
    scenario_id = dispatcher_with_a_storm(client, accounts)

    board = board_of(client, scenario_id)

    assert board["items"] == []
    assert board["job_count"] == 0
    assert board["report_count"] == 0


def test_a_job_carries_no_rank_score_or_band(client, accounts):
    """Criticality badges the dispatch queue; risk orders the planning list. They are
    different lists, and folding one into the other is how a rank starts moving crews."""
    scenario_id = dispatcher_with_a_storm(client, accounts)
    report(client, scenario_id, "Northgate")

    job = board_of(client, scenario_id)["items"][0]

    assert not {"rank", "score", "band"} & set(job)
    assert job["priority_rank"] is None


def test_opening_the_board_dispatches_nothing(client, accounts):
    """BR-001, BR-005. A job is a note that work exists, never an instruction that it starts."""
    scenario_id = dispatcher_with_a_storm(client, accounts)
    report(client, scenario_id, "Northgate")

    job = board_of(client, scenario_id)["items"][0]

    assert job["assigned_to"] is None
    assert job["status"] == "pending", "created as work to be decided on, never as work started"


def test_a_report_may_name_an_asset_and_may_not(client, accounts):
    """§4: a report with no matching asset is still a report. The board must hold both."""
    scenario_id = dispatcher_with_a_storm(client, accounts)
    asset_id = client.get(f"/api/v1/scenarios/{scenario_id}/assets").json()["items"][0]["asset_id"]

    named = report(client, scenario_id, "Northgate", asset_id=asset_id)
    anonymous = report(client, scenario_id, "Northgate")

    assert named["asset_id"] == asset_id
    assert anonymous["asset_id"] is None
    assert board_of(client, scenario_id)["items"][0]["report_count"] == 2
