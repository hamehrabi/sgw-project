"""The shared damage and repair board.

**AC-007 lives in the schema, not here** (ADR-002). `unique (scenario_id, location_key)` on
`repair_jobs` is what makes two jobs for one location impossible; the lookup below is an
optimisation of that constraint, not the enforcement of it. Delete this module's find-first
logic and the database still refuses the second job — which is the property the rule needs,
because the failure it prevents is two crews at one location during a storm.

**Nothing here dispatches anything** (BR-001, BR-005). Creating a job records that work exists.
No crew is assigned, no message leaves the platform, and `assigned_to` is a note about what
people decided, never an instruction the platform issued.

The two board queries are module constants because PTEST-002 asserts their query plans: a test
that explains its own copy of the SQL proves nothing about the SQL that runs.
"""

import json
import sqlite3
import uuid
from datetime import UTC, datetime

# Every read scoped by `scenario_id`. Two storms blended into one board would look entirely
# plausible and send a crew to a neighbourhood that is not in this storm at all.
JOBS_SQL = "select * from repair_jobs where scenario_id = ? order by created_at, id"

# A dismissed false alarm leaves the working list rather than being deleted — REQ-F-008 is one
# action, not an erasure, and TASK-008 is what writes that status. Nothing sets it yet.
REPORTS_SQL = (
    "select * from damage_reports where scenario_id = ? and status <> 'dismissed'"
    " order by reported_at, id"
)

OPEN = "open"
NEIGHBOURHOOD_MAX = 120


def _now() -> str:
    return datetime.now(UTC).isoformat()


def normalise(neighbourhood: str) -> str:
    """The name as it will be shown: trimmed, with runs of whitespace collapsed."""
    return " ".join((neighbourhood or "").split())


def location_key(neighbourhood: str) -> str:
    """The grouping key for AC-007.

    Case- and spacing-insensitive, because a capital letter is not a second location and the
    cost of treating it as one is a second crew.
    """
    return normalise(neighbourhood).casefold()


def find_report(connection, report_id) -> sqlite3.Row | None:
    return connection.execute(
        "select * from damage_reports where id = ?", (report_id,)
    ).fetchone()


def file_report(connection, *, scenario_id, neighbourhood, asset_id, reported_by) -> sqlite3.Row:
    """Record one damage report and attach it to the job for its location.

    One transaction: a report written without its job, or a job written without the report
    that caused it, are both worse than a refusal — the first is work nobody can see on the
    board, the second is a job nobody can explain.
    """
    key = location_key(neighbourhood)
    display = normalise(neighbourhood)
    now = _now()
    report_id = f"DR-{uuid.uuid4().hex[:12]}"

    try:
        connection.execute("begin")
        job = connection.execute(
            "select * from repair_jobs where scenario_id = ? and location_key = ?",
            (scenario_id, key),
        ).fetchone()

        if job is None:
            job_id = f"RJ-{uuid.uuid4().hex[:12]}"
            connection.execute(
                "insert into repair_jobs"
                " (id, scenario_id, status, location_key, created_at, updated_at)"
                " values (?, ?, 'pending', ?, ?, ?)",
                (job_id, scenario_id, key, now, now),
            )
        else:
            job_id = job["id"]
            connection.execute(
                "update repair_jobs set updated_at = ? where id = ?", (now, job_id)
            )

        connection.execute(
            "insert into damage_reports"
            " (id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by,"
            " status)"
            " values (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                report_id,
                scenario_id,
                asset_id,
                job_id,
                # Neighbourhood and nothing else. The store refuses any other shape (CON-003),
                # so this is the only object that can be built here.
                json.dumps({"neighbourhood": display}),
                now,
                reported_by,
                OPEN,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return find_report(connection, report_id)


def board(connection, scenario_id) -> tuple[list[sqlite3.Row], list[sqlite3.Row]]:
    """Two queries, whatever the volume — the jobs and their reports.

    A query per job is how `performance-tests.md`'s first risk row ("does the code query the
    database inside a loop?") reaches production: it passes every functional test.
    """
    jobs = connection.execute(JOBS_SQL, (scenario_id,)).fetchall()
    reports = connection.execute(REPORTS_SQL, (scenario_id,)).fetchall()
    return jobs, reports


def open_reports_in_area(connection, scenario_id, key) -> int:
    """The neighbourhood-level figure that reaches the log (REQ-NF-007).

    An aggregate for the area, never a line identifying the one place a report came from —
    which is the case that matters most, because a sparse area is where a single report is
    closest to naming a household.
    """
    return connection.execute(
        "select count(*) from damage_reports as reports"
        " join repair_jobs as jobs on jobs.id = reports.repair_job_id"
        " where reports.scenario_id = ? and jobs.location_key = ?"
        " and reports.status <> 'dismissed'",
        (scenario_id, key),
    ).fetchone()[0]
