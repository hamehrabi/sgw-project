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
import re
import sqlite3

import pytest
from app.store import dispatch
from conftest import sign_in

FORBIDDEN_IN_A_LOG = ("street", "avenue", "meter", "account", "33.7", "-118.5")

# The bound the schema and the service must agree on, referenced rather than repeated. Written
# out once here so a reader can see what the cases below are made of; every use goes through
# `dispatch.NEIGHBOURHOOD_MAX`, and `test_one_bound_governs_a_neighbourhoods_length` is what
# ties that constant to the two copies in the schema.
AT_THE_LIMIT = "N" * dispatch.NEIGHBOURHOOD_MAX
OVER_THE_LIMIT = "N" * (dispatch.NEIGHBOURHOOD_MAX + 1)


def a_storm(application, accounts):
    """A scenario row and nothing else — this rule needs no assets to be broken."""
    application.state.db.execute(
        # `content_key` and `seq` are required by migration 013: a storm is identified by
        # what it was loaded from, and has a place in the order storms are listed in
        # (CHG-031, CHG-032). A direct insert has to satisfy the store like any other.
        "insert into scenarios (id, name, source_note, content_key, loaded_by, loaded_at,"
        " forecast_revision, seq)"
        " values ('SC-privacy', 'Privacy storm', 'unit', ?, ?, '2026-08-16T00:00:00Z', 0, 900)",
        ("d" * 64, accounts["admin"]["id"]),
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
        # The fourth clause of the same constraint, which nothing used to reach. `length(trim
        # (...)) between 1 and 120` was exercised by no test at all — no empty neighbourhood,
        # no whitespace-only one, no over-length one, at the store or at the endpoint — and
        # relaxing it to `between 1 and 100000` left all 264 tests green.
        '{"neighbourhood": ""}',
        '{"neighbourhood": "   "}',
        '{"neighbourhood": "\\t\\n"}',
        json.dumps({"neighbourhood": OVER_THE_LIMIT}),
        # CHG-037, and these are written as **raw UTF-8** on purpose. Every clause of the check
        # accepted them: `length` is 1, SQLite's one-argument `trim()` strips spaces only, the
        # five `instr` clauses named char(9) to char(13), and `json(location) = json_object(...)`
        # agreed because both sides held the same raw character. The only thing refusing them was
        # `json.dumps`' `ensure_ascii` default one module away, which escaped the character and
        # tripped the *unrelated* json clause instead — so CON-003's guard against *a location
        # that is not a place* was being held up by a serialiser default, and the day a
        # neighbourhood needs an accent that default changes.
        '{"neighbourhood": " "}',
        '{"neighbourhood": "　"}',
        '{"neighbourhood": "​"}',
        '{"neighbourhood": "﻿"}',
        # Not blank, but not normalised either: a no-break space inside a name is a second
        # spelling of one neighbourhood, and `dispatch.normalise` produces the single-space form.
        # CHG-023's rule — the store refuses what the writer would never have produced.
        '{"neighbourhood": "North gate"}',
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


def test_the_store_accepts_a_neighbourhood_exactly_at_the_bound(application, accounts):
    """The boundary from the permitted side, so the refusals above are refusing a length rather
    than refusing long names in general."""
    scenario_id = a_storm(application, accounts)

    insert_report(application.state.db, scenario_id, json.dumps({"neighbourhood": AT_THE_LIMIT}))
    application.state.db.commit()

    assert application.state.db.execute(
        "select count(*) from damage_reports"
    ).fetchone()[0] == 1


def test_the_store_refuses_a_repair_job_key_over_the_bound(application, accounts):
    """The same bound on the other column. `repair_jobs.location_key` carries its own copy of
    `between 1 and 120` (CHG-023), and a key is derived from a neighbourhood, so the two have
    to be the same number or one of them is unreachable."""
    scenario_id = a_storm(application, accounts)

    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        application.state.db.execute(
            "insert into repair_jobs"
            " (id, scenario_id, status, location_key, created_at, updated_at, seq)"
            " values ('RJ-long', ?, 'pending', ?, '2026-08-16T00:00:00Z',"
            " '2026-08-16T00:00:00Z', 1)",
            (scenario_id, OVER_THE_LIMIT.lower()),
        )
    application.state.db.rollback()


BOUND = re.compile(r"between\s+1\s+and\s+(\d+)")


def test_one_bound_governs_a_neighbourhoods_length(application):
    """**The bound was three hard-coded copies with nothing tying them together.**

    `damage_reports.location`, `repair_jobs.location_key` and `dispatch.NEIGHBOURHOOD_MAX` each
    carried 120 and none of them knew about the others. Leaving the schema at 120 and setting
    the service constant to 5000 turns the `400 validation_error` the API contract specifies
    into a `500 internal_error` for a 121-character neighbourhood, and the whole suite stayed
    green through that. This is the tie: move any one of the three and it is red.
    """
    schema = {
        row["name"]: row["sql"]
        for row in application.state.db.execute(
            "select name, sql from sqlite_master where type = 'table'"
        )
    }

    # The haystack first. An enumeration that stopped returning tables would make every
    # assertion below vacuous, and "no bound disagreed" is worth nothing without "bounds exist".
    assert {"damage_reports", "repair_jobs"} <= set(schema)
    found = {
        name: [int(value) for value in BOUND.findall(schema[name])]
        for name in ("damage_reports", "repair_jobs")
    }
    assert all(found.values()), f"no length bound in the schema at all: {found}"

    for name, bounds in found.items():
        assert bounds == [dispatch.NEIGHBOURHOOD_MAX] * len(bounds), (
            f"{name} bounds a neighbourhood at {bounds} and the service refuses at "
            f"{dispatch.NEIGHBOURHOOD_MAX} — the endpoint's 400 becomes a 500 between them"
        )


def test_the_endpoint_refuses_an_over_length_neighbourhood_as_a_400_not_a_500(
    client, application, accounts
):
    """The contract half of the same tie, read from the caller's side. A neighbourhood one
    character over the bound is a caller mistake and must be answered as one — a `500` here
    says the platform broke, which sends a dispatcher to the wrong person during a storm."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)

    refused = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports",
        json={"neighbourhood": OVER_THE_LIMIT},
    )
    accepted = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": AT_THE_LIMIT}
    )

    assert refused.status_code == 400, refused.text
    assert refused.json()["code"] == "validation_error"
    # The permitted side beside it, so "refuses over-length" is not satisfied by refusing
    # everything long.
    assert accepted.status_code == 201, accepted.text
    assert application.state.db.execute(
        "select count(*) from damage_reports"
    ).fetchone()[0] == 1


@pytest.mark.parametrize(
    "blank",
    [
        "",
        "   ",
        "\t\n ",
        # CHG-037. `" ".join(value.split())` collapsed Python's idea of whitespace, which is
        # neither the schema's nor the browser's: U+200B and U+FEFF survived it, so a
        # neighbourhood of one invisible character reached the store and was answered with a
        # `500 internal_error` where the contract specifies a `400 validation_error` — the same
        # gap this file already records between a bound and its copy.
        " ",
        "　",
        "​",
        "﻿",
    ],
    ids=["empty", "spaces", "ascii-blanks", "U+00A0", "U+3000", "U+200B", "U+FEFF"],
)
def test_the_endpoint_refuses_a_neighbourhood_that_is_not_a_place(
    client, application, accounts, blank
):
    """Empty and whitespace-only, at the endpoint as well as at the store. A report filed
    against no place at all is work nobody can be sent to."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)

    refused = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": blank}
    )

    assert refused.status_code == 400
    assert refused.json()["code"] == "validation_error"
    assert application.state.db.execute(
        "select count(*) from damage_reports"
    ).fetchone()[0] == 0


