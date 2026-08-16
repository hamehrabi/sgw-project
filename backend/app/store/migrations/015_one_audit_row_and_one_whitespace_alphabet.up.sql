-- 015 — one human decision, one audit row; and one alphabet for what counts as blank (TASK-008,
-- remediation of the Block recorded in `review-log.md` on 2026-08-16 and re-confirmed the same
-- day on a byte-identical tree).
--
-- Two change entries, both raised rather than assumed and both left **proposed**: CHG-036,
-- CHG-037. Neither invents a requirement; each puts a rule the code already believed into the
-- place ADR-002 says it has to live.
--
--   CHG-036 *EXACTLY ONE* `decision_records` ROW OF KIND `dismiss` WAS SERVICE CODE.
--     TASK-008's done criterion 7 is *"exactly one `decision_records` row of kind `dismiss` is
--     appended"*, and `api/dismissals.py` says why in its own comment: the `409` is *"decided
--     before the write so a retrying client cannot produce two audit rows for one human
--     decision."* The store held only half of it. `damage_reports_dismissal_is_final` fires
--     `when old.status = 'dismissed'` and aborts only when `status`, `dismissed_by` or
--     `dismissed_reason` **change**, so a *different* second dismissal was refused and an
--     **identical** one was not: the `update` changed nothing, the trigger stayed quiet, and
--     `append_dismissal` wrote a second audit row that `decision_records_dismiss_shape` then
--     accepted, because it agreed with the report in every particular. With the endpoint's
--     `409` branch and `dismiss_report`'s `status <> ?` guard removed, an identical retry was
--     answered `201` twice and left **2** `dismiss` rows for one human decision, with the whole
--     gate green.
--
--     A **partial unique index** is the whole of the fix. It creates no table and drops no
--     trigger, so ADR-004's prohibition is not approached: `decision_records` cannot be given a
--     `check` without a rebuild, and a rebuild takes both append-only triggers with it. Partial
--     indexes have existed since SQLite 3.8.0 and this platform is 3.49.1.
--
--     `subject_id` alone is enough, and stronger than the pair: a report id is unique across the
--     database, and `decision_records_dismiss_shape` already refuses a `dismiss` row whose
--     subject is not a damage report. The `where kind = 'dismiss'` predicate is what keeps every
--     other kind unaffected — a ranking carries any number of placements (CHG-029) and a
--     recommendation is re-read without a second row.
--
--     THE REFUSAL IS IDENTIFIED BY ITS OWN SENTENCE, which is this repository's standing rule
--     after six assertions that could not fail for the reason they claimed. SQLite answers
--     `UNIQUE constraint failed: decision_records.subject_id`, and that names this rule and no
--     other: it is the only unique constraint on that column, and the only one on this table
--     besides its primary key.
--
--   CHG-037 WHAT COUNTS AS WHITESPACE WAS WRITTEN THREE TIMES AND THE THREE DISAGREED.
--     014 enumerated six ASCII characters, `store/dispatch.WHITESPACE` repeated the same six,
--     and the browser used JavaScript's `String.prototype.trim()`, which is Unicode-aware. On an
--     untouched tree, `POST /api/v1/damage-reports/{id}/dismiss` with a reason of U+00A0, U+2003,
--     U+200B or U+FEFF was answered **201** and that character was what `dismissed_reason` and
--     the audit row held. `'   '` was refused and a no-break space was stored — *the same
--     non-answer wearing a different whitespace character*, which is CHG-023's own sentence, for
--     the third time, on the very column CHG-033 was written to close.
--
--     It was invisible on screen because the **strictest** of the three definitions was the
--     browser's: the button stayed disabled, so only a caller reaching the API met it. That is
--     the enforcement sitting in the one layer ADR-002 says it must never sit in.
--
--     One alphabet now, enumerated in `store/dispatch.BLANK_CODEPOINTS`, repeated here as
--     `char(...)` and in `frontend/lib/dismissal.ts`, with a test that reads all three and
--     requires them to be identical — *a rule written in more than one place needs something
--     that fails when the copies disagree*, which is the row `AGENT.md` already carries about a
--     bound and which is just as true of an alphabet.
--
--     THE SAME HOLE SAT IN `damage_reports_location_is_a_neighbourhood` and is closed in the
--     same breath. Every clause of it accepted `{"neighbourhood": " "}` (U+00A0) when the JSON
--     was written as raw UTF-8; it was unreachable only because `store/dispatch.py` calls
--     `json.dumps` with `ensure_ascii` at its default, so the escaped character tripped the
--     *unrelated* `json(location) = json_object(...)` clause instead. CON-003's guard against *a
--     location that is not a place* was being held up by a serialiser default, and the day a
--     neighbourhood needs an accent that default changes.
--
--     The five `instr(..., char(n)) = 0` clauses become one `not glob '*[' || char(...) || ']*'`
--     over the alphabet without the space. It is the same claim — *no blank character other than
--     a single interior space* — over thirty characters instead of five, and `||` binds tighter
--     than `glob`, so the class is built before the match.
--
-- WHY THIS IS A NEW MIGRATION RATHER THAN AN EDIT TO 014. A migration that has run is a fact
-- about a database somebody may already hold; 008 and 009 were TASK-005's two remediations and
-- 011 was TASK-006's, and this is the same procedure. The cost is one more rebuild of
-- `damage_reports` and it is worth it.
--
-- THE TWO TRIGGERS ARE DROPPED BEFORE THE REBUILD AND RECREATED AFTER IT, AND THE ORDER IS
-- LOAD-BEARING. `decision_records_dismiss_shape` reads `damage_reports`, and since SQLite 3.25
-- an `alter table ... rename to` reparses every trigger in the schema to fix up its references —
-- so with that trigger applied the rename lands in the window where the table does not exist and
-- aborts. 014's own header records the requirement; this file is the first migration to meet it.
--
-- BOTH decision_records TRIGGERS ARE RE-ASSERTED AT THE END OF THIS FILE (ADR-004, BR-004).
-- Neither is dropped, disabled or recreated here, and this migration does not rebuild that table.

