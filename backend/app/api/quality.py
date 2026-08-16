"""Data quality after load: the stored findings and the asset match queue
(CHG-047, CHG-048).

Everything here reads rows written inside the scenario's own transaction. Nothing
re-parses a file — the quality screen works after FF-003 has deleted every source file,
which is the point of storing the findings at all.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from app.api import errors, views
from app.api.events import log_event
from app.store import findings as findings_store
from app.store import matches, scenarios

router = APIRouter(prefix="/api/v1/scenarios", tags=["quality"])


@router.get("/{scenario_id}/findings")
async def read_findings(request: Request, scenario_id: str):
    """Every finding the parse produced, needs-decision first.

    The three-row rule is the screen's, not this endpoint's: the server returns the
    whole truth and the screen decides how much of it is a question.
    """
    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")
    rows = findings_store.for_scenario(connection, scenario_id)
    return {
        "scenario_id": scenario_id,
        "items": [views.finding_item(row) for row in rows],
        "needs_decision_count": sum(1 for r in rows if r["needs_decision"] and not r["resolution"]),
        "total": len(rows),
    }


class FindingResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    # What the person chose, in the words the button offered. Bounded because it is
    # stored verbatim.
    resolution: str


@router.post("/{scenario_id}/findings/resolve", status_code=200)
async def resolve_finding(request: Request, scenario_id: str, body: FindingResolution):
    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")
    if not body.resolution.strip() or len(body.resolution) > 200:
        return errors.error(400, "validation_error", "A resolution is 1 to 200 characters.")

    row = findings_store.resolve(
        connection,
        finding_id=body.finding_id,
        resolution=body.resolution.strip(),
        resolved_by=request.state.user["id"],
        now=datetime.now(UTC).isoformat(),
    )
    if row is None or row["scenario_id"] != scenario_id:
        return errors.error(404, "not_found", "That finding could not be found.")
    log_event(
        "FINDING_RESOLVED",
        user_id=request.state.user["id"],
        scenario_id=scenario_id,
        finding_id=body.finding_id,
        outcome="resolved",
    )
    return views.finding_item(row)


@router.get("/{scenario_id}/matches")
async def read_match_queue(request: Request, scenario_id: str):
    """The withheld merges, pending first — what AC-001 deferred to a person."""
    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")
    rows = matches.queue(connection, scenario_id)
    return {
        "scenario_id": scenario_id,
        "items": [views.match_candidate_item(row) for row in rows],
        "pending_count": sum(1 for r in rows if r["resolution"] == "pending"),
        "total": len(rows),
    }


class MatchResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    resolution: str  # 'match' | 'not_match' — anything else is a 400 below


@router.post("/{scenario_id}/matches/resolve", status_code=200)
async def resolve_match(request: Request, scenario_id: str, body: MatchResolution):
    """Record what the reviewer decided. **Admin only**: resolving identity changes what
    the registry means, which is the same trust level as loading it."""
    connection = request.app.state.db
    if request.state.user["role"] != "admin":
        log_event(
            "MATCH_RESOLVE_REFUSED",
            level=logging.WARNING,
            user_id=request.state.user["id"],
            outcome="refused",
        )
        return errors.error(403, "forbidden", "You do not have permission to perform this action.")
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")
    if body.resolution not in ("match", "not_match"):
        return errors.error(
            400, "validation_error", "A resolution is 'match' or 'not_match'."
        )

    candidate = matches.find(connection, body.candidate_id)
    if candidate is None or candidate["scenario_id"] != scenario_id:
        return errors.error(404, "not_found", "That candidate could not be found.")
    if candidate["resolution"] != "pending":
        # The review happened. A second answer is a conflict, not a second review.
        return errors.error(409, "already_resolved", "That candidate was already reviewed.")

    row = matches.resolve(
        connection,
        candidate=candidate,
        resolution=body.resolution,
        resolved_by=request.state.user["id"],
        now=datetime.now(UTC).isoformat(),
    )
    log_event(
        "MATCH_RESOLVED",
        user_id=request.state.user["id"],
        scenario_id=scenario_id,
        candidate_id=body.candidate_id,
        resolution=body.resolution,
        outcome="resolved",
    )
    return views.match_candidate_item(row)
