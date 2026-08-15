"""Deciding on a recommendation.

**This endpoint is where BR-001 becomes code.** Its response is a record, never an action: no
crew is moved, no job is assigned, and nothing leaves the platform as a result of this call.
Remove that property and the product changes category — from decision support to automation,
with a different regulator and a different liability.

Deciding is deliberately **not** privileged. Any signed-in user, admin or not: it is the whole
point of the product, not an administrative function. Only *reading* the record is admin-only
(SEC-Z-003).
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api import errors
from app.api.events import log_event
from app.store import decisions

router = APIRouter(prefix="/api/v1/recommendations", tags=["decisions"])

NOTE_MAX = 2000


class Decision(BaseModel):
    decision: str
    # Required on change and reject — checked below rather than by the schema, so the refusal
    # can name the field and say why (`security-specification.md` §3).
    note: str | None = Field(default=None, max_length=NOTE_MAX)
    change: dict | None = None


@router.post("/{recommendation_id}/decision", status_code=201)
async def decide(request: Request, recommendation_id: str, body: Decision) -> JSONResponse:
    connection = request.app.state.db
    actor = request.state.user

    if body.decision not in decisions.DECISIONS:
        return errors.validation_error(
            f"A decision must be one of: {', '.join(decisions.DECISIONS)}."
        )

    note = (body.note or "").strip()
    if body.decision in ("change", "reject") and not note:
        return errors.error(
            400,
            "validation_error",
            f"A note is required when you {body.decision} a recommendation.",
        )

    recommendation = decisions.find_recommendation(connection, recommendation_id)
    if recommendation is None:
        return errors.error(404, "not_found", "That recommendation could not be found.")

    # BR-004: a second decision is a conflict, never an overwrite. Checked before the write so
    # a retrying client cannot produce two audit rows for one human decision.
    already = decisions.existing_decision(connection, recommendation_id)
    if already:
        return errors.error(
            409,
            "already_decided",
            f"This recommendation was already decided: {already['kind']} at "
            f"{already['occurred_at']}. A correction is a new recommendation, not an edit.",
        )

    try:
        record_id = decisions.append_decision(
            connection,
            recommendation=recommendation,
            kind=body.decision,
            actor_user_id=actor["id"],
            note=note or None,
            change=body.change,
        )
    except Exception:
        # No success is shown and the operator's note stays on their screen (FTEST-005). The
        # note itself is never logged: it is an operator's words about a live storm.
        log_event(
            "DB_WRITE_FAILED",
            level=logging.ERROR,
            user_id=actor["id"],
            subject="recommendation_decision",
            outcome="no_row_written",
        )
        raise

    log_event(
        "DECISION_RECORDED",
        user_id=actor["id"],
        kind=body.decision,
        recommendation_id=recommendation_id,
        outcome="recorded",
    )
    return JSONResponse(
        status_code=201,
        content={
            "decision_record_id": record_id,
            "recommendation_id": recommendation_id,
            "decision": body.decision,
            "actor_user_id": actor["id"],
            "occurred_at": decisions.existing_decision(connection, recommendation_id)[
                "occurred_at"
            ],
        },
    )
