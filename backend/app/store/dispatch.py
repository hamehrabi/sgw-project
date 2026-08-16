"""The shared damage and repair board.

**AC-007 lives in the schema, not here** (ADR-002). `unique (scenario_id, location_key)` on
`repair_jobs` is what makes two jobs for one location impossible; the lookup below is an
optimisation of that constraint, not the enforcement of it. Delete this module's find-first
logic and the database still refuses the second job — which is the property the rule needs,
because the failure it prevents is two crews at one location during a storm.

**And so does the rule that says which two locations are one** (CHG-023, migration 009). That
sentence above was written when 007 shipped and it was only three quarters true: the unique
constraint refused a byte-identical key, while the casefold-and-collapse that *defines* the
same location lived in `location_key()` below and nowhere else. Beside a stored `northgate`
the store accepted `Northgate`, and it accepted `north  gate`, and the board then rendered two
repair jobs for one neighbourhood. `repair_jobs` now carries a check that the stored key is
already normalised, so an un-normalised key cannot be written at all and the constraint has no
second spelling left to miss.

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

# **One bound, and the schema holds the same number twice.** `damage_reports.location` and
# `repair_jobs.location_key` both carry `between 1 and 120`, and this constant is what turns a
# neighbourhood over that length into the specified `400 validation_error` instead of a
# `500 internal_error` from the store. They were three copies with nothing tying them together:
# leaving the schema at 120 and setting this to 5000 broke the endpoint's contract and the whole
# suite stayed green. UTEST-012 now reads the bound out of `sqlite_master` and requires all
# three to agree, so moving one of them alone is red.
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

    **This function is not the rule and must not be read as one** (ADR-002, CHG-023). Migration
    009 puts the same normalisation in `repair_jobs` as a check constraint, so a key that did
    not come through here cannot be stored. What this buys is that the *right* key is computed
    before the insert; what the schema buys is that no other key is storable at all.
    """
    return normalise(neighbourhood).casefold()


def too_long(neighbourhood: str) -> bool:
    """Would the store refuse this neighbourhood for its length?

    Both forms are measured, because they are stored in different columns and casefolding can
    make a string *longer*: `'ß'.casefold()` is `'ss'`, so 120 of them normalise to a display
    name the schema accepts and a key of 240 characters it does not. Checking only the display
    name would turn that into a `500` for the caller, which is the shape this bound was found
    in the first place.
    """
    return (
        len(normalise(neighbourhood)) > NEIGHBOURHOOD_MAX
        or len(location_key(neighbourhood)) > NEIGHBOURHOOD_MAX
    )


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

    **A report belonging to no repair job is counted in its own neighbourhood** (CHG-022). This
    was an INNER join through `repair_jobs`, so a report whose `repair_job_id` is null — a state
    `database-design.md` §3 permits and §1 describes, *"to **at most** one repair job"* — was
    missing from the figure entirely: two open reports in one neighbourhood logged
    `open_reports_in_area=1`, which is REQ-NF-007's figure wrong in the direction that
    under-reports. A left join and the report's own neighbourhood fix it, and the report's own
    neighbourhood is the right fallback because `location` is the only place the fact is stored
    when no job holds it.

    The fallback is `lower(trim(...))` rather than a re-run of `location_key()`: SQL cannot
    collapse a run of spaces, and it does not have to — the only writer normalises before the
    insert, so the stored display name differs from its key by case alone.
    """
    return connection.execute(
        "select count(*) from damage_reports as reports"
        " left join repair_jobs as jobs"
        "   on jobs.id = reports.repair_job_id and jobs.scenario_id = reports.scenario_id"
        " where reports.scenario_id = ?"
        " and coalesce(jobs.location_key,"
        "              lower(trim(json_extract(reports.location, '$.neighbourhood')))) = ?"
        " and reports.status = 'open'",
        (scenario_id, key),
    ).fetchone()[0]
