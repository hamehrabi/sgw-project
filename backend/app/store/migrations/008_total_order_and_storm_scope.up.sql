-- 008 — a total order, and storm membership in the schema (TASK-005, second review)
--
-- Two findings from the second review of TASK-005, and neither is a new feature. Both are
-- raised as change entries rather than assumed silently:
--
--   CHG-018 `seq` on every table read chronologically.
--     Every chronological read was `order by <timestamp>, id`. `datetime.now(UTC).isoformat()`
--     resolves to about 15.6 ms on this platform — 1,999 of 2,000 consecutive calls returned an
--     identical string — and `id` is a random UUID hex, so two rows written inside one tick came
--     back in coin-flip order. Two tests asserted that order and failed on a third of clean runs.
--     A total order needs a key that is total: a timestamp is not one, and a random identifier
--     is not a tiebreak. `seq` is a monotonic per-table sequence, `unique` so the store refuses
--     two rows that claim the same place in the history.
--
--   CHG-019 storm membership, not merely existence.
--     `damage_reports.asset_id references assets (id)` proves an asset exists. It never proved
--     the asset belongs to the storm the report names, and the only thing that did was an `if`
--     in `api/dispatch.py` — a rule in the service layer that the store could refuse, which is
--     `review-log.md`'s pre-declared Block condition and ADR-002's exact prohibition. Issued
--     directly against the schema, a storm-A report could name storm-B's asset and hang off
--     storm-B's repair job. "The scenario is the scoping root ... a missing scope is a
--     correctness bug — two storms blended into one ranking would look entirely plausible."
--     Fixed with composite foreign keys over `(scenario_id, <id>)`, which SQLite can only
--     enforce against a UNIQUE parent key — hence the two unique indexes below.
--
-- BOTH decision_records TRIGGERS ARE RE-ASSERTED AT THE END OF THIS FILE (ADR-004, BR-004).
-- Neither is dropped, disabled or recreated here. One consequence is visible in step 4 and is
-- deliberate: `decision_records` cannot be backfilled, because the BEFORE UPDATE trigger
-- refuses the statement. That refusal is the guarantee working, not an obstacle to route around.

-- 1. repair_jobs: the sequence, backfilled from the rowid it was already written in.
alter table repair_jobs add column seq integer not null default 0;
update repair_jobs set seq = rowid;
create unique index repair_jobs_seq on repair_jobs (seq);

-- 2. The parent keys a composite foreign key needs. `id` is already unique on both tables, so
--    neither index changes what may be stored — each makes `(id, scenario_id)` addressable as a
--    foreign-key target, which is the only way SQLite will enforce membership rather than
--    existence.
--
--    **Ordered id-first on purpose.** `(scenario_id, id)` would serve `where scenario_id = ?`
--    just as well as the board's own index, the planner would sometimes choose it, and
--    `repair_jobs_scenario_status` would go back to being an index no test can make red —
--    which is the second review's minor finding, reintroduced by the fix for its major one.
create unique index assets_id_scenario on assets (id, scenario_id);
create unique index repair_jobs_id_scenario on repair_jobs (id, scenario_id);

-- 3. damage_reports, rebuilt. SQLite cannot add a foreign key to an existing table, so the
--    table is recreated and copied — the standard rebuild, and safe here because nothing
--    references damage_reports.
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
                                              --   is sent twice
    location         text not null,           -- json
    reported_at      text not null,
    reported_by      text not null,
    status           text not null
                     check (status in ('open', 'duplicate', 'dismissed')),
    dismissed_by     text references users (id),
    dismissed_reason text,
    seq              integer not null,        -- CHG-018: the order reports arrived in, and the
                                              --   only key the board may be ordered by

    check (status <> 'dismissed'
           or (dismissed_by is not null and dismissed_reason is not null)),
                                              -- REQ-F-008: dismissal stays one action, but never
                                              --   becomes anonymous. TASK-008 writes it; the
                                              --   constraint is §3's and belongs with the table

    check (json_valid(location)
           and json_type(location, '$.neighbourhood') = 'text'
           and length(trim(json_extract(location, '$.neighbourhood'))) between 1 and 120
           and json(location) = json_object('neighbourhood',
                                            json_extract(location, '$.neighbourhood'))),
                                              -- CON-003 / REQ-NF-007, CHG-017 proposed. The
                                              --   equality is the load-bearing half: any extra
                                              --   key — address, meter_id, lat, lon, household —
                                              --   makes the rebuilt object differ, and the row
                                              --   is refused

    foreign key (asset_id, scenario_id)
        references assets (id, scenario_id) on delete cascade,
                                              -- CHG-019: the asset must be in THIS storm. A null
                                              --   asset_id still satisfies it (SQLite matches a
                                              --   composite key simply), so an unattributable
                                              --   report is unaffected
    foreign key (repair_job_id, scenario_id)
        references repair_jobs (id, scenario_id) on delete cascade
                                              -- CHG-019: and so must the job. `on delete
                                              --   cascade` rather than `set null`, because a
                                              --   composite child key can only be nulled whole
                                              --   and `scenario_id` is not null — and §7 already
                                              --   hard-deletes reports, jobs and assets together
                                              --   with their scenario, which is the only path
                                              --   that deletes any of them
);

insert into damage_reports_new
    (id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
     dismissed_by, dismissed_reason, seq)
select id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
       dismissed_by, dismissed_reason, rowid
from damage_reports;

drop table damage_reports;
alter table damage_reports_new rename to damage_reports;

create index damage_reports_scenario_status_job
    on damage_reports (scenario_id, status, repair_job_id);
                                              -- the index `data-and-integration-spec.md` §2
                                              --   requires, and the one PTEST-002 names
create unique index damage_reports_seq on damage_reports (seq);

-- 4. decision_records: the sequence, and the one table that cannot be backfilled.
--    `alter table ... add column` is a schema operation and does not go through the trigger.
--    `update decision_records set seq = rowid` would, and would abort — correctly. Any row
--    written before this migration keeps `seq = 0` and the tie it already had; every row
--    written from here on carries a distinct, increasing sequence, which the partial unique
--    index below is what enforces.
alter table decision_records add column seq integer not null default 0;
create unique index decision_records_seq on decision_records (seq) where seq > 0;

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
