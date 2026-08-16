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
from app.store.blanks import is_blank, trim

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
    # CHG-050: how many customers this call accounts for, when the caller can say. Absent
    # is "did not say", which is not zero (defect 4's lesson, at the reporting boundary).
    customers_out: int | None = None


@router.post("/{scenario_id}/damage-reports", status_code=201)
async def file_damage_report(
    request: Request, scenario_id: str, body: DamageReport
) -> JSONResponse:
    connection = request.app.state.db
    actor = request.state.user

    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    # The legible 400 in front of the store's own bound, and it has to agree with it. The store
    # refuses an empty, whitespace-only or over-length neighbourhood by check constraint on both
    # `damage_reports.location` and `repair_jobs.location_key` (CHG-017, CHG-023); if this test
    # and those constraints disagree the caller gets a `500 internal_error` where the contract
    # specifies a `400 validation_error`, which is how the mismatch was found.
    neighbourhood = dispatch.normalise(body.neighbourhood)
    if not neighbourhood or dispatch.too_long(body.neighbourhood):
        return errors.error(
            400,
            "validation_error",
            "A damage report needs a neighbourhood, of up to "
            f"{dispatch.NEIGHBOURHOOD_MAX} characters. Never a street, a household or an "
            "address (CON-003).",
        )

    if body.customers_out is not None and body.customers_out < 0:
        return errors.error(
            400, "validation_error", "A customer count cannot be negative."
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
            customers_out=body.customers_out,
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

    Ordered by **impact** — a critical facility first, then customers accounted for, then
    arrival (CHG-050). **A rank, a score or a band must never order this list**: impact is
    what has already happened, risk is a forecast about what might, and folding the second
    into this queue is how a computed number starts moving crews. `priority_rank` is null
    and stays null; the scorer is not consulted anywhere beneath this route.
    """
    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    jobs, reports = dispatch.board(connection, scenario_id)
    return views.board_body(scenario_id, jobs, reports)


# --- The worklist's three actions (CHG-063) --------------------------------------------
#
# Records about a job, never instructions: nothing here sends anything anywhere (BR-001).
# Each moves the status machine one legal step and appends a dispatch_actions row; an
# illegal step is a 409, because "mark restored" pressed twice is a conflict, not a retry.
#
# Authorization is the session, deliberately — the same model as the dismissal endpoint.
# This platform has no scenario membership to check: every signed-in user may read every
# loaded storm and record decisions against it (`technical-spec.md` §7.2 — choosing which
# storm to work is the product), so a job id names nothing its caller could not already
# reach through GET /scenarios → GET /scenarios/{id}/jobs. A membership check here would
# verify a boundary that does not exist; if multi-tenancy ever arrives, it arrives in the
# schema first, and then EVERY scenario-scoped route changes together, not this one alone.

jobs_router = APIRouter(prefix="/api/v1/repair-jobs", tags=["dispatch"])

CREW_MAX = 120


class Assignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crew: str


def _job_or_none(request: Request, job_id: str):
    return dispatch.find_job(request.app.state.db, job_id)


def _action_body(row) -> dict:
    return {
        "action_id": row["id"],
        "repair_job_id": row["repair_job_id"],
        "action": row["action"],
        "crew": row["crew"],
        "occurred_at": row["occurred_at"],
    }


@jobs_router.post("/{job_id}/assign", status_code=200)
async def assign_crew(request: Request, job_id: str, body: Assignment):
    connection = request.app.state.db
    job = _job_or_none(request, job_id)
    if job is None:
        return errors.error(404, "not_found", "That repair job could not be found.")
    if job["status"] == "done":
        return errors.error(
            409, "job_restored", "That job is marked restored — reopen it first."
        )

    # The shared alphabet decides blank (CHG-023), and the bound is stated in the refusal.
    crew = trim(body.crew)
    if is_blank(body.crew) or len(crew) > CREW_MAX:
        return errors.error(
            400, "validation_error", f"A crew label is 1 to {CREW_MAX} characters."
        )

    row = dispatch.record_job_action(
        connection, job=job, action="assign",
        actor_user_id=request.state.user["id"], crew=crew,
    )
    log_event(
        "JOB_CREW_ASSIGNED",
        user_id=request.state.user["id"],
        scenario_id=job["scenario_id"],
        job_id=job_id,
        outcome="recorded",
    )
    return _action_body(row)


@jobs_router.post("/{job_id}/restore", status_code=200)
async def mark_restored(request: Request, job_id: str):
    connection = request.app.state.db
    job = _job_or_none(request, job_id)
    if job is None:
        return errors.error(404, "not_found", "That repair job could not be found.")
    if job["status"] == "done":
        return errors.error(409, "already_restored", "That job is already marked restored.")

    row = dispatch.record_job_action(
        connection, job=job, action="restore", actor_user_id=request.state.user["id"]
    )
    log_event(
        "JOB_RESTORED",
        user_id=request.state.user["id"],
        scenario_id=job["scenario_id"],
        job_id=job_id,
        outcome="recorded",
    )
    return _action_body(row)


@jobs_router.post("/{job_id}/reopen", status_code=200)
async def reopen(request: Request, job_id: str):
    connection = request.app.state.db
    job = _job_or_none(request, job_id)
    if job is None:
        return errors.error(404, "not_found", "That repair job could not be found.")
    if job["status"] != "done":
        return errors.error(409, "not_restored", "That job is not marked restored.")

    row = dispatch.record_job_action(
        connection, job=job, action="reopen", actor_user_id=request.state.user["id"]
    )
    log_event(
        "JOB_REOPENED",
        user_id=request.state.user["id"],
        scenario_id=job["scenario_id"],
        job_id=job_id,
        outcome="recorded",
    )
    return _action_body(row)
