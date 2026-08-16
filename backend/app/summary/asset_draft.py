"""Drafting one asset's summary (CHG-059): phrased once, stored, never re-inferred.

The lifecycle mirrors the situation summary's (`draft.py`), with three differences that
are the whole of CHG-059:

- **the figure set is narrower** — the asset's stored reasons, band, rank and type, and
  never its name, identifier or coordinate (`asset_figures.py`);
- **the verifier speaks mph** (`verify_asset`), because gust reasons state gusts in mph
  and the figure check is what pins every number to a supplied value;
- **the store is the cache** — one row per (scenario, asset, revision) by `unique`
  constraint, so a repeat request finds the row and the model is never called twice for
  one ranking.

The spend guards are shared with the situation summary: one per-scenario call bound, one
monthly ceiling, both computed from stored attempt counts across both tables.
"""

import logging
import sqlite3
import urllib.error

from app.store import asset_summaries as store
from app.summary import asset_figures
from app.summary.draft import _spent, call_model
from app.summary.verify import verify_asset

logger = logging.getLogger("app.summary")

ASSET_SYSTEM_PROMPT = (
    "You phrase the risk assessment of one infrastructure asset for an internal utility "
    "dashboard. Write one short paragraph — three or four sentences of plain prose — "
    "explaining why the asset holds its rank, using only the supplied computed factors. "
    "Introduce no number, place, or claim that is not in the supplied data. Do not name "
    "or identify the asset. Do not speculate about damage, cause, or response. Do not "
    "mention telemetry, sensors, models, or predictions."
)


def template_asset_text(figures: dict) -> str:
    """The fallback: the computed reasons in their own words, no model anywhere.

    Passes `verify_asset` by construction — every sentence is either a supplied detail
    verbatim or built from supplied figures, and an unscorable asset is stated as
    unjudged rather than dressed as safe (the empty-screen rule, applied to prose).
    """
    if figures["rank"] is None:
        return (
            f"This asset could not be scored: {figures['unscored_reason']}. It has "
            "not been judged low risk — it stays on the ranking so a person can "
            "supply what is missing."
        )
    opening = (
        f"Ranked {figures['rank']} of {figures['ranked_total']} in the current "
        f"ranking — rated {figures['risk_band']} risk."
    )
    return " ".join([opening, *(reason["detail"] for reason in figures["reasons"])])


def draft_asset_summary(
    connection: sqlite3.Connection,
    *,
    scenario_id: str,
    asset_id: str,
    forecast_revision: int,
    config,
    created_by: str,
    transport=None,
) -> tuple[sqlite3.Row, bool]:
    """The stored row for this (asset, revision), generating it only if none exists.

    Returns (row, created). Raises `asset_figures.NoStoredRank` when no ranking holds
    this asset at that revision — a summary describes an order that exists.
    """
    existing = store.find(connection, scenario_id, asset_id, forecast_revision)
    if existing is not None:
        return existing, False

    figures = asset_figures.assemble(connection, scenario_id, asset_id, forecast_revision)
    attempts = 0
    text = None

    if config.llm_enabled:
        calls, spent_usd = _spent(connection, scenario_id)
        if calls >= config.llm_max_calls_per_ranking or (
            spent_usd >= config.llm_monthly_cost_ceiling_usd
        ):
            logger.warning(
                "asset summary guard tripped (calls=%s, est_spend=%.2f): template",
                calls,
                spent_usd,
            )
        else:
            for _ in range(2):  # one draft, one regeneration — never a loop (CHG-040)
                try:
                    attempts += 1
                    candidate = call_model(
                        figures, config, transport=transport,
                        system_prompt=ASSET_SYSTEM_PROMPT,
                    )
                except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as error:
                    logger.warning("asset summary call failed: %s", type(error).__name__)
                    break
                if verify_asset(candidate, figures)["ok"]:
                    text = candidate
                    break

    label = "Phrased from computed factors" if text else "Assembled from computed factors"
    if text is None:
        text = template_asset_text(figures)

    verification = verify_asset(text, figures)
    verification["model_attempts"] = attempts
    try:
        row = store.save(
            connection,
            scenario_id=scenario_id,
            asset_id=asset_id,
            forecast_revision=forecast_revision,
            text=text,
            label=label,
            source_figures=figures,
            verification=verification,
            created_by=created_by,
        )
    except sqlite3.IntegrityError:
        # A concurrent request stored one first. The unique constraint IS the cache —
        # the row that won is the summary, and this attempt's text is discarded.
        return store.find(connection, scenario_id, asset_id, forecast_revision), False
    return row, True
