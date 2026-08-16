"""Turning stored rows into the shapes the screens are specified against.

Response shaping, not business rules. Nothing here computes a score, a rank or a band — that
is `scoring/`'s, and it does not exist yet.

Two properties are decided here because a screen cannot invent either one:

- **Every value carries its source and its age** (BR-003). There is no shape of an asset
  response without them, so they are assembled rather than optionally attached.
- **Staleness is the age of the data**, computed from `forecast_issued_at` against
  `SCENARIO_STALE_AFTER_HOURS` (CHG-013). It is never the presence of a file: reads come from
  stored rows, so a lost file leaves the picture correct.
"""

import base64
import binascii
import json
from datetime import UTC, datetime
from pathlib import Path

from app.store import dispatch

REQUIRED_SOURCE_FILES = (
    "manifest.json",
    "assets.csv",
    "maintenance.csv",
    "weather.csv",
    "outages.csv",
)


def _optional(row, column):
    """A column two of the three asset reads carry.

    `assets_for` and `read_ranking` both select `forecast_valid_time`; a row assembled some
    other way should render a value with an unknown age rather than a 500 during a storm.
    """
    # A `sqlite3.Row` is a sequence: `column in row` would test its VALUES, not its column
    # names, and would answer `False` for a column holding `None`.
    names = row.keys()
    return row[column] if column in names else None


def _value(name, value, *, source=None, observed_at=None, estimated=False):
    """One displayable value. Source and age are structural, never optional (BR-003)."""
    return {
        "name": name,
        "value": value,
        "source": source,
        "observed_at": observed_at,
        "estimated": estimated,
    }


def values_for(row) -> list[dict]:
    """The displayable values of one asset, with source and age on every one (BR-003).

    Shared by the asset view and the ranking so the two cannot disagree about what a value
    is or where it came from — and so a reader who questions a rank is questioning the same
    figures the asset table shows.
    """
    return [
        _value(
            "condition",
            row["condition"],
            source=row["condition_source"],
            observed_at=row["condition_observed_at"],
            estimated=bool(row["condition_estimated"]),
        ),
        # Defect 3: the gust is the forecast grid square's, and says so. An operator who
        # cannot see which cell a reading came from cannot tell it apart from a station read.
        #
        # `observed_at` is the forecast's own `valid_time` (CHG-025). BR-003 wants the age of
        # every value, and this one had none — which mattered the moment a second forecast
        # existed: a gust carried forward from six hours ago must not read as current, and a
        # rank recomputed against a newer forecast must not sit beside the older number.
        _value(
            "wind_gust_mph",
            row["wind_gust_mph"],
            source=f"forecast grid {row['grid_cell_id']}" if row["grid_cell_id"] else None,
            observed_at=_optional(row, "forecast_valid_time"),
        ),
        _value("flood_zone", row["flood_zone"], source="assets.csv"),
        _value("install_year", row["install_year"], source="assets.csv"),
    ]


def asset_item(row) -> dict:
    return {
        "asset_id": row["id"],
        "external_ids": json.loads(row["external_ids"]),
        "name": row["name"],
        "type": row["type"],
        "location": json.loads(row["location"]),
        "match_status": row["match_status"],
        "values": values_for(row),
    }


def decision_item(row) -> dict:
    """One row of the append-only record, as produced to a reader.

    Nothing here is editable and nothing offers an id to edit *with* — the response shape is
    the same shape the row has, because an audit trail that reformats itself on the way out is
    harder to reconcile with what was stored.
    """
    return {
        "id": row["id"],
        "occurred_at": row["occurred_at"],
        "actor_user_id": row["actor_user_id"],
        "kind": row["kind"],
        "subject_type": row["subject_type"],
        "subject_id": row["subject_id"],
        "payload": json.loads(row["payload"]),
    }


def placement_item(row) -> dict:
    """One crew placement, as the operator who recorded it reads it back.

    Assembled from the **stored row** rather than from the request that made it, so the
    confirmation on screen is what the audit trail holds and not what was asked for. The
    `forecast_revision` is the one the placement was made against — deliberately not the storm's
    current pointer, which moves.

    No location beyond the assets named, because none is stored (CON-003).
    """
    payload = json.loads(row["payload"])
    return {
        "placement_id": row["id"],
        "scenario_id": row["scenario_id"],
        "forecast_revision": payload["forecast_revision"],
        "recommendation_id": payload["recommendation_id"],
        "crew": payload["crew"],
        "asset_ids": payload["asset_ids"],
        "note": payload["note"],
        "actor_user_id": row["actor_user_id"],
        "occurred_at": row["occurred_at"],
    }


