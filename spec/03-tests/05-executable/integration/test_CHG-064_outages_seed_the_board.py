"""CHG-064 — the dataset's outage records ARE the board's starting worklist.

At load, every outage row becomes a stored damage report, attached to its asset where
the id matches and grouped into repair jobs by area — AC-007's rule, applied to the
dataset the same way it applies to a radio call. An identical re-upload resolves to the
existing scenario and seeds nothing twice.

The seven-defects fixture carries five outage rows — three in SA-NORTH (one with no
asset id), two in SA-COAST — so the board starts as two jobs holding five reports.
A figure defect 5 flagged as impossible must never enter the board's sums.
"""

import pytest
from conftest import fixture_files, sign_in


@pytest.fixture
def loaded(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Seeded storm", "source_note": "prepared pack"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


def board_of(client, scenario_id):
    answer = client.get(f"/api/v1/scenarios/{scenario_id}/jobs")
    assert answer.status_code == 200, answer.text
    return answer.json()


def test_the_outage_rows_arrive_as_reports_grouped_into_jobs_by_area(client, loaded):
    board = board_of(client, loaded)
    assert board["job_count"] > 0, "a dataset with outage rows starts with a worklist"
    # Every row is on the board: reports across jobs equal the fixture's outage rows.
    assert board["report_count"] == 5
    # Grouping is AC-007's: one job per area, not one per row.
    locations = [job["location"]["neighbourhood"] for job in board["items"]]
    assert len(locations) == len(set(locations)), "two jobs for one location cannot exist"
    assert board["job_count"] < board["report_count"]


def test_a_seeded_report_names_its_asset_when_the_id_matches(client, application, loaded):
    rows = application.state.db.execute(
        "select asset_id, customers_out from damage_reports where scenario_id = ?",
        (loaded,),
    ).fetchall()
    assert sum(1 for row in rows if row["asset_id"]) >= 3, "matched ids link to assets"
    # Defect 5's rule holds at the boundary: an impossible figure is flagged and then
    # NOT used — it must not enter the board's customer sums.
    assert all(
        row["customers_out"] is None or row["customers_out"] <= 200_000 for row in rows
    )


def test_an_identical_reupload_seeds_nothing_twice(client, loaded):
    before = board_of(client, loaded)
    again = client.post(
        "/api/v1/scenarios",
        data={"name": "Seeded storm", "source_note": "prepared pack"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    assert again.status_code == 200, "identical content resolves to the same storm"
    assert again.json()["scenario_id"] == loaded
    after = board_of(client, loaded)
    assert after["report_count"] == before["report_count"]
    assert after["job_count"] == before["job_count"]


def test_a_filed_report_in_a_seeded_area_joins_the_existing_job(client, loaded):
    board = board_of(client, loaded)
    area = board["items"][0]["location"]["neighbourhood"]
    filed = client.post(
        f"/api/v1/scenarios/{loaded}/damage-reports",
        json={"neighbourhood": area, "asset_id": None, "customers_out": 40},
    )
    assert filed.status_code == 201, filed.text
    after = board_of(client, loaded)
    assert after["job_count"] == board["job_count"], "same location, same job (AC-007)"
    assert after["report_count"] == board["report_count"] + 1
