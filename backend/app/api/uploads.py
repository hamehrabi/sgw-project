"""Accepting a prepared storm.

The only place untrusted input enters the system, so the order of the checks is the design:

    signed in  →  admin  →  size  →  type by content  →  stored  →  parsed

Everything before *stored* refuses without writing a byte to disk, which is what
`security-specification.md` §7 means by "refused before parsing wherever the check allows it".
Size comes before content inspection because inspecting an unbounded file is the work an
attacker wanted done.
"""

import hashlib
import json
import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.api import errors
from app.api.events import log_event
from app.loader.load import load_scenario
from app.loader.records import LoadFailed
from app.scoring import references
from app.scoring.rank import rank_assets
from app.store import rankings, scenarios


@dataclass
class _Scorable:
    """A stored asset row, in the shape the scorer reads.

    The scorer takes values, not database rows — it knows nothing about the store, which is
    what keeps it a pure function and lets a trained model replace it without touching either
    side (ADR-005, `ai-boundary-spec.md` §2).
    """

    external_ids: list[str]
    name: str
    type: str
    flood_zone: str | None
    install_year: int | None
    condition: str | None
    condition_observed_at: str | None
    condition_estimated: bool
    wind_gust_mph: float | None


def _as_scorable(rows) -> list[_Scorable]:
    return [
        _Scorable(
            external_ids=json.loads(row["external_ids"]),
            name=row["name"] or "",
            type=row["type"],
            flood_zone=row["flood_zone"],
            install_year=row["install_year"],
            condition=row["condition"],
            condition_observed_at=row["condition_observed_at"],
            condition_estimated=bool(row["condition_estimated"]),
            wind_gust_mph=row["wind_gust_mph"],
        )
        for row in rows
    ]

ALLOWED_FILES = frozenset(
    {"manifest.json", "assets.csv", "maintenance.csv", "weather.csv", "outages.csv"}
)


def looks_like_text(content: bytes) -> bool:
    """Content inspection, not the extension.

    An extension is a claim made by whoever uploaded the file. These files are CSV and JSON —
    text — so the check is that the bytes decode and carry no NUL, which every binary
    container the allow-list might be wearing a `.csv` name over will fail.
    """
    if b"\x00" in content[:8192]:
        return False
    try:
        content[:8192].decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    return True


def check_upload(files: dict[str, bytes], config) -> tuple[int, str] | None:
    """Return (status, message) for a refusal, or None to proceed. Nothing is written yet."""
    total = 0
    for name, content in files.items():
        total += len(content)
        if len(content) > config.scenario_max_file_bytes:
            return 413, f"{name} is larger than the {config.scenario_max_file_bytes}-byte limit."
    if total > config.scenario_max_total_bytes:
        return 413, f"The upload is larger than the {config.scenario_max_total_bytes}-byte limit."

    for name, content in files.items():
        if name not in ALLOWED_FILES:
            return 415, f"{name} is not part of a prepared scenario."
        if not looks_like_text(content):
            return 415, f"{name} is not the type its name claims."
    return None


def content_key(files: dict[str, bytes]) -> str:
    """A digest of the whole upload. Identical content replaces in place (§5)."""
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode())
        digest.update(files[name])
    return digest.hexdigest()


def store_files(files: dict[str, bytes], config) -> Path:
    """Under a generated identifier — never under a supplied filename."""
    directory = Path(config.scenario_upload_dir) / f"UPL-{uuid.uuid4().hex}"
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (directory / name).write_bytes(content)
    return directory


def run_parse(connection, upload_id, directory, files, *, name, source_note, actor_id):
    """The parse. Never retried automatically — a malformed file is a fact about the file.

    Runs after the response in production (§9.5's background job) and inline here; either way
    it is the same function, and either way a failure removes everything it wrote.
    """
    try:
        result = load_scenario(files)
    except LoadFailed as failure:
        scenarios.mark_upload_failed(
            connection, upload_id, file=failure.file, reason=failure.reason
        )
        shutil.rmtree(directory, ignore_errors=True)
        log_event(
            "SCENARIO_PARSE_FAILED",
            level=logging.ERROR,
            upload_id=upload_id,
            failing_file=failure.file,
            stage=failure.stage,
            outcome="no_scenario_created",
        )
        return None

    scenario_id = scenarios.save_loaded_scenario(
        connection,
        result,
        upload_id=upload_id,
        name=name,
        source_note=source_note,
        loaded_by=actor_id,
    )

    # Rank at load, store the result, and serve reads from it. Scoring inside a request would
    # make the same ranking recomputable — and therefore able to differ — between two readers
    # of the same revision (`technical-spec.md` §6).
    stored_assets = scenarios.assets_for(connection, scenario_id)
    ranked = rank_assets(_as_scorable(stored_assets))
    by_code = {code: row["id"] for row in stored_assets for code in json.loads(row["external_ids"])}
    rankings.save_ranking(
        connection,
        scenario_id=scenario_id,
        forecast_revision=0,
        ranked=[(by_code[item.external_ids[0]], item) for item in ranked],
        weight_set_version=references.WEIGHT_SET_VERSION,
    )
    log_event(
        "SCENARIO_RANKED",
        scenario_id=scenario_id,
        forecast_revision=0,
        ranked=sum(item.score is not None for item in ranked),
        unscored=sum(item.score is None for item in ranked),
        weight_set_version=references.WEIGHT_SET_VERSION,
        outcome="ranked",
    )
    log_event(
        "SCENARIO_LOADED",
        upload_id=upload_id,
        scenario_id=scenario_id,
        assets=len(result.assets),
        defects_caught=len({finding.defect for finding in result.findings}),
        needs_review=sum(a.match_status == "needs_review" for a in result.assets),
        outcome="ready",
    )
    for finding in result.findings:
        # Named at load, by subject. A flag nobody can trace to a row is a warning nobody
        # can act on (§4, defect 5).
        log_event(
            "SCENARIO_DEFECT_CAUGHT",
            level=logging.WARNING,
            scenario_id=scenario_id,
            defect=finding.defect,
            code=finding.code,
            subject=finding.subject,
        )
    return scenario_id


def refuse(status: int, message: str):
    return errors.error(status, "upload_refused", message)