def risk_item(row) -> dict:
    """One ranked asset, with its reasons and the values they rest on.

    `reasons` is never empty and never omitted for a scored asset — BR-002 makes it part of
    the contract rather than a convenience, and the store refuses a row without it. An
    UNSCORED asset carries `unscored_reason` instead: it is in the ranking, not ranked, and
    never given a low score (FTEST-004).
    """
    return {
        "asset_id": row["asset_id"],
        "external_ids": json.loads(row["external_ids"]),
        "name": row["name"],
        "type": row["type"],
        "rank": row["rank"],
        "score": row["score"],
        "band": row["band"],
        "reasons": json.loads(row["reasons"]),
        "unscored_reason": row["unscored_reason"],
        "weight_set_version": row["weight_set_version"],
        "match_status": row["match_status"],
        # BR-003 travels with the rank: every value the reasons rest on keeps its source and
        # its age, so a reader can question an input rather than only the conclusion.
        "values": values_for(row),
    }


def damage_report_item(row) -> dict:
    """One damage report, as the board and the filing response both show it.

    **`asset_id` and never an asset location** (REQ-NF-007, STEST-009): the asset table stores
    coordinates and this path must not carry them out. The report's own location is a
    neighbourhood, because the store cannot hold anything finer (CON-003).
    """
    return {
        "report_id": row["id"],
        "asset_id": row["asset_id"],
        "repair_job_id": row["repair_job_id"],
        "location": json.loads(row["location"]),
        "reported_at": row["reported_at"],
        "reported_by": row["reported_by"],
        "status": row["status"],
        # CHG-050's two impact facts. Guarded by key because the dismissal path reads the
        # report alone, without the board's asset join. `.keys()` is the sqlite3.Row
        # membership idiom, not a dict anti-pattern: `in row` is a TypeError.
        "customers_out": (
            row["customers_out"] if "customers_out" in row.keys() else None  # noqa: SIM118
        ),
        "asset_is_critical": bool(
            row["asset_is_critical"] if "asset_is_critical" in row.keys() else 0  # noqa: SIM118
        ),
    }


# Read from the store rather than spelled again here: the filter that decides what the board
# shows and the writer that sets the status are the same fact, and two copies of one string are
# two facts the day either moves (TASK-008).
DISMISSED = dispatch.DISMISSED


def dismissal_item(report_row, record_row) -> dict:
    """One cleared false alarm, as the dispatcher who cleared it reads it back (REQ-F-008).

    Assembled from the **stored rows** rather than from the request that made it, so the
    confirmation on screen is what the record holds and not what was asked for — the same reason
    `placement_item` is built that way.

    `dismissal_id` is the append-only row. It is returned because *never anonymous* is a claim
    about a record, and a caller that cannot name the record cannot check the claim.

    No location beyond the neighbourhood, because none is stored (CON-003).
    """
    return {
        "report_id": report_row["id"],
        "scenario_id": report_row["scenario_id"],
        "repair_job_id": report_row["repair_job_id"],
        "location": json.loads(report_row["location"]),
        "status": report_row["status"],
        "dismissed_by": report_row["dismissed_by"],
        "dismissed_reason": report_row["dismissed_reason"],
        "dismissal_id": record_row["id"],
        "occurred_at": record_row["occurred_at"],
    }


