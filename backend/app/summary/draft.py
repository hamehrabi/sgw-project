"""Drafting the situation summary (CHG-040): the model call, its guards, and the fallback
that needs no model.

**The lifecycle of one draft request:**

    figures → [guards] → model → verify → (violation? model once more → verify)
                 ↓ any guard trips              ↓ still failing
              template ————————————————————— template

Whatever the path, exactly one summaries row is stored, its `label` says which path it
took — *Drafted from platform data* survived verification; *Assembled from platform data*
is the template — and `verification.model_attempts` records what the request actually
spent, which is what the monthly ceiling is computed from. An estimate would drift; a
stored count cannot.

The key lives in this process and is read from configuration. No route returns it, no
log line prints it, and the frontend has no code path that could see it.
"""

import json
import logging
import sqlite3
import urllib.error
import urllib.request
from datetime import UTC, datetime

from app.store import summaries
from app.summary import figures as figures_module
from app.summary.verify import verify

logger = logging.getLogger("app.summary")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# A generous per-call cost bound for the configured nano-class model: ~600 tokens each
# way at current list prices is well under this. The ceiling guard multiplies stored
# attempt counts by this figure, so overestimating trips the guard early — the safe side.
EST_COST_PER_CALL_USD = 0.002

SYSTEM_PROMPT = (
    "You write a situation summary for an internal utility dashboard. "
    "Write three short paragraphs of plain prose using only the figures supplied. "
    "Introduce no number, place name, weather description, or claim that is not in the "
    "supplied data. Do not describe the storm itself. Do not speculate about cause, "
    "forecast, or protocols. Do not mention telemetry, sensors, models, or predictions."
)


def template_text(figures: dict) -> str:
    """The fallback: assembled directly from the figures, no model anywhere.

    Constructed to pass the verifier **by construction** — every number and name below is
    a supplied value, and none of the forbidden vocabulary appears. The top asset's
    computed reason is deliberately NOT quoted here: a gust reason legitimately contains
    "mph", and the fallback must never fail the check that sent the model's draft here.
    """
    parts = [
        f"There are {figures['open_incidents']} open incidents on the board. "
        f"{figures['critical_facilities_affected']} involve critical facilities and stand "
        "first in the queue."
    ]
    if figures["crews_total"] is not None:
        parts.append(
            f"{figures['crews_deployed']} of {figures['crews_total']} crews in the staging "
            f"plan are placed. An estimated {figures['customers_out']:,} customers are "
            "without service."
        )
    else:
        parts.append(
            f"{figures['crews_deployed']} crew placement(s) are recorded. An estimated "
            f"{figures['customers_out']:,} customers are without service."
        )
    led = f", led by {figures['top_asset_name']}" if figures["top_asset_name"] else ""
    when = _clock(figures["forecast_issued_at"])
    parts.append(
        f"{figures['high_risk_count']} assets are rated high risk in the current "
        f"ranking{led}. Figures as of the {when} forecast."
    )
    return "\n\n".join(parts)


def _clock(issued_at: str | None) -> str:
    if not issued_at:
        return "current"
    try:
        return datetime.fromisoformat(issued_at.replace("Z", "+00:00")).strftime("%H:%M")
    except ValueError:
        return "current"


def call_model(figures: dict, config, *, transport=None, system_prompt=SYSTEM_PROMPT) -> str:
    """One request to the configured model. `transport` exists for the tests, which must
    never reach a network — and for nothing else. The asset path (CHG-059) passes its
    own narrower instruction; everything else about the call is one code path."""
    body = {
        "model": config.openai_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(figures)},
        ],
        "max_tokens": 400,
        "temperature": 0.2,
    }
    if transport is not None:
        return transport(body)

    request = urllib.request.Request(
        OPENAI_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.openai_api_key}",
        },
        method="POST",
    )
    # S310: the scheme cannot vary — OPENAI_URL is a module constant and https.
    with urllib.request.urlopen(  # noqa: S310
        request, timeout=config.llm_timeout_seconds
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def _spent(connection: sqlite3.Connection, scenario_id: str) -> tuple[int, float]:
    """(calls for this scenario, estimated USD this month) — from stored attempt counts.

    Both drafting paths count (CHG-059): the situation summary and the per-asset
    summaries draw on one budget, so neither can spend what the other was allowed.
    """

    def _count(sql: str, params: tuple) -> int:
        return int(connection.execute(sql, params).fetchone()["n"])

    scenario_calls = _count(
        "select coalesce(sum(json_extract(verification, '$.model_attempts')), 0) as n"
        " from summaries where scenario_id = ?",
        (scenario_id,),
    ) + _count(
        "select coalesce(sum(json_extract(verification, '$.model_attempts')), 0) as n"
        " from asset_summaries where scenario_id = ?",
        (scenario_id,),
    )
    month = datetime.now(UTC).strftime("%Y-%m")
    monthly_calls = _count(
        "select coalesce(sum(json_extract(verification, '$.model_attempts')), 0) as n"
        " from summaries where drafted_at like ?",
        (f"{month}%",),
    ) + _count(
        "select coalesce(sum(json_extract(verification, '$.model_attempts')), 0) as n"
        " from asset_summaries where created_at like ?",
        (f"{month}%",),
    )
    return scenario_calls, float(monthly_calls) * EST_COST_PER_CALL_USD


def draft_summary(
    connection: sqlite3.Connection,
    *,
    scenario_id: str,
    config,
    drafted_by: str,
    transport=None,
) -> sqlite3.Row:
    """Produce and store one Draft. Never raises on a model failure — a summary the model
    could not write is a summary the figures write instead, labelled as such."""
    figures = figures_module.assemble(connection, scenario_id)
    attempts = 0
    text = None

    if config.llm_enabled:
        calls, spent_usd = _spent(connection, scenario_id)
        over_calls = calls >= config.llm_max_calls_per_ranking
        over_budget = spent_usd >= config.llm_monthly_cost_ceiling_usd
        if over_calls or over_budget:
            logger.warning(
                "summary guard tripped (calls=%s, est_spend=%.2f): falling back to template",
                calls,
                spent_usd,
            )
        else:
            for _ in range(2):  # one draft, one regeneration — never a loop (CHG-040)
                try:
                    attempts += 1
                    candidate = call_model(figures, config, transport=transport)
                except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as error:
                    logger.warning("summary model call failed: %s", type(error).__name__)
                    break
                if verify(candidate, figures)["ok"]:
                    text = candidate
                    break

    if text is None:
        text = template_text(figures)
        label = "Assembled from platform data"
    else:
        label = "Drafted from platform data"

    verification = verify(text, figures)
    verification["model_attempts"] = attempts
    return summaries.append_draft(
        connection,
        scenario_id=scenario_id,
        draft_text=text,
        label=label,
        source_figures=figures,
        verification=verification,
        drafted_by=drafted_by,
    )
