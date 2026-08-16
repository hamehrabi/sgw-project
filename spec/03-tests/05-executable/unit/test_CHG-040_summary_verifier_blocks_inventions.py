"""CHG-040 — the situation summary's guardrail is code, and these are its teeth.

Every case here is a **real failure the client's own testing recorded**, fed to the
verifier as a draft. Each must be caught, each catch must name what it caught, and a
mismatched figure must block rather than warn. The verifier is pure — a string and the
supplied figures in, a verdict out — so nothing here builds an application or reaches a
network.
"""

from app.summary.verify import verify

# The fixed set the model was allowed to see. Every test feeds the same one, so what
# varies is only the draft under judgment.
FIGURES = {
    "storm_name": "Hurricane Delia",
    "open_incidents": 34,
    "critical_facilities_affected": 3,
    "crews_deployed": 12,
    "crews_total": 18,
    "customers_out": 41200,
    "high_risk_count": 12,
    "top_asset_name": "Bayside Substation",
    "top_asset_impact": "Sits in a high-risk flood zone (FEMA VE)",
    "forecast_issued_at": "2026-08-16T14:20:00Z",
}


def violations(text):
    return [entry for entry in verify(text, FIGURES)["entries"] if not entry["allowed"]]


# ---------------------------------------------------------------------------------------
# The six real failures, one by one.


def test_an_invented_place_is_caught():
    found = violations("Hurricane Delia is making landfall along the eastern seaboard.")
    assert found, "an invented place sailed through"
    tokens = " ".join(entry["token"].lower() for entry in found)
    assert "seaboard" in tokens or "landfall" in tokens


def test_an_invented_figure_is_caught():
    found = violations("The storm brings sustained winds of 115mph to the region.")
    assert any(entry["token"] == "115" for entry in found), "115 is in no supplied figure"
    tokens = " ".join(entry["token"].lower() for entry in found)
    assert "sustained winds" in tokens or "mph" in tokens


def test_an_invented_claim_about_geography_is_caught():
    found = violations("Outages are reported across three counties.")
    assert found, "'three counties' asserts a count and a geography nobody supplied"


def test_forbidden_vocabulary_predictive_models_is_caught():
    found = violations("12 additional assets identified based on predictive structural models.")
    tokens = " ".join(entry["token"].lower() for entry in found)
    assert "predictive" in tokens or "models" in tokens


def test_forbidden_vocabulary_telemetry_is_caught():
    found = violations("Current system telemetry indicates 34 active incidents.")
    tokens = " ".join(entry["token"].lower() for entry in found)
    assert "telemetry" in tokens


def test_a_mismatched_figure_is_caught():
    # The platform says 41,200. A draft that says 41,500 is not approximately right —
    # it is a number the data does not hold, under the platform's name.
    found = violations("An estimated 41,500 customers are without service.")
    assert any(entry["token"].replace(",", "") == "41500" for entry in found)


# ---------------------------------------------------------------------------------------
# What must SURVIVE: a draft built from the supplied figures alone.

CLEAN = (
    "There are 34 open incidents, and 3 involve critical facilities. "
    "12 of 18 crews are working. An estimated 41,200 customers are without service. "
    "12 assets are rated high risk, led by Bayside Substation."
)


def test_a_draft_using_only_supplied_figures_passes():
    result = verify(CLEAN, FIGURES)
    assert result["ok"], [e for e in result["entries"] if not e["allowed"]]


def test_every_extracted_figure_is_in_the_result_not_a_fixed_four():
    # The review drawer renders every extracted figure with its platform value. A fixed
    # four-row table would hide the fifth invention.
    result = verify(CLEAN, FIGURES)
    figures = [e for e in result["entries"] if e["kind"] == "figure"]
    assert len(figures) >= 6


def test_the_verdict_is_the_conjunction_of_its_entries():
    # ok cannot be true while any entry is disallowed — the mutation this catches is a
    # verifier that lists the violation and approves anyway.
    result = verify("Emergency protocols have been fully activated.", FIGURES)
    assert not result["ok"]
    assert any(not entry["allowed"] for entry in result["entries"])
