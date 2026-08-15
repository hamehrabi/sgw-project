"""The append-only decision record.

**There is no update function here and no delete function here, and that is the design.**
BR-004 is enforced by the database — ADR-004's two triggers — but this module carries no code
that would issue such a statement either, so the rule holds twice: once because the store
refuses, and once because nothing asks.

A correction is a new row.
"""

import json
import sqlite3
import uuid
from datetime import UTC, datetime

RECOMMENDATION = "recommendation"
DECISIONS = ("accept", "change", "reject")


def _append(connection, *, scenario_id, kind, subject_type, subject_id, payload, actor_user_id):
    record_id = f"DR-{uuid.uuid4().hex[:12]}"
    connection.execute(
        "insert into decision_records"
        " (id, scenario_id, occurred_at, actor_user_id, kind, subject_type, subject_id, payload)"
        " values (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            record_id,
            scenario_id,
            datetime.now(UTC).isoformat(),
            actor_user_id,
            kind,
            subject_type,
            subject_id,
            json.dumps(payload),
        ),
    )
    connection.commit()
    return record_id


def append_recommendation(connection, *, scenario_id, forecast_revision, payload) -> str:
    """One row per delivered ranking (FF-005).

    `actor_user_id` is null: the system recommended, and nobody has decided yet. That is the
    only kind of row allowed to be actorless, and the schema enforces it.
    """
    return _append(
        connection,
        scenario_id=scenario_id,
        kind=RECOMMENDATION,
        subject_type="ranking",
        subject_id=f"{scenario_id}:{forecast_revision}",
        payload=payload,
        actor_user_id=None,
    )


def append_decision(connection, *, recommendation, kind, actor_user_id, note, change) -> str:
    return _append(
        connection,
        scenario_id=recommendation["scenario_id"],
        kind=kind,
        subject_type="recommendation",
        subject_id=recommendation["id"],
        payload={"note": note, "change": change},
        actor_user_id=actor_user_id,
    )


def find_recommendation(connection, recommendation_id) -> sqlite3.Row | None:
    return connection.execute(
        "select * from decision_records where id = ? and kind = ?",
        (recommendation_id, RECOMMENDATION),
    ).fetchone()


def existing_decision(connection, recommendation_id) -> sqlite3.Row | None:
    """BR-004 at the API boundary as well as in the store: a second decision is a 409, never
    an overwrite, so a retrying client cannot quietly rewrite an audit row."""
    return connection.execute(
        "select * from decision_records where subject_type = 'recommendation'"
        " and subject_id = ? and kind in (?, ?, ?) order by occurred_at limit 1",
        (recommendation_id, *DECISIONS),
    ).fetchone()


def latest_recommendation(connection, scenario_id, forecast_revision) -> sqlite3.Row | None:
    return connection.execute(
        "select * from decision_records where kind = ? and subject_id = ?"
        " order by occurred_at desc limit 1",
        (RECOMMENDATION, f"{scenario_id}:{forecast_revision}"),
    ).fetchone()


def read_all(connection, scenario_id) -> list[sqlite3.Row]:
    """Ordered by when they happened — the order *is* the history, not a view of it."""
    return connection.execute(
        "select * from decision_records where scenario_id = ? order by occurred_at, id",
        (scenario_id,),
    ).fetchall()
