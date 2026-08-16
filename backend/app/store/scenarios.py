"""Scenarios, their assets, and the upload jobs that produce them.

The write in `save_loaded_scenario` is one transaction on purpose: §9.1 requires that a parse
failing partway creates no scenario at all, and a partial commit is the one way to produce
exactly the half-loaded storm that rule forbids.
"""

import json
import sqlite3
import uuid
from datetime import UTC, datetime


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
    """An identical re-load replaces in place rather than creating a rival ranking (§5)."""
    return connection.execute(
        "select * from scenarios where source_note = ?", (content_key,)
    ).fetchone()


def save_loaded_scenario(connection, result, *, upload_id, name, source_note, loaded_by) -> str:
    """Write the scenario and every asset, or write nothing at all."""
    scenario_id = f"SC-{uuid.uuid4().hex[:12]}"
    try:
        connection.execute("begin")
        connection.execute(
            "insert into scenarios"
            " (id, name, source_note, loaded_by, loaded_at, forecast_revision,"
            " forecast_issued_at)"
            " values (?, ?, ?, ?, ?, 0, ?)",
            (scenario_id, name, source_note, loaded_by, _now(), result.forecast_issued_at),
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
    """Every read is scoped by `scenario_id`. Two storms must never blend into one view."""
    return connection.execute(
        "select * from assets where scenario_id = ? order by id", (scenario_id,)
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
