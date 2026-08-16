-- 022 — the manifest's service areas stored, and the staging plan recorded (CHG-049).
--
-- `service_areas[]` arrived with CHG-011 and was parsed and never stored, which CHG-017
-- noted and routed around. The staging panel needs the areas as depots, so they are stored
-- now — at load, in the scenario's transaction, exactly as the forecasts are (CHG-025's
-- reasoning: a storm never exists without them and half a list is not a state).
--
-- `crew_staging` is a record and never an action (BR-001): counts per depot that a person
-- chose while looking at one revision's ranking. No crew is moved, no roster is touched,
-- no message leaves the platform. It is its own table for CHG-048's structural reason —
-- the audit table's `kind` alphabet is frozen — and CHG-015's line: a staging count is an
-- operational note, not a decision about a recommendation. Appended, never rewritten; the
-- latest row per scenario is the plan.

create table scenario_service_areas (
    scenario_id     text not null references scenarios (id) on delete cascade,
    service_area_id text not null,
    name            text,                     -- the manifest may name it; the id stands in
                                              --   when it does not
    customer_count  integer not null
                    check (customer_count >= 0),
    primary key (scenario_id, service_area_id)
);

create table crew_staging (
    id                text primary key,
    scenario_id       text not null references scenarios (id) on delete cascade,
    forecast_revision integer not null,       -- the ranking the person was reading when they
                                              --   chose these counts — a plan is a decision
                                              --   about a list (BR-001)
    depots            text not null,          -- json: [{service_area_id, crews}]
    actor_user_id     text not null references users (id),
                                              -- never anonymous: it is somebody's plan
    created_at        text not null,
    seq               integer not null,

    check (json_valid(depots) and json_array_length(depots) >= 1),
    unique (scenario_id, seq)
);

create index crew_staging_latest on crew_staging (scenario_id, seq desc);

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
