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

from app.store import blanks

RECOMMENDATION = "recommendation"
DECISIONS = ("accept", "change", "reject")
PLACEMENT = "placement"
DISMISS = "dismiss"
DAMAGE_REPORT = "damage_report"

# One bound, and the schema holds the other copy of it. `decision_records_placement_shape`
# (migration 012) refuses a stored crew label outside `between 1 and CREW_LABEL_MAX`, and
# `test_TASK-007-AC4` reads that number out of `sqlite_master` and requires the two to agree —
# because two hard-coded copies of one bound with nothing tying them together is how the
# specified `400 validation_error` became a `500 internal_error` for a neighbourhood one
# character over the limit, with the whole suite green (CHG-023).
CREW_LABEL_MAX = 120
# The same bound the decision note carries, for the same reason and in the same place.
NOTE_MAX = 2000


def _now() -> str:
    """When it happened — which is **not** the order it happened in.

    Named, the way `store/dispatch.py` and `store/scenarios.py` name theirs, so a test can
    freeze it and assert the ordering that has to survive a clock that cannot separate two
    rows. On this platform it cannot: 1,999 of 2,000 consecutive calls return one string.
    """
    return datetime.now(UTC).isoformat()


def _append(
    connection,
    *,
    scenario_id,
    kind,
    subject_type,
    subject_id,
    payload,
    actor_user_id,
    commit=True,
):
    """Append one row.

    `commit=False` is for a caller that is already inside a transaction and whose other
    statement must stand or fall with this one — `store/dispatch.dismiss_report` is the only
    such caller today. It is a parameter rather than a second function because the row written
    must be identical either way, sequence included: two ways to write an audit row are two
    audit-row shapes the day one of them is changed.
    """
    record_id = f"DR-{uuid.uuid4().hex[:12]}"
    connection.execute(
        "insert into decision_records"
        " (id, scenario_id, occurred_at, actor_user_id, kind, subject_type, subject_id, payload,"
        " seq)"
        # `seq` is taken inside the statement, from the table itself, by the single writer
        # (ADR-002). It is the order — `occurred_at` is only when it happened, and this clock
        # cannot tell two rows written in the same 15.6 ms apart (CHG-018).
        " values (?, ?, ?, ?, ?, ?, ?, ?,"
        " (select coalesce(max(seq), 0) + 1 from decision_records))",
        (
            record_id,
            scenario_id,
            _now(),
            actor_user_id,
            kind,
            subject_type,
            subject_id,
            json.dumps(payload),
        ),
    )
    if commit:
        connection.commit()
    return record_id


RANKING = "ranking"


def ranking_subject(scenario_id, forecast_revision) -> str:
    """The identifier one delivered ranking is known by inside the audit trail.

    One function rather than three format strings, because the `recommendation` row and every
    `placement` made against that ranking have to spell it **identically** — that shared value is
    what makes `decision_records_by_subject` answer *what was recommended here, and what did
    people decide about it* in one lookup, and migration 012 refuses a placement whose subject
    disagrees with its own payload.
    """
    return f"{scenario_id}:{forecast_revision}"


def append_recommendation(connection, *, scenario_id, forecast_revision, payload) -> str:
    """One row per delivered ranking (FF-005).

    `actor_user_id` is null: the system recommended, and nobody has decided yet. That is the
    only kind of row allowed to be actorless, and the schema enforces it.
    """
    return _append(
        connection,
        scenario_id=scenario_id,
        kind=RECOMMENDATION,
        subject_type=RANKING,
        subject_id=ranking_subject(scenario_id, forecast_revision),
        payload=payload,
        actor_user_id=None,
    )


def crew_label(value: str) -> str | None:
    """The crew label as the store will hold it, or `None` if the store would refuse it.

    **This is not the enforcement and must not be read as one** (ADR-002).
    `decision_records_placement_shape` refuses the same shapes independently, and a direct insert
    never comes through here. What this buys is the legible `400 validation_error` the contract
    specifies instead of the `500 internal_error` a constraint violation would produce — the exact
    gap that opened between `dispatch.NEIGHBOURHOOD_MAX` and its two copies in the schema, and the
    reason `CREW_LABEL_MAX` is read back out of `sqlite_master` by a test.

    CON-003 permits **a display name and a role** and forbids everything else about a person, so
    this is a label: one line, trimmed, bounded.

    **`str.strip()` was the fourth spelling of "blank" in this repository and it let two through**
    (CHG-039). Python strips `White_Space` and neither U+200B nor U+FEFF is in it, the schema's
    one-argument `trim()` stripped spaces alone, and the browser's `String.prototype.trim()`
    strips U+FEFF but not U+200B — so a crew label of one zero-width space was answered `201` on
    an untouched tree and written into `decision_records`, where BR-004 means it can never be
    corrected. The alphabet is `store/blanks.py`'s, here and in the trigger.
    """
    label = blanks.trim(value)
    if not label or len(label) > CREW_LABEL_MAX:
        return None
    if any(character in label for character in blanks.WHITESPACE if character != " "):
        return None
    return label


