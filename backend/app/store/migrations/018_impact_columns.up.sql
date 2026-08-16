-- 018 — the two facts the repair queue's order is derived from (CHG-050).
--
-- The queue is ordered by IMPACT and never by a risk score — `priority_rank` stays null,
-- the scorer is not consulted, and this migration is what makes that order possible without
-- one: whether the damaged asset is a critical facility, and how many customers the report
-- accounts for. Both are facts about what has occurred, not predictions about what might.
--
-- `is_critical_facility` is CON-003's one explicitly permitted boolean about an asset. It has
-- been a column in the client's own file format since the beginning and was never stored.

alter table assets add column is_critical_facility integer not null default 0;

alter table damage_reports add column customers_out integer
    check (customers_out is null or customers_out >= 0);
                                              -- null means the caller did not say — which is
                                              --   not the same claim as zero out (defect 4's
                                              --   lesson, at the reporting boundary)

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
