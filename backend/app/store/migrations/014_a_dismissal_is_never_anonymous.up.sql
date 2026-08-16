-- 014 — a dismissal is one action, and never an anonymous one (TASK-008)
--
-- Three change entries, all raised rather than assumed and all left **proposed**: CHG-033,
-- CHG-034, CHG-035.
--
-- `database-design.md` §1 states REQ-F-008's rule in one line — *a dismissed report carries who
-- dismissed it and why* — and §3 traces it to one check constraint:
--
--     check (status <> 'dismissed' or (dismissed_by is not null and dismissed_reason is not null))
--
-- That constraint is real and it is not the rule. Three things were found by asking the question
-- the last four reviews have each asked: **what can a direct insert put in that column?**
--
--   CHG-033 A REASON THAT IS NOT ONE SATISFIES `is not null`.
--     Issued directly against 009's shape, the store ACCEPTED `''`, `'   '`, `char(9)||char(10)`
--     and `'  padded  '` as reasons for a dismissal. The first three are an anonymous dismissal
--     wearing a reason's clothes — the exact failure `edge-cases-and-failures.md` names for
--     UTEST-011, *control made cheap and untraceable* — and the fourth is a second spelling of
--     one reason, which this repository has paid for twice already (CHG-023, CHG-031). It is
--     also the same hole in the same table one column over: CHG-023 found that
--     `length(trim(...)) between 1 and 120` refused a spaces-only neighbourhood and **stored** a
--     tab-and-newline one, because SQLite's one-argument `trim()` strips spaces and nothing
--     else. The two-argument form, with the whitespace enumerated, is what closes both.
--
--     The constraint is also **named** here. `CHECK constraint failed: damage_reports` says a
--     row was refused; it does not say which rule refused it, and `damage_reports` has three
--     checks that raise the same class. `review-log.md`'s lesson about a refusal asserted by its
--     status code is the same lesson one layer down: *an assertion about a refusal has to name
--     which refusal.* Naming the constraints is what lets the tests do that.
--
--     ONE BOUND, TIED TO ITS COPY. `length(dismissed_reason) <= 2000` is the same number
--     `store/dispatch.py:DISMISSAL_REASON_MAX` names, and `test_UTEST-011` reads it back out of
--     `sqlite_master` and requires the two to agree. It is written as `>= 1` and `<= 2000`
--     rather than `between 1 and 2000` deliberately, which is migration 012's reason reused:
--     UTEST-012 reads **every** `between 1 and N` out of this table and requires them all to be
--     the neighbourhood bound, so a second `between` here would make that assertion unable to
--     tell one bound from the other.
--
--   CHG-034 A DISMISSAL COULD BE REWRITTEN.
--     Nothing stopped `update damage_reports set dismissed_by = ?, dismissed_reason = ?` on an
--     already-dismissed report, so *who dismissed it and why* meant *whoever wrote it last*, and
--     `update ... set status = 'open'` quietly un-cleared an alarm while leaving the dismissal
--     fields behind. CHG-026's argument on `risk_scores`, one table over: the rule lived in the
--     fact that no code issued the statement, and ADR-002 exists because "a rule that lives only
--     in code is removed by the first refactor with every test still green".
--
--     `damage_reports_dismissal_is_final` is narrow on purpose. It fires only when the row was
--     ALREADY dismissed, and only refuses a change to the three columns that carry the
--     dismissal. An open report can still be marked `duplicate` (CHG-021's state), and a
--     dismissed report's other columns are not frozen — a trigger that refused every update
--     would be refusing a thing nobody asked to be refused, and the silent case in UTEST-011 is
--     what keeps it honest.
--
--   CHG-035 `decision_records.kind` HAS PERMITTED `'dismiss'` SINCE 006 WITH NO WRITER.
--     No reader, and no decided shape. That is the third instance of the shape CHG-021 named
--     for `status = 'duplicate'` and CHG-029 named for `kind = 'placement'` — *a value the
--     schema permits is a state a screen can reach, and a state a screen can reach is one it has
--     to render.* And AC-008 is unambiguous about which way it should be settled: *given **any**
--     recommendation or human decision, a row is appended carrying the timestamp and the acting
--     user, and no path exists to edit or remove it.* Clearing a false alarm is a human
--     decision, and `damage_reports` is not append-only.
--
--     `decision_records_dismiss_shape` requires the row to agree with the report it names, which
--     is **membership rather than existence** — the distinction CHG-019 was blocked over and
--     CHG-029's seventh clause turns on. A row claiming somebody dismissed a report that is
--     still open is an audit trail asserting something that did not happen, and an audit trail
--     that can be contradicted by its own subject is what BR-004 exists to prevent.
--
--     THE PAYLOAD DUPLICATES THREE FACTS AND THAT IS THE POINT, not an oversight. CHG-017
--     declined a display column on `repair_jobs` because "two places to disagree about one
--     fact" — the argument does not apply here for one reason: `decision_records` deliberately
--     does not cascade with its scenario (migration 006, "an audit row must outlive the thing it
--     describes"), so a row that only pointed at the report would say nothing at all once the
--     storm was deleted. The trigger is what stops the two copies ever disagreeing: they must be
--     equal at the moment the audit row is written, and neither can move afterwards — the report
--     because of CHG-034, the record because of BR-004.
--
-- WHY THE FIRST IS A CHECK AND THE OTHER TWO ARE TRIGGERS.
--
-- ADR-002 and CHG-019 both say a rule the schema can express should not be a trigger. CHG-033 is
-- expressible, so it is a `check` — which means rebuilding `damage_reports`, because SQLite has
-- no `alter table ... add check`. That is migration 009's procedure, on the same table, and the
-- foreign keys are turned off across the rebuild for the reason 009 gives.
--
-- CHG-034 cannot be a check: a check cannot see `old`. CHG-035 cannot be either: a check cannot
-- see another table, and the clause that matters is a join — CHG-026, CHG-028(b) and CHG-029's
-- argument, unchanged. Rebuilding `decision_records` to add one is forbidden outright, because
-- `drop table` takes both append-only triggers with it (ADR-004, CLAUDE.md's Never list).
--
-- A LIMIT RECORDED RATHER THAN IMPLIED AWAY. `decision_records_dismiss_shape` says what may be
-- **written**, not what may **exist**: a report deleted afterwards leaves its dismissal record
-- behind, which is exactly what an audit row is for. And because that trigger reads
-- `damage_reports`, **any future migration that rebuilds `damage_reports` must drop it first and
-- recreate it afterwards** — since SQLite 3.25 an `alter table ... rename to` reparses every
-- trigger in the schema, so a rebuild with this trigger applied aborts in the window where the
-- table does not exist. 012 carries the same note about `risk_scores`, and 014's own down
-- migration drops it before it rebuilds.
--
-- BOTH decision_records TRIGGERS ARE RE-ASSERTED AT THE END OF THIS FILE (ADR-004, BR-004).
-- Neither is dropped, disabled or recreated here, and this migration does not rebuild that table.

pragma foreign_keys = off;

begin;

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
                                              --   belong to none — a state the board has to
                                              --   render (CHG-022)
    location         text not null,           -- json
    reported_at      text not null,
    reported_by      text not null,
    status           text not null
                     check (status in ('open', 'duplicate', 'dismissed')),
    dismissed_by     text references users (id),
    dismissed_reason text,
    seq              integer not null,        -- CHG-018

    constraint damage_reports_dismissal_is_attributed
    check (status <> 'dismissed'
           or (dismissed_by is not null
               and dismissed_reason is not null
               and dismissed_reason = trim(dismissed_reason,
                                           ' ' || char(9) || char(10) || char(11)
                                           || char(12) || char(13))
               and length(dismissed_reason) >= 1
               and length(dismissed_reason) <= 2000)),
                                              -- REQ-F-008, CHG-033. One action, never anonymous.
                                              --   The two-argument `trim` is the load-bearing
                                              --   part: the one-argument form strips spaces
                                              --   only, so `'   '` was refused and `'\t\n'` was
                                              --   stored — the same non-answer wearing a
                                              --   different whitespace character. Bounded with
                                              --   `>=` and `<=` rather than `between`, so this
                                              --   table's one `between 1 and 120` stays
                                              --   unambiguously the neighbourhood's

    constraint damage_reports_location_is_a_neighbourhood
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
                                              -- CON-003 / REQ-NF-007, CHG-017(b) and CHG-023,
                                              --   unchanged from 009 except that it now has a
                                              --   name, so a test can say WHICH rule refused a
                                              --   row rather than only that one did

    foreign key (asset_id, scenario_id)
        references assets (id, scenario_id) on delete cascade,
                                              -- CHG-019: the asset must be in THIS storm
    foreign key (repair_job_id, scenario_id)
        references repair_jobs (id, scenario_id) on delete cascade
                                              -- CHG-019: and so must the job. The cascade on
                                              --   the asset key is CHG-024, recorded there
);

-- No data is transformed. A dismissal the older shape accepted and this one refuses — an empty
-- or whitespace-only reason — makes this statement fail and the whole migration abort inside a
-- transaction that rolls back whole. That is deliberate: deciding what somebody's reason was is
-- not a migration's decision to take, and inventing one would put a fabricated fact on the
-- column REQ-F-008 exists to make trustworthy. Migration 010's loud backfill and 013's refusal
-- to choose between two storms are the same rule; `test_TASK-008-AC9` asserts it.
insert into damage_reports_new
    (id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
     dismissed_by, dismissed_reason, seq)
select id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
       dismissed_by, dismissed_reason, seq
from damage_reports;

drop table damage_reports;
alter table damage_reports_new rename to damage_reports;

-- Every index the dropped table carried, re-created by name. `damage_reports_scenario_status_job`
-- is the one PTEST-002's query-plan assertion names; a rebuild that forgot it leaves every
-- functional test green and the board scanning.
create index damage_reports_scenario_status_job
    on damage_reports (scenario_id, status, repair_job_id);
create unique index damage_reports_seq on damage_reports (seq);

commit;

pragma foreign_keys = on;

-- CHG-034. Created after the rebuild, because the rebuild would have dropped it.
create trigger damage_reports_dismissal_is_final
before update on damage_reports
when old.status = 'dismissed'
begin
    -- `is not` rather than `<>`, so a change to or from null is caught: `null <> null` is null,
    -- and a `where` clause that is null selects nothing. That is the same trap migration 012's
    -- first clause records — the obvious spelling of a null-tolerant comparison accepts exactly
    -- the row it was written to refuse.
    select raise(abort, 'a dismissal is recorded once and never rewritten (REQ-F-008, REQ-F-009)')
    where new.status is not old.status
       or new.dismissed_by is not old.dismissed_by
       or new.dismissed_reason is not old.dismissed_reason;
end;

-- CHG-035. Reads `damage_reports`, so it is created after the rebuild and dropped before any
-- future one.
create trigger decision_records_dismiss_shape
before insert on decision_records
when new.kind = 'dismiss'
begin
    -- 1. `decision_records_by_subject` is the index this record is found through, so a
    --    dismissal filed under any other subject type is a decision nobody looking at the
    --    report will ever find.
    select raise(abort, 'a dismissal names a damage report as its subject (REQ-F-008)')
    where new.subject_type <> 'damage_report';

    -- 2. The load-bearing clause: membership, not existence, on caller-supplied input. The row
    --    must agree with the report it names in every particular it repeats — the storm, the
    --    fact of the dismissal, the actor, the reason, the neighbourhood and the repair job.
    --    Anything less and the audit trail is free to say a thing that did not happen.
    --
    --    `coalesce(..., '')` on the job, because a report may legitimately belong to none
    --    (CHG-022) and `null = null` is null, which a `where` clause reads as false — the row
    --    that most needs to be recordable would be the one refused.
    select raise(abort, 'a dismissal record must agree with the report it names: this storm, dismissed, by this actor, for this reason, in this neighbourhood, against this repair job (REQ-F-008, REQ-F-009)')
    where not exists (
        select 1 from damage_reports r
        where r.id = new.subject_id
          and r.scenario_id = new.scenario_id
          and r.status = 'dismissed'
          and r.dismissed_by = new.actor_user_id
          and r.dismissed_reason = json_extract(new.payload, '$.reason')
          and json_extract(r.location, '$.neighbourhood')
              = json_extract(new.payload, '$.neighbourhood')
          and coalesce(r.repair_job_id, '')
              = coalesce(json_extract(new.payload, '$.repair_job_id'), '')
    );
end;

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
