"""Triage: one person's decision about one asset's rank (CHG-055).

The row menu, the asset drawer and Focus Mode all land here. **Nothing is dispatched,
hidden or re-scored** — Accept, Adjust and Dismiss are records of what a person thought
of a rank while reading it, which is the evidence REQ-F-006 exists to keep.
"""



from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api import errors
from app.api.events import log_event
from app.store import decisions, scenarios
from app.store.blanks import is_blank, trim

router = APIRouter(prefix="/api/v1/scenarios", tags=["triage"])


class Triage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    forecast_revision: int
    # The design's words, verbatim. The store's kind alphabet is the schema's business;
    # the mapping lives beside the writer (decisions.TRIAGE_ACTIONS).
    action: str
    note: str | None = Field(default=None, max_length=2000)


@router.post("/{scenario_id}/triage", status_code=201)
async def record_triage(request: Request, scenario_id: str, body: Triage) -> JSONResponse:
    connection = request.app.state.db
    actor = request.state.user

    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")
    if body.action not in decisions.TRIAGE_ACTIONS:
        return errors.error(
            400, "validation_error", "A triage action is Accept, Adjust or Dismiss."
        )

    # Adjust and Dismiss require the why — the note is what makes the record worth
    # keeping (REQ-F-006's rule for change and reject, applied to the same three verbs).
    note = None if body.note is None or is_blank(body.note) else trim(body.note)
    if body.action in ("Adjust", "Dismiss") and note is None:
        return errors.error(
            400,
            "validation_error",
            f"A note is required to {body.action.lower()} an asset's rank.",
        )

    # The decision names the stored rank it was taken about — the row, not the asset in
    # the abstract, so reading it back says which revision the person was looking at.
    score_row = connection.execute(
        "select rs.id, a.external_ids from risk_scores rs"
        " join assets a on a.id = rs.asset_id"
        " where rs.scenario_id = ? and rs.asset_id = ? and rs.forecast_revision = ?",
        (scenario_id, body.asset_id, body.forecast_revision),
    ).fetchone()
    if score_row is None:
        return errors.error(
            404,
            "not_found",
            "No stored rank exists for that asset at that revision — a decision is about "
            "a list a person was reading, and there is no such list.",
        )

    import json as _json

    asset_code = _json.loads(score_row["external_ids"])[0]
    record_id = decisions.append_triage(
        connection,
        scenario_id=scenario_id,
        forecast_revision=body.forecast_revision,
        risk_score_id=score_row["id"],
        asset_code=asset_code,
        action=body.action,
        note=note,
        actor_user_id=actor["id"],
    )
    log_event(
        "TRIAGE_RECORDED",
        user_id=actor["id"],
        scenario_id=scenario_id,
        forecast_revision=body.forecast_revision,
        action=body.action,
        outcome="recorded",
    )
    record = decisions.find_record(connection, record_id)
    return JSONResponse(
        status_code=201,
        content={
            "decision_record_id": record_id,
            "action": body.action,
            "asset_code": asset_code,
            "forecast_revision": body.forecast_revision,
            "actor_user_id": actor["id"],
            "occurred_at": record["occurred_at"],
        },
    )



