"""CHG-059 — the per-asset summary's guardrail, tested against strings.

The asset path reuses the situation summary's pure verifier machinery with one recorded
difference: `mph` is not forbidden vocabulary here, because a gust reason legitimately
states the gust in mph and the figure check already pins every number to a supplied
value. Everything else — invented figures, invented proper nouns, the rest of the
forbidden vocabulary — is refused exactly as it is on the situation path.
"""

from app.summary.asset_draft import template_asset_text
from app.summary.verify import verify, verify_asset

SCORED_FIGURES = {
    "asset_type": "line",
    "risk_band": "High",
    "rank": 3,
    "ranked_total": 220,
    "reasons": [
        {
            "factor": "gust_vs_design",
            "strength": "Strong",
            "contribution": 38.2,
            "detail": (
                "Forecast winds of 123 mph meet or exceed the 90 mph this line was "
                "built to withstand."
            ),
        },
        {
            "factor": "flood_zone",
            "strength": "Moderate",
            "contribution": 17.5,
            "detail": "Sits inside the mapped 100-year floodplain (zone AE).",
        },
        {
            "factor": "age_vs_service_life",
            "strength": "Slight",
            "contribution": 6.1,
            "detail": "34 years old, of an expected 50-year life.",
        },
    ],
    "unscored_reason": None,
    "forecast_issued_at": "2026-09-15T19:00:00Z",
}

UNSCORED_FIGURES = {
    "asset_type": "pump",
    "risk_band": None,
    "rank": None,
    "ranked_total": 219,
    "reasons": [],
    "unscored_reason": "its flood zone is blank, so its flood exposure is unknown",
    "forecast_issued_at": "2026-09-15T19:00:00Z",
}


def test_a_draft_built_from_the_supplied_reasons_passes():
    draft = (
        "Ranked 3 of 220 and rated high. Forecast winds of 123 mph meet or exceed the "
        "90 mph this line was built to withstand. Sits inside the mapped 100-year "
        "floodplain (zone AE)."
    )
    verdict = verify_asset(draft, SCORED_FIGURES)
    assert verdict["ok"], [e for e in verdict["entries"] if not e["allowed"]]


def test_mph_is_allowed_here_and_still_forbidden_on_the_situation_path():
    """The one recorded difference between the two paths — and only that one."""
    text = "Gusts of 123 mph are stated in the data."
    figures = {"x": "gusts of 123 mph are stated"}
    assert verify_asset(text, figures)["ok"]
    assert not verify(text, figures)["ok"], "the situation path still refuses mph"


def test_an_invented_figure_is_refused():
    verdict = verify_asset(
        "Forecast winds of 160 mph threaten this line.", SCORED_FIGURES
    )
    assert not verdict["ok"]
    assert any(e["kind"] == "figure" and e["token"] == "160" and not e["allowed"]
               for e in verdict["entries"])


def test_an_invented_proper_noun_is_refused():
    verdict = verify_asset(
        "The exposure at Bayside Substation is severe.", SCORED_FIGURES
    )
    assert not verdict["ok"]
    assert any(e["kind"] == "noun" and not e["allowed"] for e in verdict["entries"])


def test_the_rest_of_the_forbidden_vocabulary_still_applies():
    for sentence in (
        "Telemetry indicates rising exposure.",
        "Predictive analysis of 3 of 220 assets.",
        "The algorithm rated it 3 of 220.",
    ):
        assert not verify_asset(sentence, SCORED_FIGURES)["ok"], sentence


def test_one_bad_claim_among_good_ones_still_fails_the_whole_draft():
    """Kills the all→any mutation: a mostly-true draft is not a true draft."""
    draft = (
        "Ranked 3 of 220 and rated high. Forecast winds of 999 mph meet or exceed the "
        "90 mph this line was built to withstand."
    )
    verdict = verify_asset(draft, SCORED_FIGURES)
    assert any(e["allowed"] for e in verdict["entries"]), "the good claims are judged good"
    assert not verdict["ok"]


def test_the_template_passes_the_verifier_by_construction_when_scored():
    text = template_asset_text(SCORED_FIGURES)
    verdict = verify_asset(text, SCORED_FIGURES)
    assert verdict["ok"], [e for e in verdict["entries"] if not e["allowed"]]
    assert "123" in text, "the strongest reason's own words are in the fallback"


def test_the_template_passes_the_verifier_by_construction_when_unscored():
    text = template_asset_text(UNSCORED_FIGURES)
    verdict = verify_asset(text, UNSCORED_FIGURES)
    assert verdict["ok"], [e for e in verdict["entries"] if not e["allowed"]]
    assert "not been judged low risk" in text
