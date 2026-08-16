"""The asset match queue (CHG-048) — the withheld merge, kept for the person it was
withheld for.

`loader/matching.py` decides what is withheld; this stores both sides so the review drawer
has something to show, and records what the reviewer chose. Resolving `match` does **not**
rewrite the asset rows — the load is immutable once made (§6) — it records the identity
decision, moves the asset out of `needs_review`, and the record is what a later reload
acts on.
"""

import json
import sqlite3
import uuid


def save(connection: sqlite3.Connection, scenario_id: str, candidates) -> None:
    """Write every withheld pair. In the caller's transaction — a storm must not exist
    with half its review queue."""
    connection.executemany(
        "insert into asset_match_candidates"
        " (id, scenario_id, asset_id, scenario_check, map_record, candidate_record,"
        "  confidence, seq)"
        " values (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                f"AMC-{uuid.uuid4().hex[:12]}",
                scenario_id,
                candidate["asset_id"],
                scenario_id,
                json.dumps(candidate["map_record"]),
                json.dumps(candidate["candidate_record"]),
                candidate["confidence"],
                sequence,
            )
            for sequence, candidate in enumerate(candidates, start=1)
        ],
    )


def queue(connection: sqlite3.Connection, scenario_id: str) -> list[sqlite3.Row]:
    """Every candidate, pending first, in the order the loader found them."""
    return connection.execute(
        "select * from asset_match_candidates where scenario_id = ?"
        " order by case resolution when 'pending' then 0 else 1 end, seq",
        (scenario_id,),
    ).fetchall()


def find(connection: sqlite3.Connection, candidate_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "select * from asset_match_candidates where id = ?", (candidate_id,)
    ).fetchone()


def resolve(
    connection: sqlite3.Connection,
    *,
    candidate: sqlite3.Row,
    resolution: str,
    resolved_by: str,
    now: str,
) -> sqlite3.Row:
    """Record the reviewer's decision, and settle the asset's match status with it.

    One transaction for both writes: a candidate marked resolved while its asset still says
    `needs_review` — or the reverse — is two screens disagreeing about one fact.
    """
    connection.execute(
        "update asset_match_candidates"
        " set resolution = ?, resolved_by = ?, resolved_at = ?"
        " where id = ? and resolution = 'pending'",
        (resolution, resolved_by, now, candidate["id"]),
    )
    # Either answer settles the question a person was asked. `match` records the identity;
    # `not_match` records that the two really are two — and in both cases the asset stops
    # waiting for review, because the review has happened.
    remaining = connection.execute(
        "select count(*) as n from asset_match_candidates"
        " where asset_id = ? and scenario_id = ? and resolution = 'pending' and id <> ?",
        (candidate["asset_id"], candidate["scenario_id"], candidate["id"]),
    ).fetchone()["n"]
    if remaining == 0:
        connection.execute(
            "update assets set match_status = 'matched' where id = ? and scenario_id = ?",
            (candidate["asset_id"], candidate["scenario_id"]),
        )
    connection.commit()
    return connection.execute(
        "select * from asset_match_candidates where id = ?", (candidate["id"],)
    ).fetchone()
