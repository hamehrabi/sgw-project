-- 006 down.
--
-- The triggers must be dropped before the table, and dropping them is the one operation the
-- migration checklist treats as requiring a superseding ADR. It is written here because
-- database-design.md §8 requires every migration to ship a down — not because running it is
-- ever routine.

drop trigger if exists decision_records_no_delete;
drop trigger if exists decision_records_no_update;
drop index if exists decision_records_by_subject;
drop index if exists decision_records_by_scenario;
drop table if exists decision_records;
