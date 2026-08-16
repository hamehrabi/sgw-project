"""The shared damage and repair board.

**AC-007 lives in the schema, not here** (ADR-002). `unique (scenario_id, location_key)` on
`repair_jobs` is what makes two jobs for one location impossible; the lookup below is an
optimisation of that constraint, not the enforcement of it. Delete this module's find-first
logic and the database still refuses the second job — which is the property the rule needs,
because the failure it prevents is two crews at one location during a storm.

**So does the storm scope** (CHG-019, migration 008). A report may only name an asset and a
repair job belonging to the storm it is filed against, and the composite foreign keys over
`(id, scenario_id)` are what refuse the rest. Until 008 that rule lived in an `if` in
`api/dispatch.py`, which is the one place ADR-002 says a rule must never live.

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
#
# **Ordered by `seq`, never by a timestamp** (CHG-018). `datetime.now(UTC).isoformat()` resolves
# to about 15.6 ms here, so `order by created_at, id` put two rows written inside one tick in
# whichever order their random UUIDs happened to fall. A total order needs a key that is total.
JOBS_SQL = "select * from repair_jobs where scenario_id = ? order by seq"

# **Every report, whatever its status**, because two different questions are being asked of this
# result and only one of them wants the working list. The board shows the reports still open;
# the job's neighbourhood comes from the first report ever filed for it, which is the only
# stored form of that fact once a false alarm has been dismissed (CHG-020). Splitting the two in
# `api/views.py` keeps the board at two statements whatever the report count (PTEST-002).
REPORTS_SQL = "select * from damage_reports where scenario_id = ? order by seq"

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
                " (id, scenario_id, status, location_key, created_at, updated_at, seq)"
                # The sequence is taken inside the same statement, and this module is the
                # single writer (ADR-002). `unique (seq)` is what makes two rows claiming one
                # place in the history a refusal rather than a coin flip.
                " values (?, ?, 'pending', ?, ?, ?,"
                " (select coalesce(max(seq), 0) + 1 from repair_jobs))",
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
            " status, seq)"
            " values (?, ?, ?, ?, ?, ?, ?, ?,"
            " (select coalesce(max(seq), 0) + 1 from damage_reports))",
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

    **Three figures could be computed here and only one of them is legal.** Coarser — every
    open report in the storm — says nothing about the area. Finer — reports per asset — is
    precisely what REQ-NF-007 exists to forbid, because an asset is a place. This one is the
    neighbourhood: an aggregate for the area, never a line identifying the one place a report
    came from, which is the case that matters most because a sparse area is where a single
    report comes closest to naming a household.

    Open means `status = 'open'`. A report marked `duplicate` is a second call about damage
    already counted, and counting it twice would overstate the area's open work (CHG-021).
    """
    return connection.execute(
        "select count(*) from damage_reports as reports"
        " join repair_jobs as jobs on jobs.id = reports.repair_job_id"
        " where reports.scenario_id = ? and jobs.location_key = ?"
        " and reports.status = 'open'",
        (scenario_id, key),
    ).fetchone()[0]
