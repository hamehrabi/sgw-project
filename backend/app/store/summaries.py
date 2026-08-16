"""Stored situation summaries (CHG-040).

The lifecycle's walls are in the schema — a summary cannot be Approved anonymously,
undated, or textless — and this module carries no way to reach `Sent` except through
`approve` then `mark_sent`, in that order, because the API offers no other path either:
two layers holding one rule, the way the dismissal's 409 does.
"""

import json
import sqlite3
import uuid
from datetime import UTC, datetime


def _now() -> str:
    return datetime.now(UTC).isoformat()


def append_draft(
    connection: sqlite3.Connection,
    *,
    scenario_id: str,
    draft_text: str,
    label: str,
    source_figures: dict,
    verification: dict,
    drafted_by: str,
) -> sqlite3.Row:
    """A new Draft row. Appended — regenerating never rewrites what a reader may have seen."""
    summary_id = f"SUM-{uuid.uuid4().hex[:12]}"
    connection.execute(
        "insert into summaries"
        " (id, scenario_id, state, draft_text, label, source_figures, verification,"
        "  drafted_at, drafted_by, seq)"
        " values (?, ?, 'Draft', ?, ?, ?, ?, ?, ?,"
        " (select coalesce(max(seq), 0) + 1 from summaries where scenario_id = ?))",
        (
            summary_id,
            scenario_id,
            draft_text,
            label,
            json.dumps(source_figures),
            json.dumps(verification),
            _now(),
            drafted_by,
            scenario_id,
        ),
    )
    connection.commit()
    return connection.execute("select * from summaries where id = ?", (summary_id,)).fetchone()


def latest(connection: sqlite3.Connection, scenario_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "select * from summaries where scenario_id = ? order by seq desc limit 1",
        (scenario_id,),
    ).fetchone()


def find(connection: sqlite3.Connection, summary_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "select * from summaries where id = ?", (summary_id,)
    ).fetchone()


def approve(
    connection: sqlite3.Connection,
    *,
    summary: sqlite3.Row,
    approved_text: str,
    approved_by: str,
) -> sqlite3.Row:
    """Draft → Approved. The state filter in the WHERE is what makes a retry harmless:
    a second approval of the same row changes nothing rather than re-stamping it."""
    connection.execute(
        "update summaries set state = 'Approved', approved_text = ?, approved_by = ?,"
        " approved_at = ? where id = ? and state = 'Draft'",
        (approved_text, approved_by, _now(), summary["id"]),
    )
    connection.commit()
    return connection.execute("select * from summaries where id = ?", (summary["id"],)).fetchone()


def mark_sent(connection: sqlite3.Connection, *, summary: sqlite3.Row) -> sqlite3.Row:
    """Approved → Sent. Recording that a person distributed it — the platform sends
    nothing anywhere (BR-001) and has no path that could."""
    connection.execute(
        "update summaries set state = 'Sent' where id = ? and state = 'Approved'",
        (summary["id"],),
    )
    connection.commit()
    return connection.execute("select * from summaries where id = ?", (summary["id"],)).fetchone()
