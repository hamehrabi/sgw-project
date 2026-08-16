"""A scenario's forecast series — what REQ-F-004's re-rank is computed against.

**Written once, at load, and never rewritten.** A forecast revision is a fact about the
prepared file, not a running total: the whole series is inserted inside the same transaction as
the scenario and its assets, so a storm never exists without its forecasts and half a series is
not a state this store can hold (CHG-025).

Nothing here scores, ranks or bands. It answers three questions: which revisions this storm
carries, which one comes after the current one, and what the grid looked like at one of them.
"""

import sqlite3


def save_series(connection, scenario_id: str, series, *, created_at: str) -> None:
    """Write the whole series. **Inside the caller's transaction**, never its own.

    `save_loaded_scenario` opens one transaction for the scenario, its assets and this, for the
    same reason §9.1 gives for the other two: a scenario whose forecasts are half written is a
    storm that re-ranks into a ranking nobody's data supports.
    """
    connection.executemany(
        "insert into scenario_forecast_revisions"
        " (scenario_id, forecast_revision, valid_time, created_at) values (?, ?, ?, ?)",
        [
            (scenario_id, revision.forecast_revision, revision.valid_time, created_at)
            for revision in series
        ],
    )
    connection.executemany(
        "insert into scenario_forecast_cells"
        " (scenario_id, forecast_revision, grid_cell_id, valid_time, wind_gust_mph, rainfall_in)"
        " values (?, ?, ?, ?, ?, ?)",
        [
            (
                scenario_id,
                revision.forecast_revision,
                cell.grid_cell_id,
                cell.valid_time,
                cell.wind_gust_mph,
                cell.rainfall_in,
            )
            for revision in series
            for cell in revision.cells
        ],
    )


def revisions(connection, scenario_id: str) -> list[sqlite3.Row]:
    """Every forecast revision this storm carries, in order."""
    return connection.execute(
        "select forecast_revision, valid_time from scenario_forecast_revisions"
        " where scenario_id = ? order by forecast_revision",
        (scenario_id,),
    ).fetchall()


def next_after(connection, scenario_id: str, forecast_revision: int) -> sqlite3.Row | None:
    """The scenario's *next* forecast change, or `None` when it carries no more.

    `> ?` rather than `= ? + 1`: the answer stays right if a series ever arrives with a gap in
    it, and "the next one" is what `api-specification.md` asks for either way.
    """
    return connection.execute(
        "select forecast_revision, valid_time from scenario_forecast_revisions"
        " where scenario_id = ? and forecast_revision > ?"
        " order by forecast_revision limit 1",
        (scenario_id, forecast_revision),
    ).fetchone()
