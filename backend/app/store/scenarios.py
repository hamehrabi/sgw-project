"""Scenarios, their assets, and the upload jobs that produce them.

The write in `save_loaded_scenario` is one transaction on purpose: §9.1 requires that a parse
failing partway creates no scenario at all, and a partial commit is the one way to produce
exactly the half-loaded storm that rule forbids.
"""

import json
import sqlite3
import uuid
from datetime import UTC, datetime

from app.store import blanks, forecasts

# The two bounds `scenarios_identity_shape` holds, in the one place the service layer reads them.
# **Two hard-coded copies of one number are tied together by nothing**, and when they drift the
# endpoint's specified `400 validation_error` becomes a `500 internal_error` for a value between
# them — which is what happened to `dispatch.NEIGHBOURHOOD_MAX` with the whole suite green through
# it (CHG-023). `test_TASK-009-AC5` reads both numbers back out of the trigger and fails when they
# disagree with these.
NAME_MAX = 200
SOURCE_NOTE_MAX = 500

# Enumerated rather than left to `str.strip()`'s default so the service and the store agree about
# what "blank" means. SQLite's one-argument `trim()` strips spaces only, so the trigger names the
# same characters (CHG-023).
#
# **The six ASCII ones were not enough and this is the fourth column to prove it** (CHG-039).
# `" \t\n\r\v\f"` stood here beside the identical six in `scenarios_identity_shape`, so the two
# layers agreed perfectly and were both wrong the same way: a storm named U+00A0 was answered
# `201` on an untouched tree and stored, and the switcher a person picks storms out by rendered a
# row with no visible label. `ScenarioUploadPanel` used `String.prototype.trim()`, which is wider
# than both — the browser strictest again, so the hole was invisible from the only screen that
# shows it. One alphabet now, in `store/blanks.py`, in the schema as `char(...)`, and in
# `frontend/lib/blank.ts`.
_WHITESPACE = blanks.WHITESPACE


def storm_text(value, limit: int) -> str | None:
    """The value as it may be stored, or `None` if the store would refuse it.

    The legible `400` in front of the trigger, and **not** the rule: a direct insert never passes
    through here, and `scenarios_identity_shape` refuses the same shapes independently. Surrounding
    whitespace is trimmed rather than refused — a padded label is not a wrong label, which is the
    difference between this column and `repair_jobs.location_key`, where two spellings mean two
    crews (CHG-023).
    """
    if not isinstance(value, str):
        return None
    cleaned = value.strip(_WHITESPACE)
    if not cleaned or len(cleaned) > limit:
        return None
    return cleaned


def _now() -> str:
    return datetime.now(UTC).isoformat()


def start_upload(connection, *, uploaded_by, name, source_note, storage_path) -> str:
    upload_id = f"UP-{uuid.uuid4().hex[:12]}"
    connection.execute(
        "insert into scenario_uploads"
        " (id, status, uploaded_by, uploaded_at, name, source_note, storage_path)"
        " values (?, 'parsing', ?, ?, ?, ?, ?)",
        (upload_id, uploaded_by, _now(), name, source_note, storage_path),
    )
    connection.commit()
    return upload_id


def mark_upload_failed(connection, upload_id, *, file: str, reason: str) -> None:
    connection.execute(
        "update scenario_uploads set status = 'failed', failed_file = ?, failed_reason = ?,"
        " finished_at = ? where id = ?",
        (file, reason, _now(), upload_id),
    )
    connection.commit()


def find_upload(connection, upload_id) -> sqlite3.Row | None:
    return connection.execute(
        "select * from scenario_uploads where id = ?", (upload_id,)
    ).fetchone()


def find_by_content_key(connection, content_key) -> sqlite3.Row | None:
    """An identical re-load replaces in place rather than creating a rival ranking (§5).

    **Not the rule** (ADR-002, CHG-031). `unique (content_key)` refuses the second row whether or
    not this lookup ran; what this buys the endpoint is the `200 OK` with the existing id that
    `data-and-integration-spec.md` §3 specifies, instead of a `500` from a constraint.

    It reads `content_key` and not `source_note`. Until migration 013 the digest was stored in the
    column §3 defines as the admin's note, which is why the switcher's third field was hex.
    """
    return connection.execute(
        "select * from scenarios where content_key = ?", (content_key,)
    ).fetchone()


def all_loaded(connection) -> list[sqlite3.Row]:
    """Every storm that is loaded, newest first — `ScenarioSwitcher`'s whole input (CHG-030).

    **Ordered by `seq`, never by a timestamp** (CHG-018, CHG-032). `datetime.now(UTC).isoformat()`
    resolves to about 15.6 ms here and `id` is a random UUID, so two storms loaded in one tick
    come back in coin-flip order under `order by loaded_at desc, id` — and this is the one read in
    the product whose whole purpose is a list somebody scans.

    Two columns are computed rather than joined out: how many assets the storm holds, and whether
    its **current** revision has an order behind it. The second is CHG-027's argument one screen
    over — a switcher that offered a storm as though it were rankable, when nothing has ranked it,
    would put the reader one click from an empty screen that reads as safety.
    """
    return connection.execute(
        "select s.*,"
        " (select count(*) from assets a where a.scenario_id = s.id) as asset_count,"
        " exists (select 1 from risk_scores r where r.scenario_id = s.id"
        "         and r.forecast_revision = s.forecast_revision) as ranked"
        " from scenarios s order by s.seq desc"
    ).fetchall()


