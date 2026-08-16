"""The deterministic weighted rule (ADR-005, ADR-007).

A pure function of a loaded asset. No request, no screen, no store, no training step.

**Score and reasons are one computation.** Each factor produces its contribution and its
explanation in the same step, and the score is the sum of exactly the contributions the reasons
describe — so a reason cannot drift away from the arithmetic, because it *is* the arithmetic.
That is ADR-005's implementation rule, and `test_the_contributions_sum_to_the_score` is what
fails if it stops being true.

**A factor that cannot be computed makes the asset UNSCORED**, with the missing input named.
Never omitted from the ranking, and never scored low. Scoring an asset on three of four factors
would produce a number that looks comparable with the others and is not — the confidently wrong
output ADR-005 warns is more persuasive than a wrong model.
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from app.scoring import references as ref


@dataclass(frozen=True)
class Reason:
    """One factor's contribution, and the plain words for it.

    `contribution` is in score points, so the reasons sum to the score. `strength` is that
    contribution's share of the total, banded by ADR-007 — derived, never authored.
    """

    factor: str
    strength: str
    contribution: float
    detail: str


@dataclass
class RankedAsset:
    external_ids: list[str]
    name: str
    type: str
    score: float | None = None
    band: str | None = None
    rank: int | None = None
    reasons: list[Reason] = field(default_factory=list)
    unscored_reason: str | None = None
    weight_set_version: str = ref.WEIGHT_SET_VERSION
    condition_observed_at: str | None = None


class Unscorable(Exception):
    """An input the rule needs is absent or unusable. Names what, in plain words."""


def _years_since(iso_date: str, today: date) -> float:
    return (today - datetime.fromisoformat(iso_date).date()).days / 365.25


# --- The plain words -------------------------------------------------------------------------
#
# REQ-F-003 asks for reasons in **plain words**, and this text is what an operator reads at 3am.
# ADR-009's phrasing model would render it more fluently — and it is optional at runtime and
# currently blocked on Q-029 and Q-030, so **this is what ships if the model never arrives.**
# It therefore has to read as English on its own rather than as arithmetic with units attached.
#
# Each phrase is produced in the same step as its contribution, so it cannot drift from the
# number it describes (ADR-005). What changes with severity is the *wording*, not the maths:
# the same ratio always produces the same contribution, and the sentence says what that ratio
# means rather than restating it.


def _how_close(ratio: float, near: str, at: str, under: str, well_under: str) -> str:
    if ratio >= 1.0:
        return at
    if ratio >= 0.8:
        return near
    return under if ratio >= 0.5 else well_under


def _gust_vs_design(asset, reference) -> tuple[float, str]:
    if asset.wind_gust_mph is None:
        raise Unscorable("no forecast covers this asset, so its wind exposure is unknown")

    gust, design = asset.wind_gust_mph, reference.design_gust_mph
    ratio = min(gust / design, 1.0)
    kind = asset.type
    return ratio, _how_close(
        gust / design,
        at=f"Forecast winds of {gust:.0f} mph meet or exceed the {design:.0f} mph this {kind} "
        f"was built to withstand.",
        near=f"Forecast winds of {gust:.0f} mph come close to the {design:.0f} mph this {kind} "
        f"was built to withstand.",
        under=f"Forecast winds of {gust:.0f} mph, against the {design:.0f} mph this {kind} was "
        f"built to withstand.",
        well_under=f"Forecast winds of {gust:.0f} mph, well within the {design:.0f} mph this "
        f"{kind} was built to withstand.",
    )


FLOOD_ZONE_WORDS = {
    "VE": "Sits in a coastal high-hazard flood zone (VE) — exposed to storm surge and waves.",
    "AE": "Sits inside the mapped 100-year floodplain (zone AE).",
    "A": "Sits inside the mapped 100-year floodplain (zone A).",
    "AO": "Sits inside the mapped 100-year floodplain (zone AO — shallow sheet flow).",
    "AH": "Sits inside the mapped 100-year floodplain (zone AH — shallow ponding).",
    "X": "Sits outside the mapped floodplain (zone X).",
}


def _flood_zone(asset) -> tuple[float, str]:
    zone = (asset.flood_zone or "").strip().upper()
    if zone not in ref.FLOOD_ZONE_EXPOSURE:
        # CHG-042: scored at the minimal value, and SAID. A blank zone is still a refusal
        # to score — nothing was recorded, which is a missing input, not an odd code.
        if not zone:
            raise Unscorable("its flood zone is blank, so its flood exposure is unknown")
        # Not a guess dressed as knowledge: the sentence names the code and the fact that
        # the rule did not recognise it, so "minimal" cannot read as "safe" (FTEST-004's
        # concern, kept — the honesty moved from an UNSCORED row into the reason).
        return (
            ref.FLOOD_ZONE_UNRECOGNISED_EXPOSURE,
            f"Flood zone code {zone!r} was not recognised — scored at minimal flood risk "
            f"until somebody determines it.",
        )
    return ref.FLOOD_ZONE_EXPOSURE[zone], FLOOD_ZONE_WORDS[zone]


def _age_vs_service_life(asset, reference, today: date) -> tuple[float, str]:
    if asset.install_year is None:
        raise Unscorable("its installation year is missing, so its age is unknown")

    age = today.year - asset.install_year
    life = reference.service_life_years
    ratio = min(age / life, 1.0)
    return ratio, _how_close(
        age / life,
        at=f"{age} years old — past the {life:.0f} years this kind of asset is expected to last.",
        near=f"{age} years old, near the end of the {life:.0f} years this kind of asset is "
        f"expected to last.",
        under=f"{age} years old, of an expected {life:.0f}-year life.",
        well_under=f"{age} years old, early in an expected {life:.0f}-year life.",
    )


def _how_long_ago(years: float) -> str:
    if years < 1:
        return f"{max(round(years * 12), 1)} months ago"
    return f"{years:.0f} years ago" if years >= 2 else "about a year ago"


def _condition_decayed(asset, today: date) -> tuple[float, str]:
    if asset.condition is None or asset.condition_observed_at is None:
        raise Unscorable("it has no condition rating with a date, so its condition is unknown")
    try:
        rating = float(asset.condition)
    except ValueError:
        raise Unscorable(f"its condition rating {asset.condition!r} is not a number") from None

    staleness = max(_years_since(asset.condition_observed_at, today), 0.0)
    # Distrust as arithmetic rather than as a caveat: an old inspection contributes less.
    decay = 0.5 ** (staleness / ref.CONDITION_DECAY_HALF_LIFE_YEARS)
    # A worse rating is a higher risk, so the scale is inverted before decaying it.
    severity = (ref.CONDITION_RATING_MAX - rating) / ref.CONDITION_RATING_MAX

    quality = "poor" if rating <= 2 else "fair" if rating <= 3 else "good"
    detail = (
        f"Rated {rating:.0f} out of {ref.CONDITION_RATING_MAX:.0f} — {quality} — when last "
        f"inspected, {_how_long_ago(staleness)} ({asset.condition_observed_at})."
    )
    if asset.condition_estimated:
        detail += " That rating was estimated rather than measured."
    if staleness >= 2:
        # BR-003's whole point, said out loud: an old reading counts for less, and the reader
        # should know that is why, rather than wondering why condition barely moved the rank.
        detail += " Because the inspection is old, it counts for less than a recent one would."
    return severity * decay, detail


def _strength(share: float) -> str:
    if share >= ref.STRENGTH_STRONG_AT:
        return "Strong"
    if share >= ref.STRENGTH_MODERATE_AT:
        return "Moderate"
    return "Slight"


def _band(score: float) -> str:
    if score >= ref.BAND_HIGH_AT:
        return "High"
    return "Medium" if score >= ref.BAND_MEDIUM_AT else "Low"


def score_asset(asset, *, weights=None, references=None, today: date | None = None) -> RankedAsset:
    """Score one asset, or return it UNSCORED with the reason why."""
    weights = weights or ref.WEIGHTS
    references = references or ref.ASSET_TYPE_REFERENCES
    today = today or date.today()

    ranked = RankedAsset(
        external_ids=list(asset.external_ids),
        name=asset.name,
        type=asset.type,
        condition_observed_at=asset.condition_observed_at,
    )

    reference = references.get(asset.type)
    if reference is None:
        ranked.unscored_reason = f"no design reference for asset type {asset.type!r}"
        return ranked

    try:
        factors = {
            "gust_vs_design": _gust_vs_design(asset, reference),
            "flood_zone": _flood_zone(asset),
            "age_vs_service_life": _age_vs_service_life(asset, reference, today),
            "condition_decayed": _condition_decayed(asset, today),
        }
    except Unscorable as why:
        # Present, visible, and not ranked low. Omitting it is the tidiest code and the most
        # dangerous screen in the product.
        ranked.unscored_reason = str(why)
        return ranked

    contributions = {
        name: 100.0 * weights[name] * normalised for name, (normalised, _) in factors.items()
    }
    score = sum(contributions.values())

    ranked.score = round(score, 4)
    ranked.band = _band(score)
    # **Every computed factor gets a reason, including one that contributed nothing.**
    #
    # These were filtered to `contribution > 0` on the grounds that a zero adds noise. The
    # eval harness disproved that: an asset rated 5/5 *six years ago* contributes zero, so it
    # produced no condition reason, so its rank said nothing about resting on a six-year-old
    # inspection — 47 of 185 stale ranks at demo scale. `stale_inputs_disclosed` is a hard
    # floor precisely because that silence is invisible on screen.
    #
    # A factor that scored zero still participated, and *why* it scored zero is often the
    # most useful sentence on the panel.
    ranked.reasons = [
        Reason(
            factor=name,
            strength=_strength(contributions[name] / score if score else 0.0),
            contribution=round(contributions[name], 4),
            detail=detail,
        )
        for name, (_, detail) in factors.items()
    ]
    ranked.reasons.sort(key=lambda reason: -reason.contribution)
    return ranked


def tie_break_key(*, condition_observed_at: str | None, external_ids: list[str]) -> tuple:
    """Equal scores tie-break by oldest condition observation (UTEST-010).

    An asset nobody has looked at recently is the one whose score is most likely to be wrong,
    so it goes first. An asset with no observation at all sorts after those that have one —
    it is not *old*, it is *unknown* — and the identifier is the final tie-break so the order
    is total rather than merely usually-stable.
    """
    return (condition_observed_at or "9999-12-31", sorted(external_ids)[0])


def rank_assets(assets, *, weights=None, references=None, today: date | None = None):
    """Score every asset, then order the scored ones. Unscored assets keep their place in the
    list and carry no rank number — they are in the ranking, not ranked."""
    scored = [
        score_asset(asset, weights=weights, references=references, today=today)
        for asset in assets
    ]

    ranked = [item for item in scored if item.score is not None]
    ranked.sort(
        key=lambda item: (
            -item.score,
            tie_break_key(
                condition_observed_at=item.condition_observed_at, external_ids=item.external_ids
            ),
        )
    )
    for position, item in enumerate(ranked, start=1):
        item.rank = position

    return ranked + [item for item in scored if item.score is None]
