"""The situation summary's three endpoints (CHG-040).

Draft, approve, send — and no other path to `Sent` exists, in this module or anywhere.
Approval **re-verifies the exact text being approved** and refuses on any violation: the
block the review drawer shows is this endpoint's refusal rendered, not a disabled button
the browser could re-enable.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api import errors, views
from app.api.events import log_event
from app.store import scenarios
from app.store import summaries as summaries_store
from app.summary.draft import draft_summary
from app.summary.verify import verify

router = APIRouter(prefix="/api/v1/scenarios", tags=["summaries"])


@router.get("/{scenario_id}/summary")
async def read_summary(request: Request, scenario_id: str):
    """The latest summary, or a stated absence — never a 404 for "none yet", because
    "nobody has drafted one" is a fact about the storm, not a missing resource."""
    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")
    row = summaries_store.latest(connection, scenario_id)
    return {
        "scenario_id": scenario_id,
        "summary": views.summary_item(row) if row else None,
    }


@router.post("/{scenario_id}/summary/draft", status_code=201)
async def draft(request: Request, scenario_id: str):
    """Produce one Draft. Regenerate is this same endpoint pressed again — every draft is
    a new appended row, so what a reader may have seen is never rewritten."""
    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    row = draft_summary(
        connection,
        scenario_id=scenario_id,
        config=request.app.state.config,
        drafted_by=request.state.user["id"],
    )
    log_event(
        "SUMMARY_DRAFTED",
        user_id=request.state.user["id"],
        scenario_id=scenario_id,
        summary_id=row["id"],
        label=row["label"],
        outcome="drafted",
    )
    return JSONResponse(status_code=201, content=views.summary_item(row))


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_id: str
    # The text as the approver reviewed it — editable in the drawer, so what is approved
    # is what was read, not what was generated. Bounded like every stored field.
    approved_text: str = Field(min_length=1, max_length=8000)


@router.post("/{scenario_id}/summary/approve", status_code=200)
async def approve(request: Request, scenario_id: str, body: Approval):
    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    row = summaries_store.find(connection, body.summary_id)
    if row is None or row["scenario_id"] != scenario_id:
        return errors.error(404, "not_found", "That summary could not be found.")
    if row["state"] != "Draft":
        return errors.error(409, "not_a_draft", f"That summary is already {row['state']}.")

    # THE BLOCK (CHG-040). The text being approved is re-verified against the figures it
    # was drafted from — edits in the drawer pass through the same judge the model did.
    # A violation is a refusal with the violations named, never a warning.
    import json as _json

    verification = verify(body.approved_text, _json.loads(row["source_figures"]))
    if not verification["ok"]:
        log_event(
            "SUMMARY_APPROVAL_BLOCKED",
            level=logging.WARNING,
            user_id=request.state.user["id"],
            scenario_id=scenario_id,
            summary_id=body.summary_id,
            violations=sum(1 for e in verification["entries"] if not e["allowed"]),
            outcome="blocked",
        )
        return JSONResponse(
            status_code=409,
            content={
                "code": "verification_failed",
                "message": (
                    "The text contains figures or claims the platform data does not "
                    "hold. Approval is blocked until they match."
                ),
                "verification": verification,
            },
        )

    approved = summaries_store.approve(
        connection,
        summary=row,
        approved_text=body.approved_text,
        approved_by=request.state.user["id"],
    )
    log_event(
        "SUMMARY_APPROVED",
        user_id=request.state.user["id"],
        scenario_id=scenario_id,
        summary_id=body.summary_id,
        outcome="approved",
    )
    return views.summary_item(approved)


class Send(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_id: str


@router.post("/{scenario_id}/summary/send", status_code=200)
async def mark_sent(request: Request, scenario_id: str, body: Send):
    """Record that a person distributed the approved summary. **The platform sends
    nothing** — no mail, no webhook, no channel exists (BR-001); this records that the
    human act happened, which is what the state machine's third state means."""
    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    row = summaries_store.find(connection, body.summary_id)
    if row is None or row["scenario_id"] != scenario_id:
        return errors.error(404, "not_found", "That summary could not be found.")
    if row["state"] != "Approved":
        # Draft → Sent has no edge. The review drawer is the only way through, and it
        # goes via Approved (CHG-040's lifecycle, held by the store's constraint too).
        return errors.error(409, "not_approved", f"That summary is {row['state']}, not Approved.")

    sent = summaries_store.mark_sent(connection, summary=row)
    log_event(
        "SUMMARY_SENT",
        user_id=request.state.user["id"],
        scenario_id=scenario_id,
        summary_id=body.summary_id,
        outcome="sent",
    )
    return views.summary_item(sent)
