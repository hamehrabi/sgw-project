"""The crew staging plan (CHG-049) — a record, never an action.

Counts per depot that a person chose while reading one revision's ranking. No crew is
moved, no roster is touched, no message leaves the platform, and there is no path in this
module — or anywhere — that could move one (BR-001, BR-005).
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api import errors, views
from app.api.events import log_event
from app.store import scenarios
from app.store import staging as staging_store

router = APIRouter(prefix="/api/v1/scenarios", tags=["staging"])


@router.get("/{scenario_id}/staging")
async def read_staging(request: Request, scenario_id: str):
    connection = request.app.state.db
    scenario = scenarios.find(connection, scenario_id)
    if scenario is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    areas = staging_store.areas_for(connection, scenario_id)
    plan = staging_store.latest_plan(connection, scenario_id)
    high = connection.execute(
        "select count(*) as n from risk_scores"
        " where scenario_id = ? and forecast_revision = ? and band = 'High'",
        (scenario_id, scenario["forecast_revision"]),
    ).fetchone()["n"]
    return views.staging_body(scenario_id, areas, plan, high)


class Depot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_area_id: str
    crews: int = Field(ge=0, le=999)


class StagingPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forecast_revision: int
    depots: list[Depot] = Field(min_length=1, max_length=50)


@router.post("/{scenario_id}/staging", status_code=201)
async def record_staging(request: Request, scenario_id: str, body: StagingPlan):
    """Record the plan. Both roles: staging crews against a ranking is the product."""
    connection = request.app.state.db
    scenario = scenarios.find(connection, scenario_id)
    if scenario is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    known = {area["service_area_id"] for area in staging_store.areas_for(connection, scenario_id)}
    unknown = [depot.service_area_id for depot in body.depots if depot.service_area_id not in known]
    if unknown:
        # A depot is a service area the storm's own manifest names. Anything else would
        # be geography this platform invented (CHG-049).
        return errors.error(
            400, "validation_error", f"{unknown[0]} is not a service area of this storm."
        )

    plan = staging_store.record_plan(
        connection,
        scenario_id=scenario_id,
        forecast_revision=body.forecast_revision,
        depots=[depot.model_dump() for depot in body.depots],
        actor_user_id=request.state.user["id"],
    )
    log_event(
        "CREW_STAGING_RECORDED",
        user_id=request.state.user["id"],
        scenario_id=scenario_id,
        forecast_revision=body.forecast_revision,
        depots=len(body.depots),
        outcome="recorded",
    )
    areas = staging_store.areas_for(connection, scenario_id)
    high = connection.execute(
        "select count(*) as n from risk_scores"
        " where scenario_id = ? and forecast_revision = ? and band = 'High'",
        (scenario_id, scenario["forecast_revision"]),
    ).fetchone()["n"]
    return views.staging_body(scenario_id, areas, plan, high)
