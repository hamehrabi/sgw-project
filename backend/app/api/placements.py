"""Recording a crew placement against the ranking (REQ-F-005).

**Nothing here dispatches anything, and this is the endpoint most likely to be read as though it
does.** "Placement" is the closest word in this product to an instruction to move people. It is
not one: the response is a row in the append-only record saying which crew a person decided
should wait at which assets, while looking at one particular ranking. No repair job is created,
nobody is assigned, no message leaves the platform, and no path exists for one to (BR-001,
BR-005, REQ-R-003). `product-spec.md` §7 is why the feature is here at all — *"it is where the
ranking becomes a decision; without it the ranking is a report"* — and BR-001 is why it stops
there.

**Not privileged.** `technical-spec.md` §7.2 and `security-specification.md` both give the row
*Record a crew placement: Admin yes, User yes*, enforced by SEC-Z-001. The operations manager is
the persona in `product-spec.md` §6 and holds no special role.

**The "where" is a list of assets and there is no field for anything finer** (CON-003,
REQ-NF-007). No address, no coordinate, no free-text location — an unknown field is refused
rather than dropped, so a caller who sends one is told, and nothing has anywhere to be stored
even if they were not.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api import errors, views
from app.api.events import log_event
from app.store import decisions, rankings, scenarios

router = APIRouter(prefix="/api/v1/scenarios", tags=["placements"])

ASSETS_MAX = 500


class Placement(BaseModel):
    """What an operator may write down, and nothing else.

    `extra="forbid"` is the CON-003 boundary in the API layer, for the reason
    `api/dispatch.py` states about damage reports: dropping an unknown field silently teaches
    the caller it was accepted, and the next caller stores it somewhere else.
    """

    model_config = ConfigDict(extra="forbid")

    crew: str
    asset_ids: list[str]
    # Optional, and it defaults to the storm's current revision. Passing it is how a manager
    # comparing orders records a placement against the list they are **reading** rather than
    # against the one the pointer has moved to.
    forecast_revision: int | None = None
    note: str | None = Field(default=None, max_length=decisions.NOTE_MAX)


@router.post("/{scenario_id}/placements", status_code=201)
async def record_placement(
    request: Request, scenario_id: str, body: Placement
) -> JSONResponse:
    connection = request.app.state.db
    actor = request.state.user

    scenario = scenarios.find(connection, scenario_id)
    if scenario is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    crew = decisions.crew_label(body.crew)
    if crew is None:
        return errors.error(
            400,
            "validation_error",
            f"A placement needs a crew name of up to {decisions.CREW_LABEL_MAX} characters, on "
            "one line. A display name and a role, and nothing else about a person (CON-003).",
        )

    if not body.asset_ids or len(body.asset_ids) > ASSETS_MAX:
        return errors.error(
            400,
            "validation_error",
            f"A placement names between 1 and {ASSETS_MAX} assets — which crew waits where.",
        )
    if len(set(body.asset_ids)) != len(body.asset_ids):
        return errors.error(
            400, "validation_error", "A placement names each asset once."
        )

    revision = (
        scenario["forecast_revision"] if body.forecast_revision is None else body.forecast_revision
    )
    if not rankings.revision_exists(connection, scenario_id, revision):
        # Never a silent fall back to the current revision: that would record a placement
        # against a list the operator was not reading (`technical-spec.md` §7.3, the rule
        # `GET /risks` already follows).
        return errors.error(
            404, "not_found", f"This storm has no forecast revision {revision}."
        )

    on_the_ranking = rankings.assets_in_ranking(connection, scenario_id, revision, body.asset_ids)
    missing = [asset_id for asset_id in body.asset_ids if asset_id not in on_the_ranking]
    if missing:
        # The legible 400 in front of the store's own refusal (CHG-029, migration 012). This
        # lookup is not the rule — a direct insert never passes through it — and the store
        # refuses the same row independently, which is the whole of ADR-002's argument and the
        # condition `review-log.md` pre-commits to blocking on.
        return errors.error(
            400,
            "validation_error",
            f"{len(missing)} of the assets named are not on this storm's ranking at revision "
            f"{revision}. A placement is recorded against a list somebody read.",
        )

    # The delivered ranking, when one has been delivered. `null` otherwise — the subject of the
    # row names the ranking either way.
    recommendation = decisions.latest_recommendation(connection, scenario_id, revision)
    note = (body.note or "").strip() or None

    try:
        record_id = decisions.append_placement(
            connection,
            scenario_id=scenario_id,
            forecast_revision=revision,
            recommendation_id=recommendation["id"] if recommendation else None,
            crew=crew,
            asset_ids=body.asset_ids,
            note=note,
            actor_user_id=actor["id"],
        )
    except Exception:
        # No success is shown and the operator's typed placement stays on their screen
        # (FTEST-005). Neither the crew label nor the note is logged: one is crew data CON-003
        # has an opinion about, the other is an operator's words about a live storm.
        log_event(
            "DB_WRITE_FAILED",
            level=logging.ERROR,
            user_id=actor["id"],
            scenario_id=scenario_id,
            subject="placement",
            outcome="no_row_written",
        )
        raise

    log_event(
        "PLACEMENT_RECORDED",
        user_id=actor["id"],
        scenario_id=scenario_id,
        placement_id=record_id,
        forecast_revision=revision,
        asset_count=len(body.asset_ids),
        # Stated in the log as well as in the response, because the one thing a reader of this
        # line must not conclude is that something was sent somewhere.
        outcome="recorded_not_dispatched",
    )
    return JSONResponse(
        status_code=201, content=views.placement_item(decisions.find_record(connection, record_id))
    )
