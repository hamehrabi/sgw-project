-- 010 down.
--
-- Back to 009's shape. Rolling this back reinstates two defects knowingly, and both are worth
-- saying out loud rather than leaving to be discovered:
--
--   * The forecast series is gone, so a storm has one forecast again and REQ-F-004 has nothing
--     to re-rank against. `POST /scenarios/{id}/forecast-revisions` answers 409 for every
--     storm, which is at least the honest failure.
--   * `risk_scores` becomes rewritable again, so AC-005's "the previous order remains
--     retrievable" goes back to resting on nothing but the absence of an `UPDATE` statement in
--     the application.
--
-- No table is rebuilt, so no data outside these two tables is touched. `assets.wind_gust_mph`
-- still carries revision 0's gust — it was never moved out, only joined to — which is what
-- makes this rollback safe for the joined asset view and for every revision-0 ranking.
--
-- **The decision_records triggers are not touched here**: 010 did not create them, it
-- re-asserted them, and a down migration that removed BR-004's enforcement as a side effect of
-- rolling back a forecast table is exactly the failure ADR-004 exists to prevent.

begin;

drop trigger if exists risk_scores_no_update;

drop table if exists scenario_forecast_cells;
drop table if exists scenario_forecast_revisions;

commit;
