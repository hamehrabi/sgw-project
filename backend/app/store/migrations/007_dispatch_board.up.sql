-- 007 — repair_jobs and damage_reports, the shared dispatch board (TASK-005)
--
-- `database-design.md` §3 defines both tables. Two things it does not define are added here
-- and raised as change entries rather than assumed silently:
--
--   CHG-017(a) `repair_jobs.location_key` + `unique (scenario_id, location_key)`.
--     AC-007 says two reports at one location resolve to ONE job, never two. §2 calls
--     `damage_reports.repair_job_id` "the single nullable link that makes AC-007 structural",
--     and it is — a report cannot belong to two jobs. But nothing in §3 stops two JOBS existing
--     for one location, and without this constraint that half of AC-007 could only live in
--     service code, which ADR-002 forbids: "never implement a check in the service layer that
--     the store could refuse". The unique index is the rule; the lookup in `store/dispatch.py`
--     is only an optimisation of it.
--
--   CHG-017(b) the shape of `damage_reports.location`.
--     §3 says `location: json, required` and fixes no resolution. CON-003 forbids storing any
--     premise-level record, so the finest location this platform may hold is a neighbourhood —
--     and the check below makes the column physically unable to hold anything else. An address,
--     a meter id, a coordinate or a household field is refused by the database, not filtered on
--     the way out. That is what makes REQ-NF-007 ("damage locations aggregated to neighbourhood
--     level in every log and export") structural: there is nothing finer stored to leak, so no
--     log line and no export has to remember to aggregate.
--
-- BOTH decision_records TRIGGERS ARE RE-ASSERTED AT THE END OF THIS FILE. They are BR-004's
-- only enforcement (ADR-004, migration 006). `create trigger if not exists` re-asserts without
-- dropping: dropping either one inside an unrelated migration is forbidden outright, and FF-004
-- issues a real UPDATE after every migration run to prove the refusal still happens.

create table repair_jobs (
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
    location_key  text not null,              -- CHG-017(a), proposed: the normalised
                                              --   neighbourhood this job answers
    created_at    text not null,
    updated_at    text not null,

    unique (scenario_id, location_key)
                                              -- AC-007, in the schema. Two jobs for one
                                              --   location cannot exist, so no crew can be
                                              --   sent to a place another crew is already at
);

create index repair_jobs_scenario_status on repair_jobs (scenario_id, status);

create table damage_reports (
    id               text primary key,
    scenario_id      text not null references scenarios (id) on delete cascade,
    asset_id         text references assets (id) on delete set null,
                                              -- optional on purpose: §4 says a report naming no
                                              --   matching asset is still a report, and is
                                              --   never dropped for being unattributable
    repair_job_id    text references repair_jobs (id) on delete set null,
                                              -- AC-007: one nullable foreign key IS the rule. A
                                              --   report cannot belong to two jobs, so no crew
                                              --   is sent twice
    location         text not null,           -- json
    reported_at      text not null,
    reported_by      text not null,
                                              -- a plain string rather than a foreign key, as §3
                                              --   specifies: today it holds the acting user id,
                                              --   and a radio or alarm channel can be recorded
                                              --   later without a schema change
    status           text not null
                     check (status in ('open', 'duplicate', 'dismissed')),
    dismissed_by     text references users (id),
    dismissed_reason text,

    check (status <> 'dismissed'
           or (dismissed_by is not null and dismissed_reason is not null)),
                                              -- REQ-F-008: dismissal stays one action, but never
                                              --   becomes anonymous. TASK-008 writes it; the
                                              --   constraint is §3's and belongs with the table

    check (json_valid(location)
           and json_type(location, '$.neighbourhood') = 'text'
           and length(trim(json_extract(location, '$.neighbourhood'))) between 1 and 120
           and json(location) = json_object('neighbourhood',
                                            json_extract(location, '$.neighbourhood')))
                                              -- CON-003 / REQ-NF-007, CHG-017(b) proposed. The
                                              --   equality is the load-bearing half: any extra
                                              --   key — address, meter_id, lat, lon, household —
                                              --   makes the rebuilt object differ, and the row
                                              --   is refused
);

create index damage_reports_scenario_status_job
    on damage_reports (scenario_id, status, repair_job_id);
                                              -- the index `data-and-integration-spec.md` §2
                                              --   requires, and the one PTEST-002 checks the
                                              --   board query against

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