def repair_job_item(job_row, filed: list[dict]) -> dict:
    """One job and every report behind it.

    `filed` is every report ever filed against this job, oldest first, **whatever its status** —
    which is what the two halves below need, and they need different halves.

    Both halves of AC-007 are visible here: **one** job for the location, and **every** report
    that arrived for it. An implementation that de-duplicated instead would satisfy the first
    and lose the second — a second radio call about the same street with no record of it.

    **The location comes from the first report ever filed, not from the first still open**
    (CHG-020). CHG-017 declined a display column on `repair_jobs` on the ground that "the board
    derives a job's neighbourhood from its first report", and it does — but the derivation used
    to read the working list, so dismissing a job's only report left the board showing a job
    with `{"neighbourhood": null}`: work on a shared dispatcher's board with no location.
    Dismissal hides a report from the working list; it does not unsay where the job is.

    A dismissed report is counted rather than silently dropped, so a job whose reports have all
    been dismissed reads as *explained* rather than as empty.

    No rank, no score, no band.
    """
    working = [report for report in filed if report["status"] != DISMISSED]
    # CHG-050: priority is derived from IMPACT — what has already happened — and never
    # from a risk score. Two facts decide it: a critical facility among the open reports'
    # assets, and the customers those reports account for. The scorer is not consulted,
    # `priority_rank` stays null, and the vocabulary is the frozen one: High/Medium/Low,
    # never "Critical", never "Standard".
    customers = sum(report["customers_out"] or 0 for report in working)
    if any(report["asset_is_critical"] for report in working):
        priority = "High"
    elif customers >= dispatch.IMPACT_CUSTOMERS_MEDIUM_AT:
        priority = "Medium"
    else:
        priority = "Low"
    return {
        "job_id": job_row["id"],
        "status": job_row["status"],
        "priority_rank": job_row["priority_rank"],
        "assigned_to": job_row["assigned_to"],
        "location": filed[0]["location"] if filed else {"neighbourhood": None},
        "created_at": job_row["created_at"],
        "updated_at": job_row["updated_at"],
        "report_count": len(working),
        "dismissed_report_count": len(filed) - len(working),
        "priority": priority,
        "customers_out": customers,
        "reports": working,
    }


def board_body(scenario_id: str, jobs, reports) -> dict:
    """The shared board. Grouped in memory from two queries, never one query per job.

    `reports` carries every status; the split into what is shown and what was dismissed happens
    here rather than in SQL, so the board stays at two statements however many reports exist
    (PTEST-002) and a job's location survives the dismissal of the report it came from.

    **A report that belongs to no repair job is on the board too** (CHG-022). `repair_job_id` is
    optional in `database-design.md` §3 and §1 says a report belongs *"to **at most** one repair
    job"* — so the state exists, and this function used to group by that column and then emit
    one item **per job**, which left every unattached report in a bucket keyed `None` that
    nothing read. A report nobody can find is the radio call AC-007's second half exists to
    keep, and *an empty screen must never read as safety*. They come back in their own group,
    counted with the rest.

    The empty state is an empty list with its counts stated — `no damage reported`, which the
    screen must never render as `all clear`.
    """
    grouped: dict[str | None, list[dict]] = {}
    for row in reports:
        grouped.setdefault(row["repair_job_id"], []).append(damage_report_item(row))

    items = [repair_job_item(job, grouped.get(job["id"], [])) for job in jobs]
    # CHG-050: the queue is ordered by impact — High first — and by arrival within a
    # band, which the stable sort preserves because `jobs` arrives seq-ordered. This is
    # impact order, not risk order: nothing from risk_scores touched any of these rows.
    items.sort(key=lambda item: {"High": 0, "Medium": 1, "Low": 2}[item["priority"]])

    # The `None` bucket, read rather than dropped. Split the same way a job's reports are, so a
    # dismissed unattached report is explained rather than merely gone.
    filed_without_a_job = grouped.get(None, [])
    unattached = [report for report in filed_without_a_job if report["status"] != DISMISSED]
    unattached_dismissed = len(filed_without_a_job) - len(unattached)

    return {
        "scenario_id": scenario_id,
        "items": items,
        "unattached_reports": unattached,
        "job_count": len(jobs),
        "report_count": sum(item["report_count"] for item in items) + len(unattached),
        "dismissed_report_count": (
            sum(item["dismissed_report_count"] for item in items) + unattached_dismissed
        ),
    }


def finding_item(row) -> dict:
    """One data-quality finding (CHG-047), exactly as stored at load."""
    return {
        "finding_id": row["id"],
        "defect": row["defect"],
        "code": row["code"],
        "subject": row["subject"],
        "message": row["message"],
        "affected_file": row["affected_file"],
        "needs_decision": bool(row["needs_decision"]),
        "resolution": row["resolution"],
        "resolved_by": row["resolved_by"],
        "resolved_at": row["resolved_at"],
    }


def match_candidate_item(row) -> dict:
    """One withheld merge (CHG-048). Confidence is a word, never a percentage."""
    return {
        "candidate_id": row["id"],
        "asset_id": row["asset_id"],
        "map_record": json.loads(row["map_record"]),
        "candidate_record": json.loads(row["candidate_record"]),
        "confidence": row["confidence"],
        "resolution": row["resolution"],
        "resolved_by": row["resolved_by"],
        "resolved_at": row["resolved_at"],
    }


