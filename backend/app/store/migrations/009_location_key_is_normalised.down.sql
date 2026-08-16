-- 009 down.
--
-- Back to 008's shape: `repair_jobs` loses the normalisation check and the unique constraint
-- goes back to a byte-comparison. Rolling this back reinstates the defect knowingly — a second
-- repair job for one neighbourhood, spelled differently, becomes storable again, and the rule
-- that defines "the same location" goes back to living only in `store/dispatch.py`.
--
-- Foreign keys are disabled for the rebuild for the same reason 009 disables them: `drop table
-- repair_jobs` performs an implicit delete, and `damage_reports` cascades from it.
--
-- **The decision_records triggers are not touched here**: 009 did not create them, it
-- re-asserted them, and a down migration that removed BR-004's enforcement as a side effect of
-- rolling back a grouping rule is exactly the failure ADR-004 exists to prevent.

pragma foreign_keys = off;

begin;

create table repair_jobs_old (
    id            text primary key,
    scenario_id   text not null references scenarios (id) on delete cascade,
    status        text not null
                  check (status in ('pending', 'in_progress', 'done')),
    priority_rank integer,
    assigned_to   text,
    location_key  text not null,
    created_at    text not null,
    updated_at    text not null,
    seq           integer not null default 0,

    unique (scenario_id, location_key)
);

insert into repair_jobs_old
    (id, scenario_id, status, priority_rank, assigned_to, location_key, created_at, updated_at,
     seq)
select id, scenario_id, status, priority_rank, assigned_to, location_key, created_at, updated_at,
       seq
from repair_jobs;

drop table repair_jobs;
alter table repair_jobs_old rename to repair_jobs;

create index repair_jobs_scenario_status on repair_jobs (scenario_id, status);
create unique index repair_jobs_seq on repair_jobs (seq);
create unique index repair_jobs_id_scenario on repair_jobs (id, scenario_id);

-- `damage_reports` back to 008's location check: `trim()` on spaces only, and no rule about
-- what the displayed neighbourhood looks like. Everything else is unchanged.
create table damage_reports_old (
    id               text primary key,
    scenario_id      text not null references scenarios (id) on delete cascade,
    asset_id         text,
    repair_job_id    text,
    location         text not null,
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
           and length(trim(json_extract(location, '$.neighbourhood'))) between 1 and 120
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
