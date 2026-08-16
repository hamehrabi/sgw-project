"""UTEST-012 — REQ-NF-007, CON-003. Defined in `03-tests/02-functional/unit-tests.md`.

Rule under test: damage locations are aggregated before they leave.
  normal  — a neighbourhood-level figure in a log
  edge    — a single report in a sparse area still aggregates
  failure — a household-identifying location in any log or export → test fails

**This task is the first place a damage location exists**, so this is the first place the rule
can be broken. It is enforced one step earlier than the requirement asks: CON-003 forbids
storing any premise-level record, so the column is constrained to hold a neighbourhood and
nothing else. There is then nothing finer to aggregate on the way out — which is the only
version of this rule that a later refactor cannot quietly undo, because the aggregation is not
a step anyone can forget to call.
"""

import json
import logging
import sqlite3

import pytest
from conftest import sign_in

FORBIDDEN_IN_A_LOG = ("street", "avenue", "meter", "account", "33.7", "-118.5")


def a_storm(application, accounts):
    """A scenario row and nothing else — this rule needs no assets to be broken."""
    application.state.db.execute(
        "insert into scenarios (id, name, source_note, loaded_by, loaded_at, forecast_revision)"
        " values ('SC-privacy', 'Privacy storm', 'unit', ?, '2026-08-16T00:00:00Z', 0)",
        (accounts["admin"]["id"],),
    )
    application.state.db.commit()
    return "SC-privacy"


def insert_report(connection, scenario_id, location):
    connection.execute(
        "insert into damage_reports"
        " (id, scenario_id, location, reported_at, reported_by, status)"
        " values ('DR-direct', ?, ?, '2026-08-16T00:00:00Z', 'U-1', 'open')",
        (scenario_id, location),
    )


def everything_logged(caplog):
    parts = []
    for record in caplog.records:
        parts.append(record.getMessage())
        parts.extend(
            f"{key}={value}"
            for key, value in record.__dict__.items()
            if key not in logging.LogRecord("", 0, "", 0, "", (), None).__dict__
        )
    return "\n".join(parts)


@pytest.mark.parametrize(
    "location",
    [
        '{"address": "14 Harbour Street"}',
        '{"neighbourhood": "Northgate", "address": "14 Harbour Street"}',
        '{"neighbourhood": "Northgate", "meter_id": "M-99812"}',
        '{"neighbourhood": "Northgate", "lat": 33.7412, "lon": -118.4991}',
        '{"neighbourhood": null}',
        "{}",
        "not json at all",
    ],
)
def test_the_store_refuses_a_location_finer_than_a_neighbourhood(
    application, accounts, location
):
    """The failure case, asserted against the **database** rather than a validator. A rule
    that lives only in the service layer is one the first refactor removes (ADR-002)."""
    scenario_id = a_storm(application, accounts)

    with pytest.raises(sqlite3.IntegrityError):
        insert_report(application.state.db, scenario_id, location)
    application.state.db.rollback()


def test_the_store_accepts_a_neighbourhood(application, accounts):
    """The permitted shape, so the check above is refusing something rather than everything."""
    scenario_id = a_storm(application, accounts)

    insert_report(application.state.db, scenario_id, json.dumps({"neighbourhood": "Northgate"}))
    application.state.db.commit()

    stored = application.state.db.execute(
        "select location from damage_reports where id = 'DR-direct'"
    ).fetchone()
    assert json.loads(stored["location"]) == {"neighbourhood": "Northgate"}


def test_the_endpoint_refuses_a_household_field_outright(client, application, accounts):
    """It is not silently dropped — a caller who sent an address is told, and nothing is
    written. Dropping it quietly teaches the sender that the field is accepted."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)

    response = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports",
        json={"neighbourhood": "Northgate", "address": "14 Harbour Street"},
    )

    assert response.status_code == 400
    assert application.state.db.execute(
        "select count(*) from damage_reports"
    ).fetchone()[0] == 0


def test_the_log_carries_a_neighbourhood_level_figure(client, application, accounts, caplog):
    """The normal case: what reaches the log is an area and a count for that area."""
    caplog.set_level(logging.DEBUG)
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)

    client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Northgate"}
    )
    client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Northgate"}
    )
    logged = everything_logged(caplog)

    assert "DAMAGE_REPORT_RECORDED" in logged
    assert "neighbourhood=Northgate" in logged
    assert "open_reports_in_area=2" in logged
    for forbidden in FORBIDDEN_IN_A_LOG:
        assert forbidden not in logged


def test_a_single_report_in_a_sparse_area_still_aggregates(client, application, accounts, caplog):
    """The edge case. One report is a figure of one for that area — never a line that
    identifies the one place it came from, which is exactly when aggregation matters most."""
    caplog.set_level(logging.DEBUG)
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)

    client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Saltmarsh"}
    )
    logged = everything_logged(caplog)

    assert "neighbourhood=Saltmarsh" in logged
    assert "open_reports_in_area=1" in logged
    for forbidden in FORBIDDEN_IN_A_LOG:
        assert forbidden not in logged


def test_the_board_export_carries_no_location_finer_than_a_neighbourhood(
    client, application, accounts
):
    """STEST-009's reachable half: *no asset location appears in full — `asset_id` only.*
    The asset table stores coordinates; the board must not carry them out."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)
    application.state.db.execute(
        "insert into assets (id, scenario_id, external_ids, type, location, match_status,"
        " condition_estimated, created_at)"
        " values ('AS-privacy', ?, '[\"AS-1\"]', 'pump', '{\"lat\": 33.7412, \"lon\": -118.4991}',"
        " 'matched', 0, '2026-08-16T00:00:00Z')",
        (scenario_id,),
    )
    application.state.db.commit()
    client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports",
        json={"neighbourhood": "Northgate", "asset_id": "AS-privacy"},
    )

    body = client.get(f"/api/v1/scenarios/{scenario_id}/jobs").text

    assert "AS-privacy" in body, "the asset is named by identifier, which is permitted"
    assert "33.74" not in body
    assert "-118.49" not in body
    assert "lat" not in body
