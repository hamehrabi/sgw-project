"""One scoring pass over stored rows, at one forecast revision.

**The load path and the re-rank path are the same pass.** Revision 0 is produced by this
function when a storm is loaded and revision n+1 by the same function when a forecast change is
applied, because AC-005 asks a reader to *compare* two revisions — and two orders produced by
two code paths are not comparable, they are two opinions.

No route handler contains a scoring rule (FF-001) and nothing here is one: the arithmetic is
`scoring/`'s, this assembles its input from the store and hands its output back.
"""

import json
from dataclasses import dataclass

from app.scoring import references
from app.scoring.rank import RankedAsset, rank_assets
from app.store import scenarios


def references_for(connection, scenario_id: str) -> dict:
    """CHG-051: the storm's own design basis first, CHG-014's sourced table beneath it.

    Merged per type rather than replaced whole: a manifest that states the substation
    basis and omits the pump's gets its substation number and the fallback's pump number,
    each still carrying where it came from.
    """
    row = connection.execute(
        "select design_references from scenarios where id = ?", (scenario_id,)
    ).fetchone()
    merged = dict(references.ASSET_TYPE_REFERENCES)
    for kind, values in json.loads((row["design_references"] if row else None) or "{}").items():
        try:
            merged[kind] = references.AssetTypeReference(
                design_gust_mph=float(values["design_gust_mph"]),
                service_life_years=float(values["service_life_years"]),
                source="manifest design_references — the utility's own stated basis",
            )
        except (KeyError, TypeError, ValueError):
            # Half a reference is not a reference. The sourced fallback stands, which is
            # the honest answer to a manifest that names a type and forgets its numbers.
            continue
    return merged


@dataclass
class _Scorable:
    """A stored asset row, in the shape the scorer reads.

    The scorer takes values, not database rows — it knows nothing about the store, which is
    what keeps it a pure function and lets a trained model replace it without touching either
    side (ADR-005, `ai-boundary-spec.md` §2).
    """

    external_ids: list[str]
    name: str
    type: str
    flood_zone: str | None
    install_year: int | None
    condition: str | None
    condition_observed_at: str | None
    condition_estimated: bool
    wind_gust_mph: float | None
    # CHG-056: the design basis the manifest stated for this asset's dialect type, when
    # it stated one. Read by the scorer FIRST — supplied beats stated-per-category beats
    # CHG-014's engineering standard, never a guess.
    design_gust_mph: float | None = None
    service_life_years: float | None = None


@dataclass
class ScoringPass:
    """What one revision's pass produced, in the shape the store writes."""

    forecast_revision: int
    pairs: list[tuple[str, RankedAsset]]
    weight_set_version: str = references.WEIGHT_SET_VERSION

    @property
    def ranked(self) -> int:
        return sum(item.score is not None for _, item in self.pairs)

    @property
    def unscored(self) -> int:
        return sum(item.score is None for _, item in self.pairs)


def as_scorable(rows) -> list[_Scorable]:
    return [
        _Scorable(
            external_ids=json.loads(row["external_ids"]),
            name=row["name"] or "",
            type=row["type"],
            flood_zone=row["flood_zone"],
            install_year=row["install_year"],
            condition=row["condition"],
            condition_observed_at=row["condition_observed_at"],
            condition_estimated=bool(row["condition_estimated"]),
            wind_gust_mph=row["wind_gust_mph"],
            design_gust_mph=row["design_gust_mph"],
            service_life_years=row["service_life_years"],
        )
        for row in rows
    ]


def movement_between(connection, scenario_id: str, previous_revision: int, scoring: ScoringPass):
    """CHG-044: the strip's rows — a diff of the pass just computed against the stored,
    delivered ranking it supersedes. **Nothing is re-scored here**: the previous side is
    read back from `risk_scores`, the current side is the pass the caller is about to
    store, and the reason a mover carries is the factor whose stored contribution grew.
    """
    previous = {
        row["asset_id"]: row
        for row in connection.execute(
            "select asset_id, rank, reasons from risk_scores"
            " where scenario_id = ? and forecast_revision = ?",
            (scenario_id, previous_revision),
        )
    }

    rows = []
    for asset_id, item in scoring.pairs:
        earlier = previous.get(asset_id)
        previous_rank = earlier["rank"] if earlier else None
        if item.rank == previous_rank:
            continue
        # The factor whose contribution grew the most between the two passes — derived
        # from the same arithmetic that produced both scores, never authored (BR-002's
        # shape). Contributions are matched by factor name across the two stored shapes.
        earlier_contributions = (
            {r["factor"]: r["contribution"] for r in json.loads(earlier["reasons"])}
            if earlier
            else {}
        )
        growth = [
            (reason.contribution - earlier_contributions.get(reason.factor, 0.0), reason)
            for reason in item.reasons
        ]
        reason = max(growth, key=lambda pair: pair[0])[1] if growth else None
        rows.append(
            {
                "asset_id": asset_id,
                "previous_rank": previous_rank,
                "current_rank": item.rank,
                "band": item.band,
                "reason_factor": reason.factor if reason else "unscored",
                "reason_detail": (
                    reason.detail if reason else (item.unscored_reason or "not scored")
                ),
            }
        )
    return rows


def score_revision(connection, scenario_id: str, forecast_revision: int) -> ScoringPass:
    """Score **every** asset in the storm against one revision's forecast.

    Every asset, not only the ones whose grid cell moved. A partial re-rank would leave one
    list holding ranks from two forecasts, which is a list nobody can act on and nobody can
    tell apart from a whole one.
    """
    rows = scenarios.assets_with_forecast(connection, scenario_id, forecast_revision)
    ranked = rank_assets(as_scorable(rows), references=references_for(connection, scenario_id))
    by_code = {code: row["id"] for row in rows for code in json.loads(row["external_ids"])}
    return ScoringPass(
        forecast_revision=forecast_revision,
        pairs=[(by_code[item.external_ids[0]], item) for item in ranked],
    )
