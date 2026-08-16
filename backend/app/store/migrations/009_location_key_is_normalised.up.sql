-- 009 — the grouping rule that defines "the same location", in the schema (TASK-005, third review)
--
--   CHG-023 `repair_jobs.location_key` is normalised BY THE STORE, and one bound governs it.
--     Migration 007 wrote `unique (scenario_id, location_key)` and called it AC-007. It is only
--     half of it. That constraint refuses a BYTE-IDENTICAL key; the rule that makes two
--     spellings one location — casefold, then collapse whitespace — lived entirely in
--     `store/dispatch.py:location_key()`. Issued directly against the database beside a stored
--     `northgate`, the store ACCEPTED `Northgate`, and it accepted `north  gate`, and the board
--     then rendered two repair jobs for one neighbourhood: two crews at one place during a
--     storm, which is the single failure AC-007 exists to prevent. Deleting `.casefold()` from
--     the service turned exactly one test red, and that test files both reports THROUGH THE
--     ENDPOINT — so no store-level assertion existed at all. "Never implement a check in the
--     service layer that the store could refuse" (ADR-002). The fix is a CHECK that the stored
--     key is ALREADY normalised — lower case, no leading or trailing whitespace, no run of two
--     spaces, and no tab, newline or other whitespace character at all — so the only key this
--     table will hold is the one `location_key()` produces. `unique (scenario_id, location_key)`
--     then means what migration 007 said it meant, because there is no second spelling left for
--     it to miss, and the service function becomes an optimisation of the constraint rather
--     than the rule, which is what its docstring has claimed since 007 and what was not true
--     until this file.
--
--     **`unique (scenario_id, location_key collate nocase)` was the review's named remedy and
--     is deliberately NOT used, which is worth stating plainly rather than leaving to be
--     noticed.** It is unreachable beside the check: `nocase` folds ASCII `A-Z` and nothing
--     else, and every string the check admits is already ASCII-lower-cased, so no two keys this
--     table can hold collide under `nocase` without colliding under `binary` first. Adding it
--     would be a fifth instance of the shape this repository keeps finding — FF-002 (CHG-010),
--     FF-003 (CHG-013), TASK-002's two defect rules, and TASK-005's own reasons-only check —
--     a clause that cannot fail, which governs nothing and reads as though it does. It is also
--     not sufficient on its own, which is the other half of why the check is the right tool:
--     with only the collation, a direct insert of `Northgate` into an EMPTY table is accepted,
--     the store then holds an un-normalised key, and the next report filed for that
--     neighbourhood looks it up by `binary`, misses, tries to create a second job, and is
--     refused by the index — a 500 for the dispatcher instead of a joined job.
--
--     **A known limit, recorded rather than implied away.** SQLite's `lower()` is ASCII-only,
--     so `ÉCOLE` is not folded to `école` by the check, and `nocase` would not fold it either.
--     Python's `str.casefold()` is not ASCII-only, so every key this application writes is
--     still fully folded; what the schema cannot independently refuse is a DIRECT insert of a
--     non-ASCII capital. That is far narrower than the hole being closed, it needs an `ICU`
--     build to fix, and adding a build dependency to a prototype is a larger decision than
--     this migration.
--
--     **One bound, named once.** `length(location_key) between 1 and 120` is the same bound
--     `damage_reports.location` already carries and the same one `dispatch.NEIGHBOURHOOD_MAX`
--     names. It was three hard-coded copies with nothing tying them together — schema at 120
--     beside a service constant at 5000 turns the specified `400 validation_error` into a
--     `500 internal_error`, and the suite stayed green through exactly that mutation.
--     UTEST-012 now reads the bound out of `sqlite_master` and requires all three to agree.
--
--     **And the same normalisation on `damage_reports.location`, for two reasons.** The first
--     was found while writing the test for the clause above: `length(trim(...)) between 1 and
--     120` was meant to refuse a neighbourhood that is not a place, and SQLite's `trim()`
--     strips **spaces only** — so `"\t\n"` was stored as a location while `"   "` was refused,
--     which is the same value wearing a different whitespace character. The second is CHG-022:
--     an open report belonging to no repair job is now counted in its own neighbourhood, and
--     the only stored form of that neighbourhood is this display string, so it has to be the
--     same fact as the key or the figure quietly splits in two. Requiring the display name to
--     be trimmed and singly-spaced makes `lower(trim(...))` exactly the key, rather than
--     approximately it.
--
-- SQLite cannot add a CHECK constraint to an existing table, so
-- `repair_jobs` is rebuilt and copied — the same procedure migration 008 used for
-- `damage_reports`, with one addition it did not need: `damage_reports` holds a composite
-- foreign key into this table with `on delete cascade`, and `drop table` performs an implicit
-- delete. With foreign keys enabled that would silently destroy every damage report in the
-- database. They are turned off for the rebuild and turned back on immediately afterwards,
-- which is the procedure the SQLite documentation prescribes for exactly this case.
--
-- BOTH decision_records TRIGGERS ARE RE-ASSERTED AT THE END OF THIS FILE (ADR-004, BR-004).
-- Neither is dropped, disabled or recreated here.

