"""Stored rankings.

Every read is served from stored results, never computed inside the request
(`technical-spec.md` §6). A re-rank is a *write* that produces a new forecast revision; reads
then serve it. That is what makes REQ-NF-001's two limits separable — one bounds the re-rank,
one bounds the read.
"""

import json
import sqlite3
import uuid
from dataclasses import asdict
from datetime import UTC, datetime


def _insert_scores(connection, *, scenario_id, forecast_revision, ranked, weight_set_version, now):
    connection.executemany(
        "insert into risk_scores (id, scenario_id, asset_id, forecast_revision, score, band,"
        " rank, reasons, unscored_reason, weight_set_version, computed_at)"
        " values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                f"RS-{uuid.uuid4().hex[:12]}",
                scenario_id,
                asset_id,
                forecast_revision,
                item.score,
                item.band,
                item.rank,
                json.dumps([asdict(reason) for reason in item.reasons]),
                item.unscored_reason,
                weight_set_version,
                now,
            )
            for asset_id, item in ranked
        ],
    )


def save_ranking(connection, *, scenario_id, forecast_revision, ranked, weight_set_version):
    """Write one whole ranking, or none of it.

    One transaction for the same reason a scenario load is one: a half-written ranking would
    show some assets and silently omit others, which is the failure the whole product is
    built to avoid.
    """
    now = datetime.now(UTC).isoformat()
    try:
        connection.execute("begin")
        _insert_scores(
            connection,
            scenario_id=scenario_id,
            forecast_revision=forecast_revision,
            ranked=ranked,
            weight_set_version=weight_set_version,
            now=now,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return now


def save_revision(
    connection, *, scenario_id, from_revision, to_revision, ranked, weight_set_version
):
    """REQ-F-004's write: the new ranking **and** the scenario's pointer, or neither.

    `reliability-specification.md` says a revision is one transaction, and this is why it has
    to be: a ranking written without the pointer is a revision nobody can reach by default, and
    a pointer moved without a ranking is a storm whose current revision has no list at all —
    the empty screen that must never read as safety.

    **Nothing here rewrites revision `from_revision`.** The insert is refused by
    `unique (scenario_id, asset_id, forecast_revision)` if a ranking for `to_revision` already
    exists, and the store refuses an `UPDATE` to any stored ranking outright (CHG-026). The
    pointer moves by compare-and-swap — `where forecast_revision = ?` — so two operators
    pressing *apply* at the same moment produce one revision and one refusal, decided by the
    database rather than by whichever request read the pointer first.
    """
    now = datetime.now(UTC).isoformat()
    try:
        connection.execute("begin")
        _insert_scores(
            connection,
            scenario_id=scenario_id,
            forecast_revision=to_revision,
            ranked=ranked,
            weight_set_version=weight_set_version,
            now=now,
        )
        moved = connection.execute(
            "update scenarios set forecast_revision = ?"
            " where id = ? and forecast_revision = ?",
            (to_revision, scenario_id, from_revision),
        ).rowcount
        if moved != 1:
            raise RuntimeError(
                f"{scenario_id} was no longer at forecast revision {from_revision}"
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return now


def read_ranking(connection, scenario_id, forecast_revision, *, limit=100, offset=0):
    """Ordered by rank, with unscored assets last — present, and not ranked low.

    The gust comes from **this revision's** forecast, not from the asset row, so the number a
    rank rests on and the number shown beside it are the same number (BR-003). Reading revision
    0 after revision 1 has been applied has to answer with revision 0's forecast, or AC-005's
    *retrievable for comparison* would return the old order beside the new weather.
    """
    return connection.execute(
        "select rs.*, a.external_ids, a.name, a.type, a.condition, a.condition_source,"
        " a.condition_observed_at, a.condition_estimated, a.flood_zone, a.install_year,"
        " f.wind_gust_mph as wind_gust_mph, f.valid_time as forecast_valid_time,"
        " a.grid_cell_id, a.match_status"
        " from risk_scores rs join assets a on a.id = rs.asset_id"
        " left join scenario_forecast_cells f"
        "   on f.scenario_id = rs.scenario_id and f.grid_cell_id = a.grid_cell_id"
        "   and f.forecast_revision = rs.forecast_revision"
        " where rs.scenario_id = ? and rs.forecast_revision = ?"
        " order by rs.rank is null, rs.rank limit ? offset ?",
        (scenario_id, forecast_revision, limit, offset),
    ).fetchall()


def count_for(connection, scenario_id, forecast_revision) -> int:
    return connection.execute(
        "select count(*) from risk_scores where scenario_id = ? and forecast_revision = ?",
        (scenario_id, forecast_revision),
    ).fetchone()[0]


def revision_exists(connection, scenario_id, forecast_revision) -> bool:
    return count_for(connection, scenario_id, forecast_revision) > 0


def computed_at(connection, scenario_id, forecast_revision) -> str | None:
    row: sqlite3.Row | None = connection.execute(
        "select computed_at from risk_scores where scenario_id = ? and forecast_revision = ?"
        " limit 1",
        (scenario_id, forecast_revision),
    ).fetchone()
    return row["computed_at"] if row else None