def staging_body(scenario_id: str, areas, plan, high_count: int) -> dict:
    """The staging panel (CHG-049). No per-depot recommendation — none can be defended
    without an asset-to-area mapping the format does not carry. The high-band count is
    context, read from the stored ranking, and it recommends nothing."""
    recorded = json.loads(plan["depots"]) if plan else []
    counts = {depot["service_area_id"]: depot.get("crews", 0) for depot in recorded}
    return {
        "scenario_id": scenario_id,
        "depots": [
            {
                "service_area_id": area["service_area_id"],
                "name": area["name"] or area["service_area_id"],
                "customer_count": area["customer_count"],
                "crews": counts.get(area["service_area_id"], 0),
            }
            for area in areas
        ],
        "high_risk_count": high_count,
        "recorded_at": plan["created_at"] if plan else None,
        "recorded_by": plan["actor_user_id"] if plan else None,
        "forecast_revision": plan["forecast_revision"] if plan else None,
    }


def summary_item(row) -> dict:
    """One situation summary (CHG-040), verification and all. The label travels with the
    text so a reader can always tell a model draft from assembled figures."""
    return {
        "summary_id": row["id"],
        "scenario_id": row["scenario_id"],
        "state": row["state"],
        "draft_text": row["draft_text"],
        "approved_text": row["approved_text"],
        "label": row["label"],
        "source_figures": json.loads(row["source_figures"]),
        "verification": json.loads(row["verification"]),
        "drafted_at": row["drafted_at"],
        "drafted_by": row["drafted_by"],
        "approved_by": row["approved_by"],
        "approved_at": row["approved_at"],
    }


def asset_summary_item(row) -> dict:
    """One stored per-asset summary (CHG-059). The label always travels with the text."""
    return {
        "asset_summary_id": row["id"],
        "scenario_id": row["scenario_id"],
        "asset_id": row["asset_id"],
        "forecast_revision": row["forecast_revision"],
        "text": row["text"],
        "label": row["label"],
        "source_figures": json.loads(row["source_figures"]),
        "verification": json.loads(row["verification"]),
        "created_at": row["created_at"],
        "created_by": row["created_by"],
    }


def movement_item(row) -> dict:
    """One riser from the stored diff (CHG-044)."""
    return {
        "asset_id": row["asset_id"],
        "previous_rank": row["previous_rank"],
        "current_rank": row["current_rank"],
        "band": row["band"],
        "reason_factor": row["reason_factor"],
        "reason_detail": row["reason_detail"],
        "previous_label": row["previous_label"],
    }


def encode_cursor(scenario_id: str, forecast_revision: int, offset: int) -> str:
    """The opaque `cursor` `api-specification.md` writes into the `GET /risks` contract.

    **It carries the storm and the revision it was issued for, and that is the point.** A page of
    one storm's ranking served under another storm's name is REQ-F-010's blend with no visible
    symptom — the response would look entirely ordinary. Carrying the scope inside the token makes
    a crossed cursor something the endpoint can refuse rather than something a reader has to
    notice.

    Opaque, not signed. It grants nothing: every field in it is re-checked against the request,
    and the worst a forged one can do is ask for a page of a ranking the caller may already read.
    """
    raw = json.dumps(
        {"s": scenario_id, "r": forecast_revision, "o": offset}, separators=(",", ":")
    )
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(value: str) -> dict | None:
    """The cursor's three fields, or `None` if it is not one.

    Never a fall back to page one. A caller walking a list past an unreadable cursor would
    silently restart it — reading the same page forever, or believing they had seen the whole
    storm, which is the failure `technical-spec.md` §7.3 forbids for `forecast_revision` in the
    same words.
    """
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        payload = json.loads(raw.decode())
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict) or set(payload) != {"s", "r", "o"}:
        return None
    if not isinstance(payload["s"], str) or not isinstance(payload["r"], int):
        return None
    # `bool` is an `int` in Python, and `True` as an offset would silently mean 1.
    if not isinstance(payload["o"], int) or isinstance(payload["o"], bool) or payload["o"] < 0:
        return None
    return payload


