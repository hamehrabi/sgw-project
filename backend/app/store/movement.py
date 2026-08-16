"""Stored rank movement (CHG-044).

Written once per revision, read forever, never rewritten — the same read stability every
other screen keeps (§6, FF-003). The delta is a diff of two **stored, delivered** rankings
— revision n against n−1 — assembled by the apply-forecast endpoint from `risk_scores`
rows; nothing is re-scored to produce it and nothing here computes anything.
"""

import sqlite3
from datetime import UTC, datetime


def _now() -> str:
    return datetime.now(UTC).isoformat()


def save(
    connection: sqlite3.Connection,
    *,
    scenario_id: str,
    forecast_revision: int,
    rows: list[dict],
    previous_label: str,
) -> None:
    """Write one revision's movement. In the caller's transaction where one is open."""
    now = _now()
    connection.executemany(
        "insert into rank_movement"
        " (scenario_id, forecast_revision, asset_id, previous_rank, current_rank, band,"
        "  reason_factor, reason_detail, previous_label, computed_at)"
        " values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                scenario_id,
                forecast_revision,
                row["asset_id"],
                row["previous_rank"],
                row["current_rank"],
                row["band"],
                row["reason_factor"],
                row["reason_detail"],
                previous_label,
                now,
            )
            for row in rows
        ],
    )


def for_revision(
    connection: sqlite3.Connection, scenario_id: str, forecast_revision: int
) -> list[sqlite3.Row]:
    """Risers first, largest move first — the shape the strip reads."""
    return connection.execute(
        "select * from rank_movement"
        " where scenario_id = ? and forecast_revision = ?"
        "   and previous_rank is not null and current_rank is not null"
        "   and current_rank < previous_rank"
        " order by (previous_rank - current_rank) desc, current_rank",
        (scenario_id, forecast_revision),
    ).fetchall()
