"""Per-asset summaries: one GET that only reads, one POST that generates once (CHG-059).

The GET lists stored rows and can never trigger a model — FF-003 drives it with files
removed and corrupted, and a read that could infer would be a read that could change.
Generation is the POST's alone, and a repeat POST finds the stored row (the schema's
`unique` is the cache).
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api import errors, views
from app.api.events import log_event
from app.store import asset_summaries as store
from app.store import scenarios
from app.summary.asset_draft import draft_asset_summary
from app.summary.asset_figures import NoStoredRank

router = APIRouter(prefix="/api/v1/scenarios", tags=["asset-summaries"])


@router.get("/{scenario_id}/asset-summaries")
async def read_asset_summaries(request: Request, scenario_id: str):
    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")
    rows = store.for_scenario(connection, scenario_id)
    return {
        "scenario_id": scenario_id,
        "items": [views.asset_summary_item(row) for row in rows],
        "total": len(rows),
    }


class AssetSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1, max_length=64)
    forecast_revision: int = Field(ge=0)


@router.post("/{scenario_id}/asset-summaries")
async def generate_asset_summary(request: Request, scenario_id: str, body: AssetSummaryRequest):
    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    try:
        row, created = draft_asset_summary(
            connection,
            scenario_id=scenario_id,
            asset_id=body.asset_id,
            forecast_revision=body.forecast_revision,
            config=request.app.state.config,
            created_by=request.state.user["id"],
        )
    except NoStoredRank:
        # An asset the storm does not hold, or a revision nobody has applied — either
        # way there is no ranking for a summary to describe (CHG-027's rule).
        return errors.error(
            404, "not_found", "No stored ranking holds that asset at that forecast revision."
        )

    if created:
        log_event(
            "ASSET_SUMMARY_DRAFTED",
            user_id=request.state.user["id"],
            scenario_id=scenario_id,
            asset_id=body.asset_id,
            label=row["label"],
            outcome="drafted",
        )
    return JSONResponse(
        status_code=201 if created else 200, content=views.asset_summary_item(row)
    )
