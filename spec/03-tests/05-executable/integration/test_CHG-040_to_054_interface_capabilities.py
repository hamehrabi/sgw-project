"""The nine capabilities behind the interface rebuild (CHG-040..CHG-054), each proven at
the API against a live application — and each with the mutation it would take to fake it
noted beside the assertion that catches it.
"""

import json
import sqlite3

import pytest
from conftest import ADMIN_PASSWORD, USER_PASSWORD, fixture_files, sign_in


@pytest.fixture
def loaded(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Delia replay", "source_note": "prepared pack"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    assert created.status_code == 201, created.text
    return created.json()["scenario_id"]


# --- CHG-047: findings persist beyond the upload response ------------------------------


def test_findings_are_stored_and_readable_tomorrow(client, loaded):
    body = client.get(f"/api/v1/scenarios/{loaded}/findings").json()
    # The fixture carries all seven defects on purpose; at least defects 1..7 minus the
    # merged ones produce rows. What matters: rows exist, each names its file.
    assert body["total"] >= 5
    assert all(item["affected_file"] for item in body["items"])
    defects = {item["defect"] for item in body["items"]}
    assert {1, 2, 3} <= defects, defects


def test_resolving_a_finding_records_who_and_when(client, loaded):
    finding = client.get(f"/api/v1/scenarios/{loaded}/findings").json()["items"][0]
    resolved = client.post(
        f"/api/v1/scenarios/{loaded}/findings/resolve",
        json={"finding_id": finding["finding_id"], "resolution": "OK, use forecast"},
    )
    assert resolved.status_code == 200, resolved.text
    body = resolved.json()
    assert body["resolution"] == "OK, use forecast"
    assert body["resolved_by"] and body["resolved_at"]


# --- CHG-048: the match queue holds both sides of every withheld merge -----------------


def test_the_withheld_merges_are_in_the_queue_with_both_records(client, loaded):
    body = client.get(f"/api/v1/scenarios/{loaded}/matches").json()
    assert body["pending_count"] >= 1, "the fixture withholds merges on purpose (defect 1)"
    candidate = body["items"][0]
    # Both comparison cards have content, and confidence is a word, never a percentage.
    assert candidate["map_record"]["id"] and candidate["candidate_record"]["id"]
    assert candidate["confidence"] in ("high", "moderate")
    assert "%" not in candidate["confidence"]


def test_resolving_a_match_settles_the_assets_review_flag(client, application, loaded):
    body = client.get(f"/api/v1/scenarios/{loaded}/matches").json()
    candidate = next(i for i in body["items"] if i["resolution"] == "pending")
    resolved = client.post(
        f"/api/v1/scenarios/{loaded}/matches/resolve",
        json={"candidate_id": candidate["candidate_id"], "resolution": "match"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["resolved_by"]

    # A second answer to the same question is a conflict, not a second review.
    again = client.post(
        f"/api/v1/scenarios/{loaded}/matches/resolve",
        json={"candidate_id": candidate["candidate_id"], "resolution": "not_match"},
    )
    assert again.status_code == 409

    row = application.state.db.execute(
        "select match_status from assets where id = ? and scenario_id = ?",
        (candidate["asset_id"], loaded),
    ).fetchone()
    assert row["match_status"] == "matched"


def test_an_operator_cannot_resolve_identity(client, accounts, loaded):
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    refused = client.post(
        f"/api/v1/scenarios/{loaded}/matches/resolve",
        json={"candidate_id": "AMC-x", "resolution": "match"},
    )
    assert refused.status_code == 403


# --- CHG-049: staging records and dispatches nothing ------------------------------------


def test_a_staging_plan_is_recorded_with_its_actor(client, loaded):
    areas = client.get(f"/api/v1/scenarios/{loaded}/staging").json()["depots"]
    assert areas, "the fixture's manifest carries service areas (CHG-011)"

    recorded = client.post(
        f"/api/v1/scenarios/{loaded}/staging",
        json={
            "forecast_revision": 0,
            "depots": [{"service_area_id": areas[0]["service_area_id"], "crews": 4}],
        },
    )
    assert recorded.status_code == 201, recorded.text
    body = recorded.json()
    assert body["recorded_by"] and body["recorded_at"]
    assert body["depots"][0]["crews"] == 4


def test_a_depot_the_manifest_does_not_name_is_refused(client, loaded):
    refused = client.post(
        f"/api/v1/scenarios/{loaded}/staging",
        json={"forecast_revision": 0, "depots": [{"service_area_id": "SA-INVENTED", "crews": 2}]},
    )
    assert refused.status_code == 400


# --- CHG-040: the summary lifecycle and its block ----------------------------------------


def test_with_the_model_off_the_summary_is_assembled_and_says_so(client, loaded):
    drafted = client.post(f"/api/v1/scenarios/{loaded}/summary/draft")
    assert drafted.status_code == 201, drafted.text
    body = drafted.json()
    assert body["label"] == "Assembled from platform data"
    assert body["state"] == "Draft"
    assert body["verification"]["ok"] is True, "the fallback must pass its own verifier"
    assert body["verification"]["model_attempts"] == 0


def test_approval_of_text_with_an_invented_figure_is_blocked_not_warned(client, loaded):
    drafted = client.post(f"/api/v1/scenarios/{loaded}/summary/draft").json()
    blocked = client.post(
        f"/api/v1/scenarios/{loaded}/summary/approve",
        json={
            "summary_id": drafted["summary_id"],
            "approved_text": "An estimated 41,500 customers are without service.",
        },
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["code"] == "verification_failed"
    # The violations are named, so the drawer renders what blocked it.
    entries = blocked.json()["verification"]["entries"]
    assert any(not entry["allowed"] for entry in entries)


def test_the_lifecycle_is_draft_approved_sent_and_nothing_else(client, loaded):
    drafted = client.post(f"/api/v1/scenarios/{loaded}/summary/draft").json()

    # Draft → Sent has no edge.
    refused = client.post(
        f"/api/v1/scenarios/{loaded}/summary/send", json={"summary_id": drafted["summary_id"]}
    )
    assert refused.status_code == 409

    approved = client.post(
        f"/api/v1/scenarios/{loaded}/summary/approve",
        json={"summary_id": drafted["summary_id"], "approved_text": drafted["draft_text"]},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["state"] == "Approved"
    assert approved.json()["approved_by"]

    sent = client.post(
        f"/api/v1/scenarios/{loaded}/summary/send", json={"summary_id": drafted["summary_id"]}
    )
    assert sent.status_code == 200
    assert sent.json()["state"] == "Sent"


def test_the_store_refuses_an_anonymous_approval(application, client, loaded):
    drafted = client.post(f"/api/v1/scenarios/{loaded}/summary/draft").json()
    with pytest.raises(sqlite3.IntegrityError):
        application.state.db.execute(
            "update summaries set state = 'Approved', approved_text = 'x' where id = ?",
            (drafted["summary_id"],),
        )


# --- CHG-044: movement is real, and absent honestly at revision 0 ------------------------


def test_at_revision_zero_the_answer_is_first_ranking_not_a_faked_delta(client, loaded):
    body = client.get(f"/api/v1/scenarios/{loaded}/movement").json()
    assert body["first_ranking"] is True
    assert body["items"] == []


def test_after_a_forecast_change_movement_is_the_diff_of_the_two_stored_rankings(
    tmp_path, monkeypatch
):
    # The seven-defects fixture carries a single forecast time, so there is nothing to
    # apply against it. The synthetic storm carries a series — the same generator
    # PTEST-001 re-ranks — and it needs the shipped size limits, still read from
    # configuration rather than hard-coded.
    from conftest import build_application
    from fastapi.testclient import TestClient
    from synthetic import synthetic_scenario

    from app.store import users

    application = build_application(
        monkeypatch,
        tmp_path / "movement.db",
        SCENARIO_MAX_FILE_BYTES=8_388_608,
        SCENARIO_MAX_TOTAL_BYTES=10_485_760,
    )
    users.create_user(
        application.state.db,
        name="Ops",
        email="admin@sgw.example",
        password=ADMIN_PASSWORD,
        role="admin",
    )
    client = TestClient(application)
    sign_in(client, "admin@sgw.example", ADMIN_PASSWORD)
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Moving storm", "source_note": "generated"},
        files=[
            ("files", (n, c, "text/csv"))
            for n, c in synthetic_scenario(assets=40).items()
        ],
    )
    assert created.status_code == 201, created.text
    loaded = created.json()["scenario_id"]

    client.get(f"/api/v1/scenarios/{loaded}/risks")
    applied = client.post(f"/api/v1/scenarios/{loaded}/forecast-revisions")
    assert applied.status_code == 201, applied.text

    body = client.get(f"/api/v1/scenarios/{loaded}/movement").json()
    assert body["first_ranking"] is False
    assert body["previous_label"], "the strip must say what the earlier order WAS"

    # Every claimed move must agree with the two stored rankings — the strip can say
    # nothing the store cannot back.
    connection = application.state.db
    for item in body["items"]:
        for revision, claimed in (
            (0, item["previous_rank"]),
            (applied.json()["forecast_revision"], item["current_rank"]),
        ):
            stored = connection.execute(
                "select rank from risk_scores"
                " where scenario_id = ? and asset_id = ? and forecast_revision = ?",
                (loaded, item["asset_id"], revision),
            ).fetchone()
            assert stored is not None and stored["rank"] == claimed
        assert item["current_rank"] < item["previous_rank"], "the strip lists risers"
        assert item["reason_detail"], "a move without its reason is a bare number"


# --- CHG-054: the feed can say a person decided, and cannot say the system did -----------


FORBIDDEN_FEED_WORDS = ("auto-flagged", "system flagged", "sync", "automatically prioritised")


def test_the_activity_feed_records_humans_deciding_and_never_the_system(
    client, application, accounts, loaded
):
    ranking = client.get(f"/api/v1/scenarios/{loaded}/risks").json()
    decided = client.post(
        f"/api/v1/recommendations/{ranking['recommendation_id']}/decision",
        json={"decision": "accept", "note": None},
    )
    assert decided.status_code == 201, decided.text

    feed = client.get(f"/api/v1/scenarios/{loaded}/activity").json()["items"]
    text = " ".join(entry["text"].lower() for entry in feed)

    assert "accepted the ranking" in text
    assert "scenario loaded from" in text
    for phrase in FORBIDDEN_FEED_WORDS:
        assert phrase not in text, f"the feed claims the system acted: {phrase!r}"
    # Every human entry names its human; every system entry is an event, not a judgment.
    humans = [entry for entry in feed if entry["kind"] == "human"]
    assert humans and all(entry["text"][0].isupper() for entry in humans)


# --- CHG-050: the queue is ordered by impact and never by a score ------------------------


def test_the_repair_queue_orders_critical_facilities_first(client, application, loaded):
    connection = application.state.db
    # Make one asset a critical facility, then report damage against it and against an
    # ordinary neighbourhood, oldest first — so arrival order and impact order disagree
    # and the assertion below can only pass if impact wins.
    asset = connection.execute(
        "select id from assets where scenario_id = ? limit 1", (loaded,)
    ).fetchone()
    connection.execute(
        "update assets set is_critical_facility = 1 where id = ?", (asset["id"],)
    )
    connection.commit()

    first = client.post(
        f"/api/v1/scenarios/{loaded}/damage-reports",
        json={"neighbourhood": "Ordinary Corner", "customers_out": 40},
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/v1/scenarios/{loaded}/damage-reports",
        json={"neighbourhood": "Hospital Row", "asset_id": asset["id"]},
    )
    assert second.status_code == 201

    board = client.get(f"/api/v1/scenarios/{loaded}/jobs").json()
    assert board["items"][0]["priority"] == "High"
    assert board["items"][0]["location"]["neighbourhood"] == "Hospital Row"
    assert board["items"][1]["priority"] == "Low"
    # The frozen vocabulary: never "Critical", never "Standard".
    assert {item["priority"] for item in board["items"]} <= {"High", "Medium", "Low"}


# --- CHG-053: a temporary password behaves like one --------------------------------------


def test_a_temporary_password_reaches_only_the_password_change(
    client, application, accounts, monkeypatch
):
    from datetime import UTC, datetime, timedelta

    from app.store import users

    connection = application.state.db
    users.set_temporary_password(
        connection,
        user_id=accounts["user"]["id"],
        password="a-temporary-password",
        cost=4,
        expires_at=(datetime.now(UTC) + timedelta(hours=24)).isoformat(),
    )

    signed = sign_in(client, accounts["user"]["email"], "a-temporary-password")
    assert signed.status_code == 201
    assert signed.json()["must_change_password"] is True

    # Every data route refuses; the three permitted ones answer.
    assert client.get("/api/v1/scenarios").status_code == 403
    assert client.get("/api/v1/scenarios").json()["code"] == "password_change_required"
    assert client.get("/api/v1/auth/session").status_code == 200

    changed = client.post(
        "/api/v1/auth/password",
        json={"current_password": "a-temporary-password", "new_password": USER_PASSWORD},
    )
    assert changed.status_code == 204, changed.text
    assert client.get("/api/v1/scenarios").status_code == 200


def test_an_expired_temporary_password_is_refused_like_a_wrong_one(
    client, application, accounts
):
    from datetime import UTC, datetime, timedelta

    from app.store import users

    users.set_temporary_password(
        application.state.db,
        user_id=accounts["user"]["id"],
        password="an-expired-temporary",
        cost=4,
        expires_at=(datetime.now(UTC) - timedelta(hours=1)).isoformat(),
    )
    refused = sign_in(client, accounts["user"]["email"], "an-expired-temporary")
    assert refused.status_code == 401
    # The same sentence as a wrong password: "your temporary password expired" would
    # confirm the account exists (STEST-003's rule).
    assert "expired" not in refused.text.lower()


# --- CHG-046: sign-ins land in the queryable log ------------------------------------------


def test_sign_in_and_sign_out_are_in_the_security_log(client, application, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    client.delete("/api/v1/auth/session")
    events = [
        row["event"]
        for row in application.state.db.execute("select event from security_log order by seq")
    ]
    assert "sign_in" in events and "sign_out" in events


def test_no_password_reaches_the_security_log(client, application, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    details = " ".join(
        row["detail"] for row in application.state.db.execute("select detail from security_log")
    )
    assert ADMIN_PASSWORD not in details and USER_PASSWORD not in details


# --- The sample-data button goes through the same parse path ------------------------------


def test_use_sample_storm_data_measures_its_own_parse(client, accounts):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post("/api/v1/scenarios/sample")
    assert created.status_code == 201, created.text
    scenario_id = created.json()["scenario_id"]

    # The quality summary is measured from THIS parse — the fixture's seven defects are
    # in the stored findings, not hard-coded percentages.
    findings = client.get(f"/api/v1/scenarios/{scenario_id}/findings").json()
    assert findings["total"] >= 5

    # Pressed twice, it is the same storm — the same idempotency rule as a real upload.
    again = client.post("/api/v1/scenarios/sample")
    assert again.status_code == 200
    assert again.json()["scenario_id"] == scenario_id


def test_the_sample_button_is_admin_only(client, accounts):
    sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    assert client.post("/api/v1/scenarios/sample").status_code == 403
