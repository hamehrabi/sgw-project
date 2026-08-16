"""The scenario endpoints.

`POST /api/v1/scenarios` is admin-only. The role check is here rather than in the middleware
because it is per-action: `security-specification.md` §2 fixes the order as *signed in → role
on that action's allow-list*, and the allow-list belongs to the action. The signed-in half has
already run in `SessionGuard`.
"""

import logging

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from app.api import errors, rerank, uploads, views
from app.api.events import log_event
from app.store import decisions, forecasts, rankings, scenarios, security

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
        # AC-009's record, in the security log (CHG-015; the table itself is CHG-046).
        # Actor, time, filename, reason.
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
        security.log(
            connection,
            event="upload_refused",
            detail=f"upload of {len(files)} file(s) refused: not an admin",
            actor_user_id=request.state.user["id"],
        )
        # Generic, and deliberately uninformative: it does not reveal whether the upload
        # endpoint exists or what it accepts (`security-specification.md` §7).
        return uploads.refuse(403, "You do not have permission to perform this action.")

    # The legible 400 in front of `scenarios_identity_shape`, and it has to agree with it: if the
    # trigger's bounds and `store/scenarios.py`'s drift apart, a value between them arrives as a
    # `500 internal_error` where the contract says `400` — which is what happened to
    # `dispatch.NEIGHBOURHOOD_MAX` with the whole suite green (CHG-023).
    #
    # Before a byte is read, because both of these are refusals that need no file.
    stored_name = scenarios.storm_text(name, scenarios.NAME_MAX)
    if stored_name is None:
        return errors.error(
            400,
            "validation_error",
            f"A storm needs a name of 1 to {scenarios.NAME_MAX} characters. It is what somebody "
            f"picks this storm out by when several are loaded.",
        )
    stored_note = scenarios.storm_text(source_note, scenarios.SOURCE_NOTE_MAX)
    if stored_note is None:
        return errors.error(
            400,
            "validation_error",
            f"A storm needs a source note of 1 to {scenarios.SOURCE_NOTE_MAX} characters — which "
            f"prepared dataset this is, and where it came from.",
        )

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
        name=stored_name,
        # The note the admin typed. It used to be the content digest, because the digest §5's
        # idempotency rule turns on had no column of its own and squatted in the one
        # `database-design.md` §3 defines as *where it came from* (CHG-031).
        source_note=stored_note,
        storage_path=str(directory),
    )

    scenario_id = uploads.run_parse(
        connection,
        upload_id,
        directory,
        supplied,
        name=stored_name,
        source_note=stored_note,
        content_key=key,
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


@router.post("/sample")
async def load_sample_scenario(request: Request) -> JSONResponse:
    """"Use sample storm data" — the same parse path as a real upload, not a shortcut.

    The files come from `SAMPLE_SCENARIO_DIR` instead of the request body, and from there
    on nothing differs: the same content checks, the same seven defect rules, the same
    ranking at load, the same idempotent replace on identical content. The quality
    summary that renders afterwards is measured from this parse, never hard-coded.

    Admin only, exactly as the upload it is a stand-in for.
    """
    import pathlib

    config = request.app.state.config
    connection = request.app.state.db

    if not _is_admin(request):
        log_event(
            "SCENARIO_UPLOAD_REFUSED",
            level=logging.WARNING,
            user_id=request.state.user["id"],
            role=request.state.user["role"],
            reason="not_admin",
            outcome="refused",
        )
        return uploads.refuse(403, "You do not have permission to perform this action.")

    directory = pathlib.Path(config.sample_scenario_dir)
    if not directory.is_dir():
        return errors.error(
            422,
            "sample_unavailable",
            "The sample dataset is not on disk. Set SAMPLE_SCENARIO_DIR to a prepared scenario.",
        )
    supplied = {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()}

    refusal = uploads.check_upload(supplied, config)
    if refusal:
        status, message = refusal
        return uploads.refuse(status, message)

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

    # The storm names itself from its own manifest — nobody typed anything.
    import json as _json

    try:
        manifest = _json.loads(supplied.get("manifest.json", b"{}").decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        manifest = {}
    stored_name = scenarios.storm_text(
        str(manifest.get("storm_name") or "Sample storm"), scenarios.NAME_MAX
    )
    stored_note = scenarios.storm_text("Bundled sample dataset", scenarios.SOURCE_NOTE_MAX)

    stored = uploads.store_files(supplied, config)
    upload_id = scenarios.start_upload(
        connection,
        uploaded_by=request.state.user["id"],
        name=stored_name,
        source_note=stored_note,
        storage_path=str(stored),
    )
    scenario_id = uploads.run_parse(
        connection,
        upload_id,
        stored,
        supplied,
        name=stored_name,
        source_note=stored_note,
        content_key=key,
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
                    f"No scenario was created."
                ),
            },
        )
    return JSONResponse(
        status_code=201, content={"scenario_id": scenario_id, "forecast_revision": 0}
    )


