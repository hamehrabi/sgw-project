"""Clearing a false alarm, in one action and never anonymously (REQ-F-008).

**Both halves of the requirement are here and they pull against each other.** Storm alarms are
cheap by design; a dispatcher who cannot clear a false one in a single press stops clearing them,
and the board stops being the shared picture REQ-F-007 built. The whole risk of making the action
cheap is that it also becomes untraceable — a report disappearing from a shared board with
nobody's name on it, during the hour somebody else is ringing back about the same street. So:
**one action, and never anonymous** (`frontend-component-spec.md`, `DismissAlarmControl`).

**Nothing here dispatches, cancels or closes anything** (BR-001, BR-005, REQ-R-003). Clearing a
false alarm records that somebody judged it false. The repair job the report was filed against
keeps its status and its place in the queue and stays on the board, reading *explained* rather
than *empty* (CHG-020) — a shared dispatch board that silently drops work is the one thing
`frontend-component-spec.md` says that screen must never do.

**Not privileged.** `technical-spec.md` §7.2 and `security-specification.md` both give the row
*Dismiss a false alarm — Admin yes, User yes*. The dispatcher holds `user` and this is their
screen (REQ-R-001); the deny path is *signed out*, which is SEC-Z-001 and STEST-001's row.

**Every refusal the store would make is made here first, as a `400`.** Not because the check
belongs here — it does not, and migration 014 is where the rule lives (ADR-002) — but because a
caller's mistake must be answered as one. A `500` tells a dispatcher the platform broke, which
during a storm sends them to the wrong person.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.api import errors, views
from app.api.events import log_event
from app.store import decisions, dispatch

router = APIRouter(prefix="/api/v1/damage-reports", tags=["dispatch"])


class Dismissal(BaseModel):
    """What a dispatcher may write down when clearing an alarm, and nothing else.

    `extra="forbid"` is the CON-003 boundary in the API layer, for the reason `api/dispatch.py`
    states about damage reports: dropping an unknown field silently teaches the caller it was
    accepted, and the next caller stores it somewhere else. There is no field here for a place,
    a household or a person other than the one already signed in.
    """

    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


@router.post("/{report_id}/dismiss", status_code=201)
async def dismiss_false_alarm(request: Request, report_id: str, body: Dismissal) -> JSONResponse:
    connection = request.app.state.db
    actor = request.state.user

    report = dispatch.find_report(connection, report_id)
    if report is None:
        return errors.error(404, "not_found", "That damage report could not be found.")

    reason = dispatch.dismissal_reason(body.reason or "")
    if reason is None:
        # The legible 400 in front of `damage_reports_dismissal_is_attributed` (CHG-033). The
        # store refuses an empty, whitespace-only, untrimmed or over-length reason independently;
        # if this test and that constraint disagree the caller gets a `500` where the contract
        # specifies a `400`, which is the mismatch UTEST-012 was written to catch one column over.
        return errors.error(
            400,
            "validation_error",
            "A dismissal needs a reason of up to "
            f"{dispatch.DISMISSAL_REASON_MAX} characters. Clearing an alarm is one action, "
            "and it is never an anonymous one (REQ-F-008).",
        )

    if report["status"] == dispatch.DISMISSED:
        # A second dismissal is a conflict, never an overwrite — BR-004's shape, one table over,
        # and the store refuses the rewrite independently (CHG-034). Decided **before** the write
        # so a retrying client cannot produce two audit rows for one human decision, which is the
        # bug `integration-tests.md` names for the decision endpoint in the same words.
        return errors.error(
            409,
            "conflict",
            "That report was already dismissed as a false alarm, by "
            f"{report['dismissed_by']}. A dismissal is recorded once and is never rewritten.",
        )

    try:
        dismissed, record_id = dispatch.dismiss_report(
            connection, report=report, reason=reason, actor_user_id=actor["id"]
        )
    except Exception:
        # No success is shown, nothing is written, and the reason the dispatcher typed stays on
        # their screen (FTEST-005). The reason itself is not logged: it is somebody's sentence
        # about a live storm, and the audit row is where it belongs — the same rule the placement
        # endpoint follows for its note.
        log_event(
            "DB_WRITE_FAILED",
            level=logging.ERROR,
            user_id=actor["id"],
            scenario_id=report["scenario_id"],
            subject="dismissal",
            outcome="no_row_written",
        )
        raise

    log_event(
        "DAMAGE_REPORT_DISMISSED",
        user_id=actor["id"],
        scenario_id=report["scenario_id"],
        report_id=report_id,
        repair_job_id=report["repair_job_id"],
        dismissal_id=record_id,
        # REQ-NF-007: an area figure, never the report as a place — and the count is of what is
        # still open, so a reader can see what clearing this one left behind.
        open_reports_in_area=dispatch.open_reports_in_area(
            connection,
            report["scenario_id"],
            dispatch.location_key(dispatch.neighbourhood_of(dismissed)),
        ),
        # Stated in the log as well as in the response, because the one thing a reader of this
        # line must not conclude is that a crew was stood down.
        outcome="recorded_not_dispatched",
    )
    return JSONResponse(
        status_code=201,
        content=views.dismissal_item(dismissed, decisions.find_record(connection, record_id)),
    )
