"""CHG-042 and CHG-043 — the flood-zone rule's two corrections.

**CHG-042:** FEMA zone D means *flood hazard undetermined*, and a handful of real assets
carry it. Discarding three known factors because the fourth is undetermined loses more
information than it protects — so an unrecognised zone scores at the minimal value **with
a reason that names it**, and nobody reads *minimal flood risk* where the truth is
*unknown flood risk*, because the sentence says which one it is.

**CHG-043:** A, AO and AH are within the same 1%-annual-chance floodplain as AE — the
letters record surveying method, not a different exposure. Without them zone AO fell to
the unrecognised path and scored *minimal*, which is the opposite of the truth.
"""

from datetime import date

from app.loader.records import LoadedAsset
from app.scoring import references
from app.scoring.rank import score_asset

TODAY = date(2026, 8, 16)


def asset(zone):
    return LoadedAsset(
        external_ids=["AS-1"],
        name="Bayside",
        type="substation",
        lat=33.7,
        lon=-118.4,
        install_year=2000,
        flood_zone=zone,
        condition="4",
        condition_source="inspection",
        condition_observed_at="2026-01-05",
        wind_gust_mph=60.0,
    )


# --- CHG-042: unrecognised zones -----------------------------------------------------


def test_zone_d_is_scored_not_unscored():
    ranked = score_asset(asset("D"), today=TODAY)
    assert ranked.score is not None, "an undetermined hazard must not discard three known factors"
    assert ranked.unscored_reason is None


def test_zone_d_scores_the_flood_factor_at_the_minimal_value():
    ranked = score_asset(asset("D"), today=TODAY)
    flood = next(r for r in ranked.reasons if r.factor == "flood_zone")
    minimal = 100.0 * references.WEIGHTS["flood_zone"] * references.FLOOD_ZONE_EXPOSURE["X"]
    assert flood.contribution == round(minimal, 4)


def test_zone_d_carries_a_reason_naming_the_unrecognised_code():
    # Never a silent "minimal flood risk": the sentence says the code was not recognised,
    # so the reader knows the claim is "unknown", not "safe".
    ranked = score_asset(asset("D"), today=TODAY)
    flood = next(r for r in ranked.reasons if r.factor == "flood_zone")
    assert "D" in flood.detail
    assert "not recognised" in flood.detail or "not recognized" in flood.detail


def test_a_recognised_zone_does_not_claim_to_be_unrecognised():
    ranked = score_asset(asset("AE"), today=TODAY)
    flood = next(r for r in ranked.reasons if r.factor == "flood_zone")
    assert "not recognised" not in flood.detail


# --- CHG-043: the A-prefixed zones ---------------------------------------------------


def test_zones_a_ao_and_ah_score_at_the_ae_value():
    ae = references.FLOOD_ZONE_EXPOSURE["AE"]
    for zone in ("A", "AO", "AH"):
        assert references.FLOOD_ZONE_EXPOSURE[zone] == ae, zone
        ranked = score_asset(asset(zone), today=TODAY)
        flood = next(r for r in ranked.reasons if r.factor == "flood_zone")
        assert flood.contribution == round(100.0 * references.WEIGHTS["flood_zone"] * ae, 4)
        # And they are the floodplain, not the unrecognised path.
        assert "not recognised" not in flood.detail


def test_the_weight_set_version_moved_with_the_rule():
    # A ranking stored under the old rule is not comparable with one stored under this
    # one, and WEIGHT_SET_VERSION is what makes that checkable later (ADR-007's register
    # rule: bump on ANY change).
    assert references.WEIGHT_SET_VERSION != "adr-007-v1"
