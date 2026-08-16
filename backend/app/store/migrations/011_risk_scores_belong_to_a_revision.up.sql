-- 011 — a stored ranking belongs to a storm's own forecast and to a storm's own asset, and is
--        never deleted-and-reinserted (TASK-006, remediation of the review that blocked it)
--
-- CHG-028, raised rather than assumed and left **proposed**. Three invariants the review found
-- the store could hold and did not. None is reachable from caller input today, which is what kept
-- them observations rather than this log's pre-declared Block — and all three are on the one
-- table AC-005 is actually about.
--
--   (a) *"Never rewrite an earlier revision. Not by `UPDATE`, not by delete-and-reinsert."*
--       TASK-006's own Constraints, and only the first half was in the schema. 010's
--       `risk_scores_no_update` refuses the `UPDATE`; `delete from risk_scores where
--       scenario_id = ? and forecast_revision = 0` followed by one insert was **accepted**, and
--       `GET /risks?forecast_revision=0` then served the rewritten revision 0 with a 200 — the
--       order a crew was placed against, changed underneath the decision that names it.
--
--       010 declined a `before delete` twin **in writing**, because `risk_scores` is
--       cascade-deleted with its scenario and with its assets and a delete guard would turn
--       §7.2's *delete or replace a scenario* into an integrity error. That reasoning is right
--       about an unconditional guard, and it is why CHG-024 declined `on delete no action`. What
--       it missed is that the two cases are **distinguishable inside the trigger**: a cascade
--       deletes the parent row before applying the action to its children, so within one, a
--       parent of the row being removed is already gone. The guard below fires only when **both**
--       parents are still present — which is exactly "a live ranking is being rewritten" and
--       exactly not "the thing it hangs off is being deleted". Both cascades are asserted by
--       tests rather than reasoned about, because SQLite does not promise that ordering.
--
--   (b) A ranking could name a forecast revision the storm does not carry. A row at revision 42
--       of a storm with three forecasts was accepted and served with a 200, and since CHG-027
--       `GET /scenarios/{id}` reports which revisions have an order behind them — so a ranking of
--       a forecast that does not exist is now an answer the screen believes.
--
--   (c) `risk_scores.asset_id references assets (id)` proves an asset exists *somewhere* and
--       never that it belongs to **this** storm. CHG-019 recorded this instance as knowingly
--       unfixed — "rewriting a fourth table inside a TASK-005 remediation would be scope this
--       task does not have" — and it is closed here because this migration rebuilds the table
--       anyway and `assets (id, scenario_id)` has been unique since 008.
--
-- **(b) is a trigger and not a foreign key, and the reason is evidence rather than preference.**
-- `foreign key (scenario_id, forecast_revision) references scenario_forecast_revisions (…)` is
-- the constraint the review named and it was written, run, and withdrawn:
--
--   * `on delete cascade` hands `scenario_forecast_revisions` the power to delete rankings, and
--     010's down migration drops that table. Rolling 010 back therefore **destroys every stored
--     ranking in the database** — a rollback that silently empties the one table AC-005 exists to
--     protect, arriving by way of an ops procedure.
--   * `on delete restrict` instead of cascade turns §7.2's scenario delete into an integrity
--     error, because a scenario reaches `risk_scores` by two paths and SQLite does not define
--     which cascade it applies first. That is CHG-024's argument, unchanged.
--   * And the key cannot be satisfied by data that already exists after a 010 rollback: the
--     rankings survive, the forecast times do not, and there is no honest `valid_time` left
--     anywhere in the database for a revision above 0. The rebuild would abort, or it would have
--     to invent a forecast time from a computation time — a fabricated fact on the column BR-003
--     puts an age beside.
--
-- A `before insert` trigger is the narrower statement and the true one: **what may be written**.
-- It refuses the row the review demonstrated, it adds no delete path to this table, and it
-- leaves rows written before the rule alone rather than making a rollback unrunnable. The cost is
-- recorded rather than implied away: it does not guarantee that an orphan can never *exist*, only
-- that none can be *created*, so deleting a revision row directly leaves its rankings behind.
--
-- BOTH decision_records TRIGGERS ARE RE-ASSERTED AT THE END OF THIS FILE (ADR-004, BR-004).
-- Neither is dropped, disabled or recreated here.