pragma foreign_keys = off;

begin;

create table repair_jobs_new (
    id            text primary key,
    scenario_id   text not null references scenarios (id) on delete cascade,
    status        text not null
                  check (status in ('pending', 'in_progress', 'done')),
    priority_rank integer,
                                              -- stays null in version one. Criticality badges
                                              --   the dispatch queue and risk orders the
                                              --   planning list; they are different lists, and
                                              --   nothing here may be ordered by a score
    assigned_to   text,
                                              -- a note that people recorded, never an
                                              --   instruction the platform issued (BR-001)
    location_key  text not null,              -- CHG-017(a): the normalised neighbourhood this
                                              --   job answers. CHG-023: and the store is what
                                              --   makes "normalised" true of it
    created_at    text not null,
    updated_at    text not null,
    seq           integer not null,           -- CHG-018: the order work arrived in, and the
                                              --   only key the board may be ordered by

    check (location_key = lower(location_key)
           and length(location_key) between 1 and 120
           and location_key = trim(location_key)
           and location_key not like '%  %'
           and instr(location_key, char(9)) = 0
           and instr(location_key, char(10)) = 0
           and instr(location_key, char(11)) = 0
           and instr(location_key, char(12)) = 0
           and instr(location_key, char(13)) = 0),
                                              -- CHG-023: a key that is not already normalised
                                              --   is refused, so `north  gate` can never sit
                                              --   beside `north gate` as a second job

    unique (scenario_id, location_key)
                                              -- AC-007, in the schema, and now it means what
                                              --   007 said it meant: the check above leaves no
                                              --   second spelling for this to miss, so two jobs
                                              --   for one location cannot exist and no crew can
                                              --   be sent where another already is
);

insert into repair_jobs_new
    (id, scenario_id, status, priority_rank, assigned_to, location_key, created_at, updated_at,
     seq)
select id, scenario_id, status, priority_rank, assigned_to, location_key, created_at, updated_at,
       seq
from repair_jobs;

drop table repair_jobs;
alter table repair_jobs_new rename to repair_jobs;

-- Every index the dropped table carried, re-created by name. `repair_jobs_scenario_status` is
-- named by PTEST-002's query-plan assertion; the parent key stays ordered `(id, scenario_id)`
-- so it cannot serve `where scenario_id = ?` and make that assertion unfailable again (008 §2).
create index repair_jobs_scenario_status on repair_jobs (scenario_id, status);
create unique index repair_jobs_seq on repair_jobs (seq);
create unique index repair_jobs_id_scenario on repair_jobs (id, scenario_id);

