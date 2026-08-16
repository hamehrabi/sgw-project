"""Stored per-asset summaries (CHG-059).

One row per (scenario, asset, forecast revision) — the schema's `unique`, not this
module's discipline. Reading one back is a select; nothing here can trigger a model.
"""

import json
import sqlite3
import uuid
from datetime import UTC, datetime


def save(
    connection: sqlite3.Connection,
    *,
    scenario_id: str,
    asset_id: str,
    forecast_revision: int,
    text: str,
    label: str,
    source_figures: dict,
    verification: dict,
    created_by: str,
) -> sqlite3.Row:
    summary_id = f"ASUM-{uuid.uuid4().hex[:12]}"
    connection.execute(
        "insert into asset_summaries"
        " (id, scenario_id, asset_id, forecast_revision, text, label, source_figures,"
        "  verification, created_at, created_by)"
        " values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            summary_id,
            scenario_id,
            asset_id,
            forecast_revision,
            text,
            label,
            json.dumps(source_figures),
            json.dumps(verification),
            datetime.now(UTC).isoformat(),
            created_by,
        ),
    )
    connection.commit()
    return connection.execute(
        "select * from asset_summaries where id = ?", (summary_id,)
    ).fetchone()


def find(
    connection: sqlite3.Connection, scenario_id: str, asset_id: str, forecast_revision: int
) -> sqlite3.Row | None:
    return connection.execute(
        "select * from asset_summaries"
        " where scenario_id = ? and asset_id = ? and forecast_revision = ?",
        (scenario_id, asset_id, forecast_revision),
    ).fetchone()


def for_scenario(connection: sqlite3.Connection, scenario_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        "select * from asset_summaries where scenario_id = ?"
        " order by forecast_revision, asset_id",
        (scenario_id,),
    ).fetchall()
