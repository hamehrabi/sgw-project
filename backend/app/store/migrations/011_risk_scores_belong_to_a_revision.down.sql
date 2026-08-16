-- 011 down.
--
-- Back to 010's shape: `risk_scores` with `references assets (id)` and `risk_scores_no_update` as
-- its only guard.
--
-- Rolling this back reinstates three defects knowingly, and all three are worth saying out loud
-- rather than leaving to be discovered:
--
--   * A ranking can be deleted and reinserted again, so AC-005's *"the previous order remains
--     retrievable"* goes back to holding only for the `UPDATE` path.
--   * A ranking can name a forecast revision the storm does not carry, which makes
--     `GET /scenarios/{id}`'s `ranked` flag (CHG-027) report an order that cannot be read.
--   * `risk_scores.asset_id` goes back to proving an asset exists somewhere rather than that it
--     belongs to this storm — CHG-019's shape, back on the table it was recorded against.
--
-- **This must run before 010's down migration and not after.** `risk_scores_names_a_forecast`
-- reads `scenario_forecast_revisions`, which 010's down migration drops; leaving the trigger
-- behind a dropped table makes every later `insert into risk_scores` fail with *no such table*,
-- which is a loud failure rather than a silent one but is still a broken database. Migrations
-- roll back in reverse order for exactly this reason, and the AC13 test walks the trip in both
-- directions rather than asserting the rule in a comment.
--
-- **The decision_records triggers are not touched here**: 011 did not create them, it
-- re-asserted them, and a down migration that removed BR-004's enforcement as a side effect of
-- rolling back a foreign key is exactly the failure ADR-004 exists to prevent.

begin;

drop trigger if exists risk_scores_no_update;
drop trigger if exists risk_scores_no_delete;
drop trigger if exists risk_scores_names_a_forecast;

create table risk_scores_old (
    id                 text primary key,
    scenario_id        text not null references scenarios (id) on delete cascade,
    asset_id           text not null references assets (id) on delete cascade,
    forecast_revision  integer not null,
    score              real,
    band               text
                       check (band is null or band in ('High', 'Medium', 'Low')),
    rank               integer,
    reasons            text not null,
    unscored_reason    text,
    weight_set_version text not null,
    computed_at        text not null,

    check (json_array_length(reasons) >= 1 or score is null),
    check (score is not null or unscored_reason is not null),
    unique (scenario_id, asset_id, forecast_revision)
);

insert into risk_scores_old
    (id, scenario_id, asset_id, forecast_revision, score, band, rank, reasons, unscored_reason,
     weight_set_version, computed_at)
select id, scenario_id, asset_id, forecast_revision, score, band, rank, reasons, unscored_reason,
       weight_set_version, computed_at
from risk_scores;

drop table risk_scores;
alter table risk_scores_old rename to risk_scores;

create index risk_scores_ranking on risk_scores (scenario_id, forecast_revision, rank);

-- 010's guard, back as 010 left it: the UPDATE half of *never rewrites n* and nothing else.
create trigger risk_scores_no_update
before update on risk_scores
begin
    select raise(abort, 'a stored ranking is never rewritten; a forecast change writes a new revision (REQ-F-004, AC-005)');
end;

commit;
