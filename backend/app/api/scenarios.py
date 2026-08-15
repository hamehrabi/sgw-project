"""The scenario endpoints.

`POST /api/v1/scenarios` is admin-only. The role check is here rather than in the middleware
because it is per-action: `security-specification.md` §2 fixes the order as *signed in → role
on that action's allow-list*, and the allow-list belongs to the action. The signed-in half has
already run in `SessionGuard`.
"""

import logging

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from app.api import errors, uploads, views
from app.api.events import log_event
from app.store import decisions, rankings, scenarios

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])

# FastAPI's dependency markers, hoisted out of the signature: calling them in a default
# argument is the mutable-default trap wearing a framework's clothes (ruff B008).
NAME = Form(...)
SOURCE_NOTE = Form(...)
FILES = File(...)


def _is_admin(request: Request) -> bool:
    return request.state.user["role"] == "admin"


@router.post("")
async def load_scenario(
    request: Request,
    name: str = NAME,
    source_note: str = SOURCE_NOTE,
    files: list[UploadFile] = FILES,
) -> JSONResponse:
    config = request.app.state.config
    connection = request.app.state.db

    if not _is_admin(request):
        # AC-009's record, in the security log (CHG-015). Actor, time, filename, reason.
        #
        # **Not in `decision_records`.** That table holds decisions about recommendations, and
        # a refused upload is an access-control event rather than a decision. Putting it there
        # would have meant making `scenario_id` nullable — and a refused upload has no
        # scenario by definition — which trades the not-null constraint that makes the audit
        # table trustworthy for one event type's convenience.
        log_event(
            "SCENARIO_UPLOAD_REFUSED",
            level=logging.WARNING,
            user_id=request.state.user["id"],
            role=request.state.user["role"],
            filenames=[file.filename for file in files],
            reason="not_admin",
            outcome="refused",
        )
        # Generic, and deliberately uninformative: it does not reveal whether the upload
        # endpoint exists or what it accepts (`security-specification.md` §7).
        return uploads.refuse(403, "You do not have permission to perform this action.")

    supplied = {file.filename: await file.read() for file in files}

    refusal = uploads.check_upload(supplied, config)
    if refusal:
        status, message = refusal
        log_event(
            "SCENARIO_UPLOAD_REFUSED",
            level=logging.WARNING,
            user_id=request.state.user["id"],
            status=status,
            outcome="refused_before_parsing",
        )
        return uploads.refuse(status, message)

    # An identical re-load replaces in place rather than creating a rival ranking (§5).
    key = uploads.content_key(supplied)
    existing = scenarios.find_by_content_key(connection, key)
    if existing:
        return JSONResponse(
            status_code=200,
            content={
                "scenario_id": existing["id"],
                "forecast_revision": existing["forecast_revision"],
            },
        )

    directory = uploads.store_files(supplied, config)
    upload_id = scenarios.start_upload(
        connection,
        uploaded_by=request.state.user["id"],
        name=name,
        source_note=key,
        storage_path=str(directory),
    )

    scenario_id = uploads.run_parse(
        connection,
        upload_id,
        directory,
        supplied,
        name=name,
        source_note=key,
        actor_id=request.state.user["id"],
    )

    if scenario_id is None:
        upload = scenarios.find_upload(connection, upload_id)
        return JSONResponse(
            status_code=422,
            content={
                "code": "scenario_parse_failed",
                "message": (
                    f"{upload['failed_file']} could not be read: {upload['failed_reason']}. "
                    f"No scenario was created and every loaded storm is untouched."
                ),
            },
        )

    return JSONResponse(
        status_code=201, content={"scenario_id": scenario_id, "forecast_revision": 0}
    )


@router.get("/{scenario_id}")
async def read_scenario(request: Request, scenario_id: str):
    """The scenario, its data's age, and whether its source files are still intact.

    Readable by every signed-in user (REQ-R-001): loading is privileged, reading is not.
    """
    connection = request.app.state.db
    scenario = scenarios.find(connection, scenario_id)
    if scenario is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    return views.scenario_body(
        scenario,
        scenarios.find_upload_for_scenario(connection, scenario_id),
        request.app.state.config,
    )


