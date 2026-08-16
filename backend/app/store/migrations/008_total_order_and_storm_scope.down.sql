-- 008 down.
--
-- Back to 007's shape: the sequence columns and the two unique parent-key indexes go, and
-- damage_reports is rebuilt with the plain `references assets (id)` it had before.
--
-- **The decision_records triggers are not touched here**: 008 did not create them, it
-- re-asserted them, and a down migration that removed BR-004's enforcement as a side effect of
-- rolling back an ordering fix is exactly the failure ADR-004 exists to prevent.
--
-- Rolling this back reinstates two defects knowingly: two rows written in one clock tick come
-- back in coin-flip order again, and a damage report may once more name an asset from a
-- different storm. It is written because database-design.md §8 requires every migration to
-- ship a down, not because running it is ever routine.

drop index if exists damage_reports_seq;
drop index if exists damage_reports_scenario_status_job;

create table damage_reports_old (
    id               text primary key,
    scenario_id      text not null references scenarios (id) on delete cascade,
    asset_id         text references assets (id) on delete set null,
    repair_job_id    text references repair_jobs (id) on delete set null,
    location         text not null,
    reported_at      text not null,
    reported_by      text not null,
    status           text not null
                     check (status in ('open', 'duplicate', 'dismissed')),
    dismissed_by     text references users (id),
    dismissed_reason text,

    check (status <> 'dismissed'
           or (dismissed_by is not null and dismissed_reason is not null)),

    check (json_valid(location)
           and json_type(location, '$.neighbourhood') = 'text'
           and length(trim(json_extract(location, '$.neighbourhood'))) between 1 and 120
           and json(location) = json_object('neighbourhood',
                                            json_extract(location, '$.neighbourhood')))
);

insert into damage_reports_old
    (id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
     dismissed_by, dismissed_reason)
select id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status,
       dismissed_by, dismissed_reason
from damage_reports;

drop table damage_reports;
alter table damage_reports_old rename to damage_reports;

create index damage_reports_scenario_status_job
    on damage_reports (scenario_id, status, repair_job_id);

drop index if exists repair_jobs_id_scenario;
drop index if exists assets_id_scenario;
drop index if exists repair_jobs_seq;
alter table repair_jobs drop column seq;

-- decision_records keeps its column. `alter table ... drop column` rewrites the table, and the
-- one table in this schema that may never be rewritten is the append-only one — the rewrite
-- would carry its rows through a delete the triggers exist to refuse. The column is inert when
-- nothing reads it.
drop index if exists decision_records_seq;
