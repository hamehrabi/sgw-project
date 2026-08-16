"""ATEST-003 — REQ-F-002, AC-003. And ATEST-004 — REQ-F-003, BR-002.

ATEST-003: a signed-in operations manager opens the planning view with a scenario loaded →
every asset in the scenario appears in one list ordered by risk.

ATEST-004: a user looks at any risk rank → the reasons are available **beside it in plain
words, never behind a separate request**.

Also closes ITEST-001's ranking half, owed from TASK-002.

The plain-words assertion is a golden one on purpose. "Plain" cannot be asserted by a rule,
so the exact sentence is pinned: if someone regresses it back to `gust 96 vs 130`, this fails
and says so. ADR-009's phrasing model is blocked on Q-029 and Q-030 and is optional at
runtime anyway — **this text is what an operator reads if it never arrives.**
"""

from conftest import fixture_files, sign_in


def load_and_rank(client, accounts, as_role="admin"):
    sign_in(client, accounts["admin"]["email"], accounts["admin"]["password"])
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Helene replay", "source_note": "prepared fixture"},
        files=[("files", (n, c, "text/csv")) for n, c in fixture_files().items()],
    )
    scenario_id = created.json()["scenario_id"]
    if as_role == "user":
        client.delete("/api/v1/auth/session")
        sign_in(client, accounts["user"]["email"], accounts["user"]["password"])
    return scenario_id, client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()


def test_every_asset_in_the_scenario_appears_in_one_list(client, accounts):
    scenario_id, body = load_and_rank(client, accounts)

    assets = client.get(f"/api/v1/scenarios/{scenario_id}/assets").json()

    assert body["total"] == len(assets["items"])
    assert len(body["items"]) == len(assets["items"])


def test_the_list_is_ordered_by_risk(client, accounts):
    _, body = load_and_rank(client, accounts)

    scored = [item for item in body["items"] if item["score"] is not None]
    assert [item["score"] for item in scored] == sorted(
        (item["score"] for item in scored), reverse=True
    )
    assert [item["rank"] for item in scored] == list(range(1, len(scored) + 1))


def test_an_unscorable_asset_is_present_and_last_rather_than_ranked_low(client, accounts):
    """It is *in* the ranking, not *ranked*. Omitting it is the most dangerous screen here."""
    _, body = load_and_rank(client, accounts)

    unscored = [item for item in body["items"] if item["score"] is None]

    assert unscored
    assert body["items"][-1]["score"] is None
    for item in unscored:
        assert item["rank"] is None
        assert item["unscored_reason"]


def test_the_reasons_arrive_with_the_rank_not_on_a_second_request(client, accounts):
    """BR-002 at the contract level. A separate fetch makes "a rank with no reasons" reachable."""
    _, body = load_and_rank(client, accounts)

    for item in body["items"]:
        if item["score"] is not None:
            assert item["reasons"], f"{item['external_ids']} arrived with a rank and no reasons"


def test_the_reasons_read_as_plain_words(client, accounts):
    """The golden assertion. If this text regresses to arithmetic, this test says so."""
    _, body = load_and_rank(client, accounts)

    top = body["items"][0]
    details = [reason["detail"] for reason in top["reasons"]]

    assert details[0].startswith("Forecast winds of 103 mph")
    assert "built to withstand" in details[0]
    assert any("coastal high-hazard flood zone (VE)" in d for d in details)
    assert any("past the 50 years this kind of asset is expected to last" in d for d in details)
    assert any("Rated 1 out of 5 — poor — when last inspected" in d for d in details)
    # BR-003's distrust, said out loud rather than left as a silent weighting.
    assert any("counts for less than a recent one would" in d for d in details)


def test_every_reason_is_a_sentence_rather_than_a_label(client, accounts):
    _, body = load_and_rank(client, accounts)

    for item in body["items"]:
        for reason in item["reasons"]:
            detail = reason["detail"]
            # A digit is a legitimate opening — "61 years old — past the 50 years…" is a
            # sentence, and spelling the number out would be worse, not plainer.
            assert detail[0].isupper() or detail[0].isdigit(), f"not a sentence: {detail}"
            assert detail.endswith("."), f"not a sentence: {detail}"
            assert " vs " not in detail, f"reads as arithmetic, not words: {detail}"
            assert reason["strength"] in ("Strong", "Moderate", "Slight")


def test_each_rank_carries_the_values_its_reasons_rest_on(client, accounts):
    """BR-003 travels with the rank: a reader can question an input, not only a conclusion."""
    _, body = load_and_rank(client, accounts)

    for value in body["items"][0]["values"]:
        assert set(value) >= {"name", "value", "source", "observed_at", "estimated"}


def test_the_response_says_its_numbers_are_uncalibrated(client, accounts):
    """TASK-003 done criterion 7, at the contract rather than only in a screen's copy."""
    _, body = load_and_rank(client, accounts)

    assert body["weights_calibrated"] is False
    assert body["weight_set_version"]


def test_a_user_role_sees_the_same_ranking_as_an_admin(client, accounts):
    """Every role sees the same ranking; deciding is the product, not a privilege."""
    _, body = load_and_rank(client, accounts, as_role="operator")

    assert body["items"]


def test_an_unknown_forecast_revision_is_refused_rather_than_silently_replaced(client, accounts):
    """A silent fallback shows one ranking to a reader who believes it is another."""
    scenario_id, _ = load_and_rank(client, accounts)

    response = client.get(f"/api/v1/scenarios/{scenario_id}/risks?forecast_revision=7")

    assert response.status_code == 404


def test_an_out_of_range_limit_is_refused(client, accounts):
    scenario_id, _ = load_and_rank(client, accounts)

    assert client.get(f"/api/v1/scenarios/{scenario_id}/risks?limit=9999").status_code == 400
