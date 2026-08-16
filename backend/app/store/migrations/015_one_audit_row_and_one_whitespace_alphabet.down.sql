-- 015 down.
--
-- Back to 014's shape: `damage_reports` with the six-ASCII alphabet in both checks, and no
-- unique index standing between a retrying client and a second audit row.
--
-- Rolling this back reinstates two defects knowingly, and saying so out loud is the point of
-- this paragraph rather than leaving them to be discovered:
--
--   * A dismissal reason of one no-break space, em space, zero width space or U+FEFF is accepted
--     again — `201`, stored, and shown as the reason under a dispatcher's name. `'   '` is still
--     refused, which is what makes it hard to see. The same alphabet comes off
--     `damage_reports_location_is_a_neighbourhood`, so a whitespace-only neighbourhood becomes
--     storable again the moment anything writes its JSON as raw UTF-8.
--   * *Exactly one audit row per human decision* goes back to living in `api/dismissals.py`'s
--     `409` branch and `store/dispatch.dismiss_report`'s `status <> ?` guard — two service-layer
--     copies, which is ADR-002's prohibition and `review-log.md`'s standing Block condition.
--     Rows written while the index was gone are **not** revisited when it comes back: the index
--     says what may be **written**, and re-applying 015 over a duplicated report aborts rather
--     than choosing which of two audit rows to believe.
--
-- **015 MUST BE ROLLED BACK BEFORE 014 AND NOT AFTER.** Both rebuild `damage_reports`, and both
-- recreate the two triggers that read it; taking 014 off first would leave this file rebuilding
-- a table 014's rebuild had already replaced, with 014's triggers reparsed against it. The
-- ordinary reverse order is the right one and `test_TASK-008-AC9` asserts it.
--
-- **THE TWO TRIGGERS ARE DROPPED BEFORE THE TABLE IS REBUILT** for 014's reason unchanged:
-- `decision_records_dismiss_shape` reads `damage_reports`, and an `alter table ... rename to`
-- reparses every trigger in the schema.
--
-- **The decision_records append-only triggers are not touched here.** 015 did not create them,
-- it re-asserted them, and a down migration that removed BR-004's enforcement as a side effect
-- would be exactly the failure ADR-004 exists to prevent.

drop index if exists decision_records_one_dismissal_per_report;

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

    constraint damage_reports_dismissal_is_attributed
    check (status <> 'dismissed'
           or (dismissed_by is not null
               and dismissed_reason is not null
               and dismissed_reason = trim(dismissed_reason,
                                           ' ' || char(9) || char(10) || char(11)
                                           || char(12) || char(13))
               and length(dismissed_reason) >= 1
               and length(dismissed_reason) <= 2000)),

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

-- 014's two triggers, recreated verbatim, because the rebuild above dropped them.
create trigger damage_reports_dismissal_is_final
before update on damage_reports
when old.status = 'dismissed'
begin
    select raise(abort, 'a dismissal is recorded once and never rewritten (REQ-F-008, REQ-F-009)')
    where new.status is not old.status
       or new.dismissed_by is not old.dismissed_by
       or new.dismissed_reason is not old.dismissed_reason;
end;

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