@router.get("")
async def list_scenarios(request: Request):
    """Every loaded storm — `ScenarioSwitcher`'s input, and the endpoint the index did not carry.

    **CHG-030, proposed.** `frontend-component-spec.md` gives the switcher *loaded scenarios:
    name, source note, loaded date*; `product-spec.md` §9's load flow promises the new storm
    *"appears in the list alongside any others already loaded, and becomes selectable"*; and the
    endpoint index carried `POST /scenarios` and `GET /scenarios/{id}` and no collection read. It
    is CHG-009's shape exactly — a component required to know something with no endpoint that
    returns it.

    **Signed in, both roles.** `technical-spec.md` §7.2: *Switch between loaded scenarios — Admin
    yes, User yes*, and `database-design.md` §5: *Scenario — written only by an admin, readable
    by every signed-in user.* Loading is privileged; choosing which loaded storm to look at is
    the product.

    **A read, and only a read.** Nothing is marked current, nothing is archived, and no storm
    changes because somebody looked at a different one.
    """
    connection = request.app.state.db
    rows = scenarios.all_loaded(connection)
    return {
        "items": [
            views.loaded_scenario_item(row, request.app.state.config) for row in rows
        ],
        "total": len(rows),
    }


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
        # `ForecastRevisionControl` needs "current and available revisions" — a control that
        # guessed the range would offer a forecast this storm does not carry.
        revisions=forecasts.revisions(connection, scenario_id),
    )


