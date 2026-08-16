"""The fixed figure set one asset's summary may speak about (CHG-059).

Assembled from the asset's stored `risk_scores` row and nothing else. **This dict is the
whole prompt surface for the per-asset path** — and unlike the situation summary's
(CHG-040), it carries **no asset name, no identifier, and no coordinate**: ADR-009's
boundary holds here without any widening. The popup's title is the client's to render;
the model has no need of it.
"""

import json
import sqlite3


class NoStoredRank(LookupError):
    """No risk_scores row exists for that asset at that revision — a summary describes a
    ranking that exists, never one that might."""


def assemble(
    connection: sqlite3.Connection, scenario_id: str, asset_id: str, forecast_revision: int
) -> dict:
    row = connection.execute(
        "select rs.score, rs.band, rs.rank, rs.reasons, rs.unscored_reason, a.type"
        " from risk_scores rs join assets a on a.id = rs.asset_id"
        "   and a.scenario_id = rs.scenario_id"
        " where rs.scenario_id = ? and rs.asset_id = ? and rs.forecast_revision = ?",
        (scenario_id, asset_id, forecast_revision),
    ).fetchone()
    if row is None:
        raise NoStoredRank(
            f"no stored rank for that asset at forecast revision {forecast_revision}"
        )

    ranked_total = connection.execute(
        "select count(*) as n from risk_scores"
        " where scenario_id = ? and forecast_revision = ? and rank is not null",
        (scenario_id, forecast_revision),
    ).fetchone()["n"]

    scenario = connection.execute(
        "select forecast_issued_at from scenarios where id = ?", (scenario_id,)
    ).fetchone()

    return {
        "asset_type": row["type"],
        "risk_band": row["band"],
        "rank": row["rank"],
        "ranked_total": ranked_total,
        # The computed reasons verbatim — the exact thing ADR-009 says a model may
        # phrase. Contributions rounded to one decimal, so a draft that quotes one is
        # quoting a supplied value rather than a truncation of it.
        "reasons": [
            {
                "factor": reason["factor"],
                "strength": reason["strength"],
                "contribution": round(reason["contribution"], 1),
                "detail": reason["detail"],
            }
            for reason in json.loads(row["reasons"])
        ],
        "unscored_reason": row["unscored_reason"],
        "forecast_issued_at": scenario["forecast_issued_at"] if scenario else None,
    }