drop trigger if exists decision_records_dismiss_shape;
drop trigger if exists damage_reports_dismissal_is_final;

pragma foreign_keys = off;

begin;

create table damage_reports_new (
    id               text primary key,
    scenario_id      text not null references scenarios (id) on delete cascade,
    asset_id         text,
    repair_job_id    text,
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
               and dismissed_reason
                   = trim(dismissed_reason,
                          char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760,
                               8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200,
                               8201, 8202, 8203, 8232, 8233, 8239, 8287, 12288, 65279))
               and length(dismissed_reason) >= 1
               and length(dismissed_reason) <= 2000)),
                                              -- REQ-F-008, CHG-033 and CHG-037. One action,
                                              --   never anonymous. The alphabet is the whole
                                              --   change from 014: six ASCII characters let a
                                              --   no-break space through as a reason. Only the
                                              --   ends are governed — a reason is somebody's
                                              --   sentence. Bounded with `>=` and `<=` rather
                                              --   than `between`, so this table's one
                                              --   `between 1 and 120` stays unambiguously the
                                              --   neighbourhood's

    constraint damage_reports_location_is_a_neighbourhood
    check (json_valid(location)
           and json_type(location, '$.neighbourhood') = 'text'
           and length(json_extract(location, '$.neighbourhood')) between 1 and 120
           and json_extract(location, '$.neighbourhood')
               = trim(json_extract(location, '$.neighbourhood'),
                      char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760,
                           8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200,
                           8201, 8202, 8203, 8232, 8233, 8239, 8287, 12288, 65279))
           and json_extract(location, '$.neighbourhood') not like '%  %'
           and json_extract(location, '$.neighbourhood')
               not glob '*[' || char(9, 10, 11, 12, 13, 28, 29, 30, 31, 133, 160, 5760,
                                     8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200,
                                     8201, 8202, 8203, 8232, 8233, 8239, 8287, 12288, 65279)
                             || ']*'
           and json(location) = json_object('neighbourhood',
                                            json_extract(location, '$.neighbourhood'))),
                                              -- CON-003 / REQ-NF-007, CHG-017(b), CHG-023 and
                                              --   CHG-037. The alphabet is the change: a
                                              --   whitespace-only neighbourhood written as raw
                                              --   UTF-8 was accepted by every clause, and the
                                              --   only thing refusing it was a serialiser
                                              --   default one module away. The glob class is
                                              --   the alphabet WITHOUT the space, because a
                                              --   single interior space is what a two-word
                                              --   neighbourhood is made of

    foreign key (asset_id, scenario_id)
        references assets (id, scenario_id) on delete cascade,
                                              -- CHG-019: the asset must be in THIS storm
    foreign key (repair_job_id, scenario_id)
        references repair_jobs (id, scenario_id) on delete cascade
                                              -- CHG-019: and so must the job
);

-- No data is transformed, for 014's reason unchanged: a location or a dismissal reason the older
-- alphabet accepted and this one refuses makes this statement fail and the whole migration abort
-- inside a transaction that rolls back whole. Deciding what somebody's reason was, or where they
-- meant, is not a migration's decision to take.
insert into damage_reports_new
    (id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
     dismissed_by, dismissed_reason, seq)
select id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
       dismissed_by, dismissed_reason, seq
from damage_reports;

drop table damage_reports;
alter table damage_reports_new rename to damage_reports;

-- Every index the dropped table carried, re-created by name. `damage_reports_scenario_status_job`
-- is the one PTEST-002's query-plan assertion names.
create index damage_reports_scenario_status_job
    on damage_reports (scenario_id, status, repair_job_id);
create unique index damage_reports_seq on damage_reports (seq);

commit;

pragma foreign_keys = on;

-- CHG-034, unchanged from 014 and recreated because the rebuild dropped it.
create trigger damage_reports_dismissal_is_final
before update on damage_reports
when old.status = 'dismissed'
begin
    select raise(abort, 'a dismissal is recorded once and never rewritten (REQ-F-008, REQ-F-009)')
    where new.status is not old.status
       or new.dismissed_by is not old.dismissed_by
       or new.dismissed_reason is not old.dismissed_reason;
end;

-- CHG-035, unchanged from 014 and recreated because it reads the rebuilt table.
create trigger decision_records_dismiss_shape
before insert on decision_records
when new.kind = 'dismiss'
begin
    select raise(abort, 'a dismissal names a damage report as its subject (REQ-F-008)')
    where new.subject_type <> 'damage_report';

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

-- CHG-036. One human decision, one audit row — in the store, where the endpoint's `409` and
-- `dismiss_report`'s `status <> ?` guard were the only two copies of it.
--
-- It is created after the triggers above rather than before, so that a database carrying two
-- `dismiss` rows for one report — reachable only by a direct insert while 014 was rolled back —
-- fails **here**, loudly, with the whole migration rolled back, rather than being silently
-- deduplicated. BR-004 means nothing may go back and tidy such rows; a person has to look.
create unique index decision_records_one_dismissal_per_report
    on decision_records (subject_id)
    where kind = 'dismiss';

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
