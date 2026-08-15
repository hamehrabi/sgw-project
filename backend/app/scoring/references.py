"""Every number the scorer uses. One place, on purpose.

**No magic number appears anywhere in the arithmetic.** Changing a weight, a band boundary, a
strength threshold or a design constant must be a one-place edit — that is the entire point of
expecting them to change, and a value spread across four expressions is a value nobody will
dare adjust.

**All of it is uncalibrated.** See this package's `__init__` for what that means and what the
exit condition is.

`WEIGHT_SET_VERSION` is stored on every ranking. A recalibration must not silently rewrite
history: a rank read next month has to be able to say which numbers produced it.
"""

from dataclasses import dataclass

# Bump on ANY change below. A ranking stored under one version is not comparable with a
# ranking stored under another, and the store is what makes that checkable.
WEIGHT_SET_VERSION = "adr-007-v1"

# --- The four factors and their weights (ADR-007) ----------------------------------------
# Uncalibrated. ADR-007's reasoning: what is about to hit the asset matters most, where it
# stands matters next, and what condition it is in matters least — not because condition is
# unimportant, but because §7 measured that condition data is between two months and six
# years old, and a factor you half-trust should not carry the weight of one you measure.
WEIGHTS: dict[str, float] = {
    "gust_vs_design": 0.40,
    "flood_zone": 0.25,
    "age_vs_service_life": 0.20,
    "condition_decayed": 0.15,
}

# --- Bands (ADR-007) ----------------------------------------------------------------------
# Round numbers rather than measured thresholds, and ADR-007 says so.
BAND_HIGH_AT = 60.0
BAND_MEDIUM_AT = 30.0

# --- Reason strength (ADR-007) -------------------------------------------------------------
# A factor's share of the total score. Derived from the same arithmetic as the score, so a
# "Strong" label cannot drift away from a 3% contribution: the threshold *is* the score.
STRENGTH_STRONG_AT = 0.25
STRENGTH_MODERATE_AT = 0.10

# --- Flood zone lookup (ADR-007) ------------------------------------------------------------
# FEMA zones. A zone outside this table is not defaulted — the asset becomes UNSCORED with
# that as its reason (FTEST-004), because guessing an exposure is how a coastal asset gets
# ranked like an inland one.
FLOOD_ZONE_EXPOSURE: dict[str, float] = {"VE": 1.0, "AE": 0.7, "X": 0.1}

# --- Condition decay (ADR-007) --------------------------------------------------------------
# "Condition rating, decayed by inspection staleness". The decay makes distrust of an old
# inspection arithmetic rather than a caveat. Half-life in years: a six-year-old inspection
# carries about a quarter of the weight of a fresh one.
CONDITION_DECAY_HALF_LIFE_YEARS = 3.0
CONDITION_RATING_MAX = 5.0


@dataclass(frozen=True)
class AssetTypeReference:
    """The two reference values ADR-007 compares against but never supplies (CHG-014)."""

    design_gust_mph: float
    service_life_years: float
    source: str


# --- Per-type engineering constants (CHG-014) ------------------------------------------------
# ADR-007 claims the four factors "map exactly onto the four CSVs, so nothing needs an input
# the fixture does not carry". That is true of gust, flood zone, install year and condition —
# and false of the two values they are compared *against*. Neither exists in any document.
#
# These carry a source rather than a preference, which is the standard SCENARIO_STALE_AFTER_HOURS
# set. They remain assumptions: a real utility knows its own design basis per structure, and
# these are category-level figures standing in until SGW supplies theirs.
ASSET_TYPE_REFERENCES: dict[str, AssetTypeReference] = {
    "substation": AssetTypeReference(
        design_gust_mph=130.0,
        service_life_years=50.0,
        source="ASCE 7 basic wind speed, Risk Category III–IV structures; 50-yr utility "
        "substation service life",
    ),
    "plant": AssetTypeReference(
        design_gust_mph=130.0,
        service_life_years=50.0,
        source="As substation — both are enclosed Risk Category III–IV facilities",
    ),
    "pump": AssetTypeReference(
        design_gust_mph=120.0,
        service_life_years=25.0,
        source="ASCE 7 Risk Category II–III; pumping plant mechanical life is shorter than "
        "the structure around it",
    ),
    "line": AssetTypeReference(
        design_gust_mph=105.0,
        service_life_years=40.0,
        source="NESC district loading for distribution structures — the weakest of the four, "
        "and the first thing a storm takes down",
    ),
}
