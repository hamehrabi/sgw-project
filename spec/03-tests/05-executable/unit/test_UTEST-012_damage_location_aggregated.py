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

**"Aggregated" names a resolution, and a resolution has two ways to be wrong.** The figure that
reaches the log must be the count for *that neighbourhood* — not the count for the whole storm,
which is coarser and says nothing about the area, and not the count for one asset, which is
finer and is the thing REQ-NF-007 exists to forbid. The first version of this file filed every
case into a single neighbourhood with no asset, so all three figures were the same number and
neither wrong rule could be made to fail. The fixtures below keep the three apart on purpose.
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


def insert_report(connection, scenario_id, location, report_id="DR-direct", seq=1):
    connection.execute(
        "insert into damage_reports"
        " (id, scenario_id, location, reported_at, reported_by, status, seq)"
        " values (?, ?, ?, '2026-08-16T00:00:00Z', 'U-1', 'open', ?)",
        (report_id, scenario_id, location, seq),
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
    that lives only in the service layer is one the first refactor removes (ADR-002).

    Matched on `CHECK` rather than on `IntegrityError` alone: every other constraint on this
    table raises the same class, so a bare `raises` would go on passing if the location check
    were dropped and some unrelated column started refusing the row instead. It nearly did —
    adding `seq not null` in migration 008 made every case here raise for the wrong reason.
    """
    scenario_id = a_storm(application, accounts)

    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
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


def an_asset(application, scenario_id, asset_id):
    """An asset in this storm, so a report can name one and the per-asset figure can differ."""
    application.state.db.execute(
        "insert into assets (id, scenario_id, external_ids, type, location, match_status,"
        " condition_estimated, created_at)"
        " values (?, ?, '[\"X\"]', 'pump', '{\"lat\": 33.7412, \"lon\": -118.4991}', 'matched',"
        " 0, '2026-08-16T00:00:00Z')",
        (asset_id, scenario_id),
    )
    application.state.db.commit()
    return asset_id


def test_the_logged_figure_is_the_neighbourhoods_and_not_the_whole_storms(
    client, application, accounts, caplog
):
    """The **coarser** wrong answer. Counting every open report in the storm satisfies every
    single-neighbourhood fixture and tells a reader nothing about the area they asked about.

    Four reports, three of them in Northgate: the area figure is 3 and the storm figure is 4,
    so the two can no longer be the same number by accident.
    """
    caplog.set_level(logging.DEBUG)
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)

    for neighbourhood in ("Northgate", "Harbour West", "Northgate"):
        client.post(
            f"/api/v1/scenarios/{scenario_id}/damage-reports",
            json={"neighbourhood": neighbourhood},
        )
    caplog.clear()
    client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Northgate"}
    )
    logged = everything_logged(caplog)

    assert application.state.db.execute(
        "select count(*) from damage_reports where scenario_id = ?", (scenario_id,)
    ).fetchone()[0] == 4, "four reports in the storm, so the storm figure is a different number"
    assert "open_reports_in_area=3" in logged
    assert "open_reports_in_area=4" not in logged, "that is the storm, not the neighbourhood"


def test_the_logged_figure_is_the_neighbourhoods_and_not_one_assets(
    client, application, accounts, caplog
):
    """The **finer** wrong answer, and the one REQ-NF-007 exists to forbid. An asset is a
    place; a count per asset is a count per place, which is the resolution CON-003 refuses.

    Three reports in Northgate naming three different things — two assets and no asset — so a
    per-asset figure would be 1 where the neighbourhood figure is 3.
    """
    caplog.set_level(logging.DEBUG)
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)
    first = an_asset(application, scenario_id, "AS-north-1")
    second = an_asset(application, scenario_id, "AS-north-2")

    client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports",
        json={"neighbourhood": "Northgate", "asset_id": first},
    )
    client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports",
        json={"neighbourhood": "Northgate", "asset_id": second},
    )
    caplog.clear()
    client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Northgate"}
    )
    logged = everything_logged(caplog)

    assert "open_reports_in_area=3" in logged
    assert "open_reports_in_area=1" not in logged, "that is one asset, not the neighbourhood"
    for forbidden in FORBIDDEN_IN_A_LOG:
        assert forbidden not in logged


def test_the_area_figure_is_the_area_and_neither_of_its_neighbours(
    client, application, accounts
):
    """The same three-way distinction asserted against the function that computes it, with
    three numbers that are all different: 5 in the storm, 3 in Northgate, 1 for the asset."""
    from app.store import dispatch

    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)
    named = an_asset(application, scenario_id, "AS-north-1")

    for neighbourhood, asset_id in (
        ("Northgate", named),
        ("Northgate", None),
        ("Harbour West", None),
        ("Northgate", None),
        ("Saltmarsh", None),
    ):
        client.post(
            f"/api/v1/scenarios/{scenario_id}/damage-reports",
            json={"neighbourhood": neighbourhood, "asset_id": asset_id},
        )

    connection = application.state.db
    in_the_storm = connection.execute(
        "select count(*) from damage_reports where scenario_id = ?", (scenario_id,)
    ).fetchone()[0]
    for_the_asset = connection.execute(
        "select count(*) from damage_reports where scenario_id = ? and asset_id = ?",
        (scenario_id, named),
    ).fetchone()[0]
    for_the_area = dispatch.open_reports_in_area(
        connection, scenario_id, dispatch.location_key("Northgate")
    )

    assert (in_the_storm, for_the_area, for_the_asset) == (5, 3, 1)
    assert for_the_area != in_the_storm, "the storm is coarser than a neighbourhood"
    assert for_the_area != for_the_asset, "an asset is finer than a neighbourhood"


def test_a_duplicate_report_is_not_counted_as_open_work_in_the_area(
    client, application, accounts
):
    """`damage_reports.status` has always permitted `duplicate` and nothing had a reader for
    it, so the area figure counted a repeat call as a second piece of open work (CHG-021).

    Nothing writes the status yet — TASK-008 writes `dismissed`, not this — so it is set
    directly, which is also the only way a reader for it can be asserted today.
    """
    from app.store import dispatch

    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)
    for _ in range(3):
        client.post(
            f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Northgate"}
        )
    connection = application.state.db
    key = dispatch.location_key("Northgate")
    assert dispatch.open_reports_in_area(connection, scenario_id, key) == 3

    repeat = connection.execute(
        "select id from damage_reports where scenario_id = ? order by seq desc limit 1",
        (scenario_id,),
    ).fetchone()["id"]
    connection.execute("update damage_reports set status = 'duplicate' where id = ?", (repeat,))
    connection.commit()

    assert dispatch.open_reports_in_area(connection, scenario_id, key) == 2, (
        "a second call about damage already counted is not a second piece of open work"
    )


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
