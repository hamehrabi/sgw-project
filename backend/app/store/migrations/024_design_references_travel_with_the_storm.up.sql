-- 024 — the utility's own design basis, stored with the storm (CHG-051).
--
-- CHG-014 resolved two reference values ADR-007 compares against but never supplies as
-- per-type engineering constants carrying their sources — and named calibration with the
-- client as the exit condition. The manifest's `design_references` block IS that
-- calibration arriving: the scorer reads this first and falls back to CHG-014's table,
-- so a manifest that omits it scores exactly as before.
--
-- Stored on the scenario because it is a fact about the prepared file, like the forecast
-- series — two storms may carry two different design bases, and a re-rank must use the
-- one its storm was loaded with, not whichever manifest arrived last.

alter table scenarios add column design_references text;

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
