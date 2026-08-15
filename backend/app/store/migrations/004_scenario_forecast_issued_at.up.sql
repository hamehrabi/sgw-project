-- 004 — scenarios.forecast_issued_at (TASK-002, CHG-013)
--
-- REQ-NF-003(a) states the age of the data on every screen, measured from the manifest's
-- forecast_issued_at. The loader has always parsed it; nothing stored it, so the age it is
-- measured from did not survive the load.
--
-- Added NULLABLE, per database-design.md §8's standing rule: a new required field is added
-- nullable, backfilled, then made required — never required in one step. There is nothing to
-- backfill yet (no scenario predates this), and a scenario with no issue time reports an
-- unknown age rather than a false one.

alter table scenarios add column forecast_issued_at text;
