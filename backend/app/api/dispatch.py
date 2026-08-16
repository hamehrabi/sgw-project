"""The dispatch board — filing damage, and reading one shared list of it.

**`POST .../damage-reports` is CHG-016, proposed.** `database-design.md` §3 defines
`damage_reports`, `api-specification.md` carries a board read and a dismissal, and no endpoint
in the index brings a report into existence. Nothing in the prepared scenario carries one
either: `outages.csv` is historical replay input that "feeds nothing at run time", and a
replayed 2024 outage is not a report a dispatcher took by radio in this storm. Without this
endpoint AC-007 has no way to occur and the board is permanently empty.

**Neither endpoint is privileged.** The dispatcher holds the `user` role, and this is their
screen (REQ-R-001). Only *reading the decision record* is admin-only.

**Nothing here dispatches.** Filing a report creates a job, and a job is a note that work
exists — no crew is assigned, and no request from this module reaches anything outside the
platform, at any version (BR-001, BR-005, REQ-R-003).
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.api import errors, views
from app.api.events import log_event
from app.store import dispatch, scenarios

router = APIRouter(prefix="/api/v1/scenarios", tags=["dispatch"])


class DamageReport(BaseModel):
    """What a dispatcher may write down, and nothing else.

    `extra="forbid"` is the CON-003 boundary in the API layer: an address, a meter id, a phone
    number or a coordinate is **refused**, not quietly dropped. Dropping it silently teaches the
    caller that the field was accepted, and the next caller stores it somewhere else. The store
    refuses the same shapes independently — this one names the field, that one cannot be
    bypassed.
    """

    model_config = ConfigDict(extra="forbid")

    neighbourhood: str
    asset_id: str | None = None


@router.post("/{scenario_id}/damage-reports", status_code=201)
async def file_damage_report(
    request: Request, scenario_id: str, body: DamageReport
) -> JSONResponse:
    connection = request.app.state.db
    actor = request.state.user

    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    neighbourhood = dispatch.normalise(body.neighbourhood)
    if not neighbourhood or len(neighbourhood) > dispatch.NEIGHBOURHOOD_MAX:
        return errors.error(
            400,
            "validation_error",
            "A damage report needs a neighbourhood, of up to "
            f"{dispatch.NEIGHBOURHOOD_MAX} characters. Never a street, a household or an "
            "address (CON-003).",
        )

    if body.asset_id and not scenarios.find_asset(connection, scenario_id, body.asset_id):
        # Refused rather than stored as null: at load, an unmatched report keeps its null
        # `asset_id` because nobody is there to correct it. Here somebody is.
        #
        # **This lookup is not the enforcement of the rule and must not be read as one**
        # (ADR-002, CHG-019). The store refuses a cross-storm `asset_id` independently, through
        # a composite foreign key over `(id, scenario_id)`. Until migration 008 this `if` was
        # the only thing standing between a storm-A report and storm-B's asset — disabling it
        # left 248 tests green — which is the failure `review-log.md` pre-committed to blocking
        # on. What it buys now is a legible 400 instead of an integrity error.
        return errors.error(400, "validation_error", "That asset is not part of this storm.")

    try:
        report = dispatch.file_report(
            connection,
            scenario_id=scenario_id,
            neighbourhood=neighbourhood,
            asset_id=body.asset_id,
            reported_by=actor["id"],
        )
    except Exception:
        log_event(
            "DB_WRITE_FAILED",
            level=logging.ERROR,
            user_id=actor["id"],
            subject="damage_report",
            outcome="no_row_written",
        )
        raise

    # REQ-NF-007: an area and a figure for that area. Never the report's location as a place —
    # there is no finer location stored to log, which is what makes this rule hold by
    # construction rather than by everyone remembering it.
    log_event(
        "DAMAGE_REPORT_RECORDED",
        user_id=actor["id"],
        scenario_id=scenario_id,
        report_id=report["id"],
        repair_job_id=report["repair_job_id"],
        neighbourhood=neighbourhood,
        open_reports_in_area=dispatch.open_reports_in_area(
            connection, scenario_id, dispatch.location_key(neighbourhood)
        ),
        outcome="recorded",
    )
    return JSONResponse(status_code=201, content=views.damage_report_item(report))


@router.get("/{scenario_id}/jobs")
async def read_board(request: Request, scenario_id: str):
    """One shared list of damage reports and repair jobs (REQ-F-007).

    Ordered by when the work arrived, and by nothing else. **A rank, a score or a band must
    never order this list**: criticality badges the dispatch queue, risk orders the planning
    list, and folding one into the other is how a computed number starts moving crews.
    """
    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    jobs, reports = dispatch.board(connection, scenario_id)
    return views.board_body(scenario_id, jobs, reports)