-- `damage_reports`, rebuilt for the second half of CHG-023: the same normalisation on the
-- neighbourhood the board displays. Every column, constraint and foreign key is migration
-- 008's, unchanged, except the location check.
create table damage_reports_new (
    id               text primary key,
    scenario_id      text not null references scenarios (id) on delete cascade,
    asset_id         text,
                                              -- optional on purpose: §4 says a report naming no
                                              --   matching asset is still a report, and is
                                              --   never dropped for being unattributable
    repair_job_id    text,
                                              -- AC-007: one nullable foreign key IS the rule. A
                                              --   report cannot belong to two jobs, so no crew
                                              --   is sent twice. Nullable, so a report may
                                              --   belong to none — which is a state the board
                                              --   has to render (CHG-022)
    location         text not null,           -- json
    reported_at      text not null,
    reported_by      text not null,
    status           text not null
                     check (status in ('open', 'duplicate', 'dismissed')),
    dismissed_by     text references users (id),
    dismissed_reason text,
    seq              integer not null,        -- CHG-018

    check (status <> 'dismissed'
           or (dismissed_by is not null and dismissed_reason is not null)),
                                              -- REQ-F-008: dismissal stays one action, but never
                                              --   becomes anonymous. TASK-008 writes it; the
                                              --   constraint is §3's and belongs with the table

    check (json_valid(location)
           and json_type(location, '$.neighbourhood') = 'text'
           and length(json_extract(location, '$.neighbourhood')) between 1 and 120
           and json_extract(location, '$.neighbourhood')
               = trim(json_extract(location, '$.neighbourhood'))
           and json_extract(location, '$.neighbourhood') not like '%  %'
           and instr(json_extract(location, '$.neighbourhood'), char(9)) = 0
           and instr(json_extract(location, '$.neighbourhood'), char(10)) = 0
           and instr(json_extract(location, '$.neighbourhood'), char(11)) = 0
           and instr(json_extract(location, '$.neighbourhood'), char(12)) = 0
           and instr(json_extract(location, '$.neighbourhood'), char(13)) = 0
           and json(location) = json_object('neighbourhood',
                                            json_extract(location, '$.neighbourhood'))),
                                              -- CON-003 / REQ-NF-007, CHG-017(b) and CHG-023.
                                              --   The equality is still the load-bearing half:
                                              --   any extra key — address, meter_id, lat, lon,
                                              --   household — makes the rebuilt object differ
                                              --   and the row is refused. What is new is that
                                              --   the neighbourhood must be a place: `""`,
                                              --   `"   "` and `"\t\n"` are all refused now,
                                              --   where `trim()` alone caught only the second

    foreign key (asset_id, scenario_id)
        references assets (id, scenario_id) on delete cascade,
                                              -- CHG-019: the asset must be in THIS storm
    foreign key (repair_job_id, scenario_id)
        references repair_jobs (id, scenario_id) on delete cascade
                                              -- CHG-019: and so must the job. The `on delete
                                              --   cascade` on the asset key above contradicts
                                              --   §4 the day anything deletes a single asset —
                                              --   nothing does, and it is raised as CHG-024
                                              --   rather than changed inside this remediation
);

insert into damage_reports_new
    (id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
     dismissed_by, dismissed_reason, seq)
select id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
       dismissed_by, dismissed_reason, seq
from damage_reports;

drop table damage_reports;
alter table damage_reports_new rename to damage_reports;

create index damage_reports_scenario_status_job
    on damage_reports (scenario_id, status, repair_job_id);
                                              -- the index PTEST-002 names
create unique index damage_reports_seq on damage_reports (seq);

commit;

pragma foreign_keys = on;

-- BR-004, re-asserted. Present after this migration or the guarantee is gone (ADR-004).
create trigger if not exists decision_records_no_update
before update on decision_records
begin
    select raise(abort, 'decision_records is append-only (BR-004, ADR-004)');
end;

create trigger if not exists decision_records_no_delete
before delete on decision_records
begin
    select raise(abort, 'decision_records is append-only (BR-004, ADR-004)');
end;
