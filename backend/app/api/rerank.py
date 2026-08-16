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
        )
        for row in rows
    ]


def score_revision(connection, scenario_id: str, forecast_revision: int) -> ScoringPass:
    """Score **every** asset in the storm against one revision's forecast.

    Every asset, not only the ones whose grid cell moved. A partial re-rank would leave one
    list holding ranks from two forecasts, which is a list nobody can act on and nobody can
    tell apart from a whole one.
    """
    rows = scenarios.assets_with_forecast(connection, scenario_id, forecast_revision)
    ranked = rank_assets(as_scorable(rows))
    by_code = {code: row["id"] for row in rows for code in json.loads(row["external_ids"])}
    return ScoringPass(
        forecast_revision=forecast_revision,
        pairs=[(by_code[item.external_ids[0]], item) for item in ranked],
    )