def save_loaded_scenario(
    connection, result, *, upload_id, name, source_note, content_key, loaded_by
) -> str:
    """Write the scenario and every asset, or write nothing at all."""
    scenario_id = f"SC-{uuid.uuid4().hex[:12]}"
    try:
        connection.execute("begin")
        connection.execute(
            "insert into scenarios"
            " (id, name, source_note, content_key, loaded_by, loaded_at, forecast_revision,"
            " forecast_issued_at, seq)"
            # `seq` is taken inside the statement, from the table itself, by the single writer
            # (ADR-002). A counter held beside the connection is indistinguishable inside one
            # process and restarts at 1 after a restart, which `unique (seq)` then refuses.
            " values (?, ?, ?, ?, ?, ?, 0, ?,"
            " (select coalesce(max(seq), 0) + 1 from scenarios))",
            (
                scenario_id,
                name,
                source_note,
                content_key,
                loaded_by,
                _now(),
                result.forecast_issued_at,
            ),
        )
        connection.executemany(
            "insert into assets (id, scenario_id, external_ids, type, location, condition,"
            " condition_source, condition_observed_at, condition_estimated, grid_cell_id,"
            " wind_gust_mph, rainfall_in, install_year, flood_zone, name, match_status,"
            " created_at)"
            " values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    f"AS-{uuid.uuid4().hex[:12]}",
                    scenario_id,
                    json.dumps(asset.external_ids),
                    asset.type,
                    json.dumps({"lat": asset.lat, "lon": asset.lon}),
                    asset.condition,
                    asset.condition_source,
                    asset.condition_observed_at,
                    int(asset.condition_estimated),
                    asset.grid_cell_id,
                    asset.wind_gust_mph,
                    asset.rainfall_in,
                    asset.install_year,
                    asset.flood_zone,
                    asset.name,
                    asset.match_status,
                    _now(),
                )
                for asset in result.assets
            ],
        )
        # The whole forecast series, in the same transaction (CHG-025). A storm without its
        # forecasts is a storm REQ-F-004 cannot re-rank, and half a series is worse than none.
        forecasts.save_series(
            connection, scenario_id, result.forecast_revisions, created_at=_now()
        )
        connection.execute(
            "update scenario_uploads set status = 'ready', scenario_id = ?, finished_at = ?"
            " where id = ?",
            (scenario_id, _now(), upload_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return scenario_id


def find(connection, scenario_id) -> sqlite3.Row | None:
    return connection.execute(
        "select * from scenarios where id = ?", (scenario_id,)
    ).fetchone()


def find_upload_for_scenario(connection, scenario_id) -> sqlite3.Row | None:
    return connection.execute(
        "select * from scenario_uploads where scenario_id = ?", (scenario_id,)
    ).fetchone()


def assets_for(connection, scenario_id) -> list[sqlite3.Row]:
    """The joined asset view — the storm **as loaded**, at forecast revision 0.

    Every read is scoped by `scenario_id`. Two storms must never blend into one view.

    The join adds one thing: the `valid_time` of the gust the asset carries, so BR-003's *every
    value shows its source and its age* is true of the forecast too. It is deliberately pinned
    to revision 0 — this view is REQ-F-001's picture of what was loaded, and re-dating it when
    a later forecast is applied would be rewriting revision n, which is the one thing AC-005
    forbids. The ranking is where a revision's own numbers live.
    """
    return connection.execute(
        "select a.*, f.valid_time as forecast_valid_time"
        " from assets a"
        " left join scenario_forecast_cells f"
        "   on f.scenario_id = a.scenario_id and f.grid_cell_id = a.grid_cell_id"
        "   and f.forecast_revision = 0"
        " where a.scenario_id = ? order by a.id",
        (scenario_id,),
    ).fetchall()


def assets_with_forecast(connection, scenario_id, forecast_revision) -> list[sqlite3.Row]:
    """Every asset in the storm, carrying **one revision's** forecast.

    The scoring input for that revision, and the *only* one — there is no fallback to an
    earlier revision's gust. An asset whose cell the revision does not cover arrives with
    `wind_gust_mph` null and becomes UNSCORED with the missing input named, which is the
    honest answer; quietly reusing the last gust would produce a rank that looks comparable
    with the others and is not (ADR-005, FTEST-004).

    Carrying a value forward when the *file* stops mentioning a cell is a different thing and
    happens once at load, where the value keeps the time it was issued (CHG-025).
    """
    return connection.execute(
        "select a.id, a.external_ids, a.name, a.type, a.flood_zone, a.install_year,"
        " a.condition, a.condition_source, a.condition_observed_at, a.condition_estimated,"
        " a.grid_cell_id, f.wind_gust_mph as wind_gust_mph,"
        " f.valid_time as forecast_valid_time"
        " from assets a"
        " left join scenario_forecast_cells f"
        "   on f.scenario_id = a.scenario_id and f.grid_cell_id = a.grid_cell_id"
        "   and f.forecast_revision = ?"
        " where a.scenario_id = ? order by a.id",
        (forecast_revision, scenario_id),
    ).fetchall()


def find_asset(connection, scenario_id, asset_id) -> sqlite3.Row | None:
    """Scoped by scenario on purpose: an asset id from another storm is not an asset here."""
    return connection.execute(
        "select * from assets where scenario_id = ? and id = ?", (scenario_id, asset_id)
    ).fetchone()


def asset_count(connection, scenario_id) -> int:
    return connection.execute(
        "select count(*) from assets where scenario_id = ?", (scenario_id,)
    ).fetchone()[0]
