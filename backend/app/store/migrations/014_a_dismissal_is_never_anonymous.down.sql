-- 014 down.
--
-- Back to 013's shape: `damage_reports` with 009's unnamed checks, no opinion about whether a
-- dismissal reason is a reason, no guard against a dismissal being rewritten, and no shape for a
-- `decision_records` row of kind `'dismiss'`.
--
-- Rolling this back reinstates three defects knowingly, and saying so out loud is the point of
-- this paragraph rather than leaving them to be discovered:
--
--   * `dismissed_reason = ''` is accepted again, and so is `char(9) || char(10)`. REQ-F-008's
--     *never anonymous* goes back to resting on `api/dismissals.py` remembering to check, which
--     is the service-layer rule ADR-002 forbids and `review-log.md` pre-commits to blocking on.
--   * A dismissal can be rewritten or undone by a direct `UPDATE`. *Who dismissed it and why*
--     means *whoever wrote it last* again.
--   * A `dismiss` row may be appended naming a report nobody dismissed, or disagreeing with the
--     one it names. Rows written while the trigger was gone are **not** revisited when it comes
--     back — the guard says what may be **written**, and BR-004 means nothing can go back and
--     tidy them.
--
-- **THE TWO TRIGGERS ARE DROPPED BEFORE THE TABLE IS REBUILT, AND THE ORDER IS LOAD-BEARING.**
-- `decision_records_dismiss_shape` reads `damage_reports`, and this file drops and renames that
-- table. Since SQLite 3.25 an `alter table ... rename to` reparses every trigger in the schema to
-- fix up its references, so with that trigger still applied the rename lands in the window where
-- `damage_reports` does not exist and aborts. It would abort inside a transaction that rolls back
-- whole — loud rather than lossy — but there is no reason to make an operator meet it, and 012's
-- own down migration carries the same note about `risk_scores`.
--
-- **The decision_records triggers are not touched here.** 014 did not create them, it re-asserted
-- them, and a down migration that removed BR-004's enforcement as a side effect of rolling back a
-- dismissal rule is exactly the failure ADR-004 exists to prevent. `test_TASK-008-AC9` issues a
-- real `UPDATE` and a real `DELETE` after this file has run and requires both refusals, rather
-- than reading two names out of `sqlite_master` — a trigger can be present and wrong.

drop trigger if exists decision_records_dismiss_shape;
drop trigger if exists damage_reports_dismissal_is_final;

pragma foreign_keys = off;

begin;

create table damage_reports_old (
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
    seq              integer not null,

    check (status <> 'dismissed'
           or (dismissed_by is not null and dismissed_reason is not null)),

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

    foreign key (asset_id, scenario_id)
        references assets (id, scenario_id) on delete cascade,
    foreign key (repair_job_id, scenario_id)
        references repair_jobs (id, scenario_id) on delete cascade
);

insert into damage_reports_old
    (id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
     dismissed_by, dismissed_reason, seq)
select id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
       dismissed_by, dismissed_reason, seq
from damage_reports;

drop table damage_reports;
alter table damage_reports_old rename to damage_reports;

create index damage_reports_scenario_status_job
    on damage_reports (scenario_id, status, repair_job_id);
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