begin;

-- 1. The guards come off first. They are recreated at the end against the rebuilt table, so
--    there is no window in this transaction where a caller could reach an unguarded one.
drop trigger if exists risk_scores_no_update;
drop trigger if exists risk_scores_no_delete;
drop trigger if exists risk_scores_names_a_forecast;

-- 2. risk_scores, rebuilt. SQLite cannot add a foreign key to an existing table, so the table is
--    recreated and copied — the standard rebuild, the same one 008 did for `damage_reports`, and
--    safe here because nothing references `risk_scores`. Every column, check and unique
--    constraint from 005 is carried over unchanged; only the asset key is new.
create table risk_scores_new (
    id                 text primary key,
    scenario_id        text not null references scenarios (id) on delete cascade,
    asset_id           text not null,
    forecast_revision  integer not null,
    score              real,                  -- null for an UNSCORED asset (FTEST-004): it is
                                              --   in the ranking, not ranked, and never low
    band               text
                       check (band is null or band in ('High', 'Medium', 'Low')),
    rank               integer,
    reasons            text not null,         -- json
    unscored_reason    text,
    weight_set_version text not null,         -- CHG-014 / TASK-003 done criterion 5: a later
                                              --   recalibration must not silently rewrite
                                              --   history
    computed_at        text not null,

    check (json_array_length(reasons) >= 1 or score is null),
                                              -- BR-002, the core subdomain's rule: the store
                                              --   refuses a rank that carries no reasons
    check (score is not null or unscored_reason is not null),
                                              -- FTEST-004: an asset with no score must say why.
                                              --   Silence must never be readable as safety
    unique (scenario_id, asset_id, forecast_revision),
                                              -- REQ-F-004 / AC-005: a re-run cannot produce two
                                              --   rankings for one revision

    foreign key (asset_id, scenario_id)
        references assets (id, scenario_id) on delete cascade
                                              -- CHG-028(c) / CHG-019's remaining instance.
                                              --   Membership of THIS storm, not existence
                                              --   somewhere. `on delete cascade` matches what
                                              --   005 already had and what §7 specifies
);

insert into risk_scores_new
    (id, scenario_id, asset_id, forecast_revision, score, band, rank, reasons, unscored_reason,
     weight_set_version, computed_at)
select id, scenario_id, asset_id, forecast_revision, score, band, rank, reasons, unscored_reason,
       weight_set_version, computed_at
from risk_scores;

drop table risk_scores;
alter table risk_scores_new rename to risk_scores;

create index risk_scores_ranking on risk_scores (scenario_id, forecast_revision, rank);

-- 3. CHG-026, re-asserted against the rebuilt table. A stored ranking is never rewritten.
create trigger risk_scores_no_update
before update on risk_scores
begin
    select raise(abort, 'a stored ranking is never rewritten; a forecast change writes a new revision (REQ-F-004, AC-005)');
end;

-- 4. CHG-028(a). The other half of *never rewrites n*, and the `when` clause is the whole design:
--    true of a direct `delete from risk_scores …`, false inside either cascade that reaches this
--    table, because the parent has already gone by the time the trigger is consulted.
create trigger risk_scores_no_delete
before delete on risk_scores
when exists (select 1 from scenarios where id = old.scenario_id)
 and exists (select 1 from assets where id = old.asset_id)
begin
    select raise(abort, 'a stored ranking is never rewritten; delete-and-reinsert is not a re-rank (REQ-F-004, AC-005)');
end;

-- 5. CHG-028(b). A ranking is a ranking OF one of this storm's own forecasts.
create trigger risk_scores_names_a_forecast
before insert on risk_scores
when not exists (
    select 1 from scenario_forecast_revisions
    where scenario_id = new.scenario_id
      and forecast_revision = new.forecast_revision
)
begin
    select raise(abort, 'a ranking must name a forecast revision this storm carries (REQ-F-004, CHG-025)');
end;

commit;

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
