-- 025 — a design basis the manifest states per dialect type is stored per asset
-- (CHG-056).
--
-- The client's dataset types its assets seven ways and states a design basis for each;
-- our scoring categories are four. `Distribution` is built to 90 mph and `Transmission
-- Line` to 140, both land in category `line`, and one per-category number would misapply
-- the utility's own basis to half its lines. So the basis is resolved AT LOAD, from the
-- manifest, per asset — and stored, because a re-rank must use the basis the storm was
-- loaded with (§6, the same reason design_references landed on scenarios in 024).
--
-- Nullable: absent means "the manifest stated none for this asset's type", and the
-- scorer falls through to the scenario-level block (024) and then CHG-014's sourced
-- table — supplied beats stated-per-category beats engineering-standard, never a guess.

alter table assets add column design_gust_mph real
    check (design_gust_mph is null or design_gust_mph > 0);
alter table assets add column service_life_years real
    check (service_life_years is null or service_life_years > 0);

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