def append_placement(
    connection,
    *,
    scenario_id,
    forecast_revision,
    recommendation_id,
    crew,
    asset_ids,
    note,
    actor_user_id,
) -> str:
    """Record that a person decided which crew waits where (REQ-F-005).

    **A record, never an action** (BR-001). Nothing here creates a repair job, assigns anybody,
    or reaches anything outside the platform — the row says what somebody decided while looking
    at one particular ranking, and that is the whole of it.

    There is no 409 here and that is deliberate: a ranking carries any number of placements,
    because several crews wait in several places. A *decision* is one per recommendation because
    a recommendation is accepted, changed or rejected once; a placement is not a verdict on the
    list, it is a plan made against it.
    """
    return _append(
        connection,
        scenario_id=scenario_id,
        kind=PLACEMENT,
        subject_type=RANKING,
        subject_id=ranking_subject(scenario_id, forecast_revision),
        payload={
            "crew": crew,
            "asset_ids": list(asset_ids),
            "forecast_revision": forecast_revision,
            # The delivered ranking this was made against, when one has been delivered. It is
            # `null` for a placement recorded without the list ever having been read — reachable
            # only outside the screens, because `PlacementForm` is not rendered without a ranking
            # (BR-001). The subject above names the ranking either way, which is the traceability
            # that always holds.
            "recommendation_id": recommendation_id,
            "note": note,
        },
        actor_user_id=actor_user_id,
    )


def append_dismissal(
    connection,
    *,
    scenario_id,
    report_id,
    repair_job_id,
    neighbourhood,
    reason,
    actor_user_id,
) -> str:
    """Record that a person cleared a false alarm (REQ-F-008, AC-008).

    **A record, never an action** (BR-001). Dismissing an alarm cancels no work, closes no repair
    job and reaches nothing outside the platform. The job the report was filed against stays on
    the board reading *explained* rather than *empty* (CHG-020) — whether work leaves a shared
    board is not this row's decision to take.

    **Written without committing, inside the caller's transaction.** The report's own columns and
    this row are one fact: a dismissal that is not recorded, and a record of a dismissal that did
    not happen, are both worse than a refusal.

    **The payload repeats three facts the report already holds, and that is deliberate.**
    `decision_records` does not cascade with its scenario (migration 006) because an audit row
    must outlive the thing it describes — a row that only pointed at the report would say nothing
    at all once the storm was deleted. `decision_records_dismiss_shape` (migration 014) is what
    stops the two copies ever disagreeing: they must be equal when this row is written, and
    neither can move afterwards.

    Nothing finer than a neighbourhood, because nothing finer exists to copy (CON-003).
    """
    return _append(
        connection,
        scenario_id=scenario_id,
        kind=DISMISS,
        subject_type=DAMAGE_REPORT,
        subject_id=report_id,
        payload={
            "reason": reason,
            "neighbourhood": neighbourhood,
            "repair_job_id": repair_job_id,
        },
        actor_user_id=actor_user_id,
        commit=False,
    )


def find_record(connection, record_id) -> sqlite3.Row | None:
    return connection.execute(
        "select * from decision_records where id = ?", (record_id,)
    ).fetchone()


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
        " and subject_id = ? and kind in (?, ?, ?) order by seq limit 1",
        (recommendation_id, *DECISIONS),
    ).fetchone()


def latest_recommendation(connection, scenario_id, forecast_revision) -> sqlite3.Row | None:
    """The last one written, by the sequence rather than by the clock.

    `order by occurred_at desc limit 1` could return the wrong row outright: two recommendations
    written inside one 15.6 ms tick carry the same timestamp, and `limit 1` then picks whichever
    the planner reached first (CHG-018).
    """
    return connection.execute(
        "select * from decision_records where kind = ? and subject_id = ?"
        " order by seq desc limit 1",
        (RECOMMENDATION, ranking_subject(scenario_id, forecast_revision)),
    ).fetchone()


def read_all(connection, scenario_id) -> list[sqlite3.Row]:
    """Ordered by when they happened — the order *is* the history, not a view of it.

    That claim is only true of a key that is total. `occurred_at` is not one: it comes from a
    clock that resolves to about 15.6 ms, and the `id` beside it was a random UUID, so two rows
    appended in one tick came back in coin-flip order. It had been that way since migration 006
    shipped, and ITEST-002 failed on roughly a third of clean runs because of it. `seq` is the
    order (CHG-018); rows written before migration 008 carry `seq = 0` and keep the tie they
    already had, which `occurred_at, id` at least makes repeatable.
    """
    return connection.execute(
        "select * from decision_records where scenario_id = ? order by seq, occurred_at, id",
        (scenario_id,),
    ).fetchall()