def loaded_scenario_item(row, config, *, now=None) -> dict:
    """One storm as `ScenarioSwitcher` reads it (CHG-030).

    `frontend-component-spec.md` asks for *name, source note, loaded date*; the age travels with
    them because AC-010 requires every screen to state how old its data is **always**, and a
    switcher that named a six-day-old storm as though it were current would be the first screen
    to break that rule.

    **No asset, no coordinate, no neighbourhood** (CON-003, REQ-NF-007). A count is the finest
    thing here, and this is the cheapest place in the product for something finer to be added by
    accident — a switcher row reading "3 substations at risk" would look helpful.
    """
    issued_at = row["forecast_issued_at"]
    age = data_age_hours(issued_at, now) if issued_at else None
    return {
        "scenario_id": row["id"],
        "name": row["name"],
        "source_note": row["source_note"],
        "loaded_at": row["loaded_at"],
        "forecast_revision": row["forecast_revision"],
        "forecast_issued_at": issued_at,
        "data_age_hours": round(age, 2) if age is not None else None,
        "stale": bool(age is not None and age >= config.scenario_stale_after_hours),
        "asset_count": row["asset_count"],
        # Whether the storm's current revision has an order behind it. A storm can be loaded and
        # unranked, and a switcher that could not tell would offer the reader an empty screen.
        "ranked": bool(row["ranked"]),
    }


def data_age_hours(forecast_issued_at: str, now: datetime | None = None) -> float | None:
    now = now or datetime.now(UTC)
    try:
        issued = datetime.fromisoformat(forecast_issued_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if issued.tzinfo is None:
        issued = issued.replace(tzinfo=UTC)
    return (now - issued).total_seconds() / 3600.0


def integrity(storage_path: str | None) -> dict:
    """Are the uploaded files still there?

    Not a render-path concern — nothing on a screen depends on the answer. It is reported
    because the files are `ai-evals.md`'s replay input and half of what `technical-spec.md`
    §12 calls a backup, so losing one is a real operational fact with a real consequence.
    """
    if not storage_path:
        return {"intact": True, "missing_files": [], "affects": []}

    directory = Path(storage_path)
    missing = sorted(
        name for name in REQUIRED_SOURCE_FILES if not (directory / name).is_file()
    )
    return {
        "intact": not missing,
        "missing_files": missing,
        # Named precisely, because "something is wrong" sends someone looking at the screens,
        # which are fine.
        "affects": ["replay", "recovery"] if missing else [],
    }


def scenario_body(scenario_row, upload_row, config, *, revisions=(), now=None) -> dict:
    issued_at = scenario_row["forecast_issued_at"]
    age = data_age_hours(issued_at, now) if issued_at else None
    current = scenario_row["forecast_revision"]
    later = [row for row in revisions if row["forecast_revision"] > current]
    return {
        "scenario_id": scenario_row["id"],
        "name": scenario_row["name"],
        "forecast_revision": current,
        # Every revision this storm carries, with the forecast time behind each one. A
        # re-rank is not "one more" — the series is a property of the prepared file, and a
        # control that guessed at it would offer a forecast that does not exist (CHG-025).
        #
        # **`ranked` says which of them can be read back** (CHG-027). The list is the forecasts
        # the FILE carries and it is complete from the moment the storm is loaded; a ranking
        # exists only where somebody has applied one. Nothing in this response distinguished
        # the two, so `ForecastRevisionControl` offered a button per entry and pressing an
        # unapplied one answered the 404 §7.3 requires — correctly — and took the whole screen
        # down with it. A revision with no ranking is a forecast that is *coming*, not an order
        # that can be compared, and the response has to be able to say so.
        "forecast_revisions": [
            {
                "forecast_revision": row["forecast_revision"],
                "valid_time": row["valid_time"],
                "ranked": bool(row["ranked"]),
            }
            for row in revisions
        ],
        # Null once the storm is at its last forecast, so the control disables rather than
        # offering an action that answers 409.
        "next_forecast_revision": later[0]["forecast_revision"] if later else None,
        "loaded_at": scenario_row["loaded_at"],
        "forecast_issued_at": issued_at,
        # Stated always, never inferred (AC-010) — a screen that only mentions age when it is
        # bad teaches the reader that silence means fresh.
        "data_age_hours": round(age, 2) if age is not None else None,
        "stale": bool(age is not None and age >= config.scenario_stale_after_hours),
        "stale_after_hours": config.scenario_stale_after_hours,
        "integrity": integrity(upload_row["storage_path"] if upload_row else None),
    }