@router.get("/{scenario_id}/assets")
async def read_assets(request: Request, scenario_id: str):
    """The joined asset view — one record per asset, each value with its source and age.

    Served entirely from stored rows (`technical-spec.md` §6). No source file is opened on
    this path, which is why FTEST-002's lost file cannot reach it and why FF-003(c) checks
    that no view ever starts.
    """
    connection = request.app.state.db
    scenario = scenarios.find(connection, scenario_id)
    if scenario is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    rows = scenarios.assets_for(connection, scenario_id)
    return {
        "scenario_id": scenario_id,
        "items": [views.asset_item(row) for row in rows],
        # Surfaced rather than left to be counted: AC-001 requires unmatched records to reach
        # a person, and a count nobody is shown is a queue nobody works.
        "needs_review_count": sum(row["match_status"] == "needs_review" for row in rows),
    }


@router.get("/{scenario_id}/decisions")
async def read_decisions(request: Request, scenario_id: str):
    """The decision record. **Admin only** (SEC-Z-003).

    Deciding is not privileged; reading the whole record is. It is the artefact produced to a
    regulator afterwards, and it names who did what.
    """
    if not _is_admin(request):
        log_event(
            "DECISION_RECORD_READ_REFUSED",
            level=logging.WARNING,
            user_id=request.state.user["id"],
            outcome="refused",
        )
        return errors.error(403, "forbidden", "You do not have permission to perform this action.")

    connection = request.app.state.db
    if scenarios.find(connection, scenario_id) is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    return {
        "scenario_id": scenario_id,
        "items": [views.decision_item(row) for row in decisions.read_all(connection, scenario_id)],
    }


@router.get("/{scenario_id}/risks")
async def read_risks(
    request: Request, scenario_id: str, forecast_revision: int | None = None, limit: int = 100
):
    """The ranked risk list. **The core subdomain's endpoint.**

    Reasons arrive in the **same response** as the rank, never on a second request — a
    separate fetch makes "a rank on screen with no reasons" a reachable state, which is
    exactly what BR-002 forbids (`technical-spec.md` §3).

    Any signed-in user. No per-record rules: one organisation, and every role sees the same
    ranking.
    """
    connection = request.app.state.db
    scenario = scenarios.find(connection, scenario_id)
    if scenario is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    if not 1 <= limit <= 500:
        return errors.error(400, "validation_error", "limit must be between 1 and 500.")

    revision = scenario["forecast_revision"] if forecast_revision is None else forecast_revision
    if not rankings.revision_exists(connection, scenario_id, revision):
        # Never a silent fallback to the current revision: that shows one ranking to a reader
        # who believes they are looking at another (`technical-spec.md` §7.3).
        return errors.error(
            404, "not_found", f"This storm has no forecast revision {revision}."
        )

    rows = rankings.read_ranking(connection, scenario_id, revision, limit=limit)

    # FF-005: every delivered ranking has a matching `recommendation` row, so what was shown
    # can be reconstructed later (REQ-F-009). One per revision — re-reading the same ranking
    # is the same recommendation, not a new one, or a reader refreshing a page would fill the
    # audit trail with recommendations nobody made.
    recommendation = decisions.latest_recommendation(connection, scenario_id, revision)
    if recommendation is None:
        recommendation_id = decisions.append_recommendation(
            connection,
            scenario_id=scenario_id,
            forecast_revision=revision,
            payload={
                "weight_set_version": rows[0]["weight_set_version"] if rows else None,
                "ranked": [
                    {"asset_id": row["asset_id"], "rank": row["rank"], "score": row["score"]}
                    for row in rows
                ],
            },
        )
    else:
        recommendation_id = recommendation["id"]

    return {
        "scenario_id": scenario_id,
        "forecast_revision": revision,
        "recommendation_id": recommendation_id,
        "computed_at": rankings.computed_at(connection, scenario_id, revision),
        "weight_set_version": rows[0]["weight_set_version"] if rows else None,
        # Stated in the payload, not only in a screen's copy: any consumer of this ranking
        # has to be able to see that its numbers are uncalibrated (CHG-014, ADR-007).
        "weights_calibrated": False,
        "items": [views.risk_item(row) for row in rows],
        "total": rankings.count_for(connection, scenario_id, revision),
    }
