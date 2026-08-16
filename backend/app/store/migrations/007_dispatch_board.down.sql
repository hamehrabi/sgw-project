-- 007 down.
--
-- The two tables and their indexes, and nothing else. **The decision_records triggers are not
-- touched here**: 007 did not create them, it re-asserted them, and a down migration that
-- removed BR-004's enforcement as a side effect of rolling back the dispatch board is exactly
-- the failure ADR-004 and the migration checklist exist to prevent.
--
-- Reports are dropped before jobs: damage_reports.repair_job_id points at repair_jobs.

drop index if exists damage_reports_scenario_status_job;
drop table if exists damage_reports;
drop index if exists repair_jobs_scenario_status;
drop table if exists repair_jobs;
