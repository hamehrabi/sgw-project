"""Service areas and the crew staging plan (CHG-049).

A staging plan is a **record and never an action** (BR-001): counts a person chose while
looking at one revision's ranking. Appended, never rewritten — the latest row is the plan,
and the earlier rows are what it was before, which is the same property the decision
record keeps for the same reason.
"""

import json
import sqlite3
import uuid
from datetime import UTC, datetime


def _now() -> str:
    return datetime.now(UTC).isoformat()


def save_areas(connection: sqlite3.Connection, scenario_id: str, areas: dict, names=None) -> None:
    """Write the manifest's service areas. In the caller's transaction, at load."""
    names = names or {}
    connection.executemany(
        "insert into scenario_service_areas"
        " (scenario_id, service_area_id, name, customer_count) values (?, ?, ?, ?)",
        [
            (scenario_id, area_id, names.get(area_id), population)
            for area_id, population in sorted(areas.items())
        ],
    )


def areas_for(connection: sqlite3.Connection, scenario_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        "select * from scenario_service_areas where scenario_id = ? order by service_area_id",
        (scenario_id,),
    ).fetchall()


def record_plan(
    connection: sqlite3.Connection,
    *,
    scenario_id: str,
    forecast_revision: int,
    depots: list[dict],
    actor_user_id: str,
) -> sqlite3.Row:
    plan_id = f"STG-{uuid.uuid4().hex[:12]}"
    connection.execute(
        "insert into crew_staging"
        " (id, scenario_id, forecast_revision, depots, actor_user_id, created_at, seq)"
        " values (?, ?, ?, ?, ?, ?,"
        " (select coalesce(max(seq), 0) + 1 from crew_staging where scenario_id = ?))",
        (
            plan_id,
            scenario_id,
            forecast_revision,
            json.dumps(depots),
            actor_user_id,
            _now(),
            scenario_id,
        ),
    )
    connection.commit()
    return connection.execute("select * from crew_staging where id = ?", (plan_id,)).fetchone()


def latest_plan(connection: sqlite3.Connection, scenario_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "select * from crew_staging where scenario_id = ? order by seq desc limit 1",
        (scenario_id,),
    ).fetchone()