def test_the_endpoint_refuses_a_neighbourhood_whose_key_would_be_too_long(
    client, application, accounts
):
    """The silent case for the bound: casefolding can make a string **longer**. `'ß'.casefold()`
    is `'ss'`, so a neighbourhood the display column accepts produces a `location_key` twice as
    long that `repair_jobs` refuses — a `500` where the contract specifies a `400`, and only
    measuring both forms catches it."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)

    grows = "ß" * dispatch.NEIGHBOURHOOD_MAX
    assert len(grows) == dispatch.NEIGHBOURHOOD_MAX, "the display name is inside the bound"
    assert len(dispatch.location_key(grows)) > dispatch.NEIGHBOURHOOD_MAX, "its key is not"

    refused = client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": grows}
    )

    assert refused.status_code == 400, refused.text
    assert application.state.db.execute(
        "select count(*) from damage_reports"
    ).fetchone()[0] == 0


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


def test_an_open_report_with_no_repair_job_is_counted_in_its_own_neighbourhood(
    client, application, accounts, caplog
):
    """**CHG-022, and the figure was wrong in the direction that under-reports.**

    `open_reports_in_area` was an INNER join through `repair_jobs`, so a report whose
    `repair_job_id` is null — a state `database-design.md` §3 permits and §1 describes — was
    missing from the count entirely. Two open reports in one neighbourhood logged
    `open_reports_in_area=1`, and a dispatcher reading that figure sees half the calls.

    Three numbers again, all different, so no coarser or finer answer can pass by accident:
    3 open in the storm, 2 in Northgate, 1 of those attached to a job.
    """
    caplog.set_level(logging.DEBUG)
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)

    client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Harbour West"}
    )
    insert_report(
        application.state.db,
        scenario_id,
        json.dumps({"neighbourhood": "Northgate"}),
        report_id="DR-no-job",
        seq=90,
    )
    application.state.db.commit()
    caplog.clear()

    client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Northgate"}
    )
    logged = everything_logged(caplog)

    connection = application.state.db
    assert connection.execute(
        "select count(*) from damage_reports where scenario_id = ? and status = 'open'",
        (scenario_id,),
    ).fetchone()[0] == 3, "three open in the storm, so the storm figure is a different number"
    assert connection.execute(
        "select count(*) from damage_reports where scenario_id = ?"
        " and repair_job_id is not null and status = 'open'",
        (scenario_id,),
    ).fetchone()[0] == 2, "and two of them hang off a job at all"
    assert dispatch.open_reports_in_area(
        connection, scenario_id, dispatch.location_key("Northgate")
    ) == 2
    assert "open_reports_in_area=2" in logged
    assert "open_reports_in_area=1" not in logged, (
        "that is the joined reports only — the unattached call is on nobody's screen"
    )


def test_a_report_with_no_job_in_another_area_is_not_counted_here(
    client, application, accounts
):
    """The silent case for the fix: counting *every* unattached report regardless of where it
    came from would satisfy the test above and turn a neighbourhood figure into a storm figure
    the moment a job is missing."""
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    scenario_id = a_storm(application, accounts)

    insert_report(
        application.state.db,
        scenario_id,
        json.dumps({"neighbourhood": "Saltmarsh"}),
        report_id="DR-elsewhere",
        seq=91,
    )
    application.state.db.commit()
    client.post(
        f"/api/v1/scenarios/{scenario_id}/damage-reports", json={"neighbourhood": "Northgate"}
    )

    connection = application.state.db
    assert dispatch.open_reports_in_area(
        connection, scenario_id, dispatch.location_key("Northgate")
    ) == 1
    assert dispatch.open_reports_in_area(
        connection, scenario_id, dispatch.location_key("Saltmarsh")
    ) == 1


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
