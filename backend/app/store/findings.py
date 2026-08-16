"""Data-quality findings, persisted (CHG-047).

The seven defect rules run at load and used to leave nothing behind but log lines — so
the quality screen could only exist in the seconds after an upload, while the defects were
still in the data and still shaping the ranking. These rows are written **inside the
scenario's transaction** and read forever; nothing here re-parses anything (§6, FF-003).
"""

import sqlite3
import uuid

# The defect numbers whose finding is a question a person has to answer rather than a fact
# the loader already handled. Defect 1's withheld merges go to the match queue; defects 3
# and 4 each carry one decision the client's design gives a button ("OK, use forecast",
# "OK, exclude"). Everything else is named and collapsed (CHG-047's three-row rule).
NEEDS_DECISION = frozenset({1, 3, 4})


def save(connection: sqlite3.Connection, scenario_id: str, findings, *, now: str) -> None:
    """Write every finding. In the caller's transaction, never its own — a storm must not
    exist half-described (CHG-025's reasoning, applied to quality rather than forecasts)."""
    connection.executemany(
        "insert into data_findings"
        " (id, scenario_id, defect, code, subject, message, affected_file,"
        "  needs_decision, seq)"
        " values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                f"DF-{uuid.uuid4().hex[:12]}",
                scenario_id,
                finding.defect,
                finding.code,
                finding.subject,
                finding.message,
                finding.affected_file,
                1 if finding.defect in NEEDS_DECISION else 0,
                sequence,
            )
            for sequence, finding in enumerate(findings, start=1)
        ],
    )


def for_scenario(connection: sqlite3.Connection, scenario_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        "select * from data_findings where scenario_id = ? order by needs_decision desc, seq",
        (scenario_id,),
    ).fetchall()


def resolve(
    connection: sqlite3.Connection,
    *,
    finding_id: str,
    resolution: str,
    resolved_by: str,
    now: str,
) -> sqlite3.Row | None:
    """Record what the reviewing human chose. Never anonymous, never undated — the schema
    refuses half a record, this just supplies the whole one."""
    connection.execute(
        "update data_findings set resolution = ?, resolved_by = ?, resolved_at = ?"
        " where id = ? and resolution is null",
        (resolution, resolved_by, now, finding_id),
    )
    connection.commit()
    return connection.execute(
        "select * from data_findings where id = ?", (finding_id,)
    ).fetchone()