@router.post("/{scenario_id}/forecast-revisions", status_code=201)
async def apply_forecast_revision(request: Request, scenario_id: str) -> JSONResponse:
    """Apply the scenario's next forecast change and re-rank (REQ-F-004, AC-005).

    **A write that produces a new revision, and never a rewrite of the old one.** Both roles
    may do it (`technical-spec.md` §7.2): adjusting the plan when the forecast moves is the
    product, not an administrative action.

    **The change comes from inside the prepared scenario.** REQ-F-004 says so, and it is a
    safety property rather than a convenience: a gust supplied by the caller would make the
    ranking a function of untrusted input, and this endpoint takes no body at all.

    **No `decision_records` row.** `kind` is a closed enumeration of six values and none of
    them is *re-ranked*; the new ranking gets its `recommendation` row when it is delivered,
    which is FF-005 unchanged. Inventing a seventh kind would be a schema decision this task
    does not own — the reasoning CHG-021 used for `duplicate`, and CHG-015 before it.

    **Nothing leaves the platform.** A re-rank moves no crew and sends no command (BR-001,
    BR-005).
    """
    connection = request.app.state.db
    scenario = scenarios.find(connection, scenario_id)
    if scenario is None:
        return errors.error(404, "not_found", "That storm could not be found.")

    current = scenario["forecast_revision"]
    following = forecasts.next_after(connection, scenario_id, current)
    if following is None:
        # 409 rather than 404: the collection in the path exists, and what is in conflict is
        # the storm's state — it is already at its last forecast. Repeating the current
        # forecast as a new revision would be a ranking nobody's data supports.
        return errors.error(
            409,
            "no_further_forecast",
            f"This storm carries no forecast after revision {current}. A newer forecast "
            f"arrives by loading a newer prepared scenario.",
        )

    revision = following["forecast_revision"]
    scoring = rerank.score_revision(connection, scenario_id, revision)

    # CHG-044: the strip's rows are the diff of this pass against the ranking it
    # supersedes, computed before the write and stored inside it — a revision whose
    # ranking exists but whose movement does not is a strip lying by omission.
    moved = rerank.movement_between(connection, scenario_id, current, scoring)
    previous_row = connection.execute(
        "select valid_time from scenario_forecast_revisions"
        " where scenario_id = ? and forecast_revision = ?",
        (scenario_id, current),
    ).fetchone()

    try:
        computed_at = rankings.save_revision(
            connection,
            scenario_id=scenario_id,
            from_revision=current,
            to_revision=revision,
            ranked=scoring.pairs,
            weight_set_version=scoring.weight_set_version,
            movement_rows=moved,
            movement_label=(
                f"the {previous_row['valid_time']} forecast"
                if previous_row
                else f"revision {current}"
            ),
        )
    except Exception:
        # Neither the ranking nor the pointer moved — `save_revision` is one transaction. The
        # operator sees a failure and the storm still ranks at the revision it did before.
        log_event(
            "DB_WRITE_FAILED",
            level=logging.ERROR,
            user_id=request.state.user["id"],
            scenario_id=scenario_id,
            subject="forecast_revision",
            outcome="no_revision_written",
        )
        raise

    log_event(
        "SCENARIO_RERANKED",
        user_id=request.state.user["id"],
        scenario_id=scenario_id,
        forecast_revision=revision,
        previous_forecast_revision=current,
        valid_time=following["valid_time"],
        ranked=scoring.ranked,
        unscored=scoring.unscored,
        weight_set_version=scoring.weight_set_version,
        outcome="reranked",
    )

    remaining = forecasts.next_after(connection, scenario_id, revision)
    return JSONResponse(
        status_code=201,
        content={
            "scenario_id": scenario_id,
            "forecast_revision": revision,
            # Named in the response, because the whole point of AC-005 is that the reader can
            # go back and ask for it.
            "previous_forecast_revision": current,
            "valid_time": following["valid_time"],
            "computed_at": computed_at,
            "ranked": scoring.ranked,
            "unscored": scoring.unscored,
            "next_forecast_revision": (
                remaining["forecast_revision"] if remaining else None
            ),
        },
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
        security.log(
            request.app.state.db,
            event="permission_denied",
            detail="decision record read refused: not an admin",
            actor_user_id=request.state.user["id"],
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
    request: Request,
    scenario_id: str,
    forecast_revision: int | None = None,
    limit: int = 100,
    cursor: str | None = None,
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

    # The page to start at. **Never a silent fall back to the first page** — a caller walking a
    # list past an unreadable cursor would restart it and believe they had seen the whole storm,
    # which is §7.3's rule about `forecast_revision` one parameter over.
    offset = 0
    if cursor is not None:
        decoded = views.decode_cursor(cursor)
        if decoded is None:
            return errors.error(
                400,
                "validation_error",
                "That cursor could not be read. Ask for the first page and follow next_cursor.",
            )
        if decoded["s"] != scenario_id:
            # REQ-F-010's blend, arriving through the paging parameter: one storm's page served
            # under another storm's name would look entirely ordinary on screen.
            return errors.error(
                400,
                "validation_error",
                "That cursor was issued for another storm. A page of one storm's ranking is "
                "never served under another's.",
            )
        if decoded["r"] != revision:
            return errors.error(
                400,
                "validation_error",
                f"That cursor was issued for forecast revision {decoded['r']} of this storm, "
                f"not {revision}.",
            )
        offset = decoded["o"]

    rows = rankings.read_ranking(connection, scenario_id, revision, limit=limit, offset=offset)
    total = rankings.count_for(connection, scenario_id, revision)

    # FF-005: every delivered ranking has a matching `recommendation` row, so what was shown
    # can be reconstructed later (REQ-F-009). One per revision — re-reading the same ranking
    # is the same recommendation, not a new one, or a reader refreshing a page would fill the
    # audit trail with recommendations nobody made.
    #
    # **Recorded from the whole ranking, never from the page.** A recommendation naming the five
    # rows somebody happened to be looking at cannot reconstruct what was delivered, which is the
    # only thing the row exists to do.
    whole = rankings.recorded_ranking(connection, scenario_id, revision)
    weight_set_version = whole[0]["weight_set_version"] if whole else None
    recommendation = decisions.latest_recommendation(connection, scenario_id, revision)
    if recommendation is None:
        recommendation_id = decisions.append_recommendation(
            connection,
            scenario_id=scenario_id,
            forecast_revision=revision,
            payload={
                "weight_set_version": weight_set_version,
                "ranked": [
                    {"asset_id": row["asset_id"], "rank": row["rank"], "score": row["score"]}
                    for row in whole
                ],
            },
        )
    else:
        recommendation_id = recommendation["id"]

    served = offset + len(rows)
    return {
        "scenario_id": scenario_id,
        "forecast_revision": revision,
        "recommendation_id": recommendation_id,
        "computed_at": rankings.computed_at(connection, scenario_id, revision),
        "weight_set_version": weight_set_version,
        # Stated in the payload, not only in a screen's copy: any consumer of this ranking
        # has to be able to see that its numbers are uncalibrated (CHG-014, ADR-007).
        "weights_calibrated": False,
        "items": [views.risk_item(row) for row in rows],
        "total": total,
        # Null on the last page, so a caller stops rather than asking for an empty one — and the
        # scope travels inside it, so the next page cannot be asked for against another storm.
        "next_cursor": (
            views.encode_cursor(scenario_id, revision, served) if served < total else None
        ),
    }
