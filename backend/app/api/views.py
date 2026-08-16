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

import json
from datetime import UTC, datetime
from pathlib import Path

REQUIRED_SOURCE_FILES = (
    "manifest.json",
    "assets.csv",
    "maintenance.csv",
    "weather.csv",
    "outages.csv",
)


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
        _value(
            "wind_gust_mph",
            row["wind_gust_mph"],
            source=f"forecast grid {row['grid_cell_id']}" if row["grid_cell_id"] else None,
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
    }


DISMISSED = "dismissed"


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


def scenario_body(scenario_row, upload_row, config, *, now=None) -> dict:
    issued_at = scenario_row["forecast_issued_at"]
    age = data_age_hours(issued_at, now) if issued_at else None
    return {
        "scenario_id": scenario_row["id"],
        "name": scenario_row["name"],
        "forecast_revision": scenario_row["forecast_revision"],
        "loaded_at": scenario_row["loaded_at"],
        "forecast_issued_at": issued_at,
        # Stated always, never inferred (AC-010) — a screen that only mentions age when it is
        # bad teaches the reader that silence means fresh.
        "data_age_hours": round(age, 2) if age is not None else None,
        "stale": bool(age is not None and age >= config.scenario_stale_after_hours),
        "stale_after_hours": config.scenario_stale_after_hours,
        "integrity": integrity(upload_row["storage_path"] if upload_row else None),
    }
