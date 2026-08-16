-- 010 — the forecast series a re-rank is computed from, and *never rewrites n* (TASK-006)
--
-- Two change entries, both raised rather than assumed and both left **proposed**:
--
--   CHG-025 a scenario's forecast series had nowhere to live, and nothing decided what
--           "the scenario's next forecast change" is.
--     `data-and-integration-spec.md` §1 gives `weather.csv` a `valid_time` column and
--     `technical-spec.md` sizes the fixture at "220 assets, ~5,000 forecast rows" — far more
--     rows than one forecast needs — so REQ-F-004's "a changed forecast INSIDE the prepared
--     scenario" is already in the file. The loader took ONE gust per grid cell and discarded
--     every other row, and `assets` holds ONE `wind_gust_mph`, so there was nothing to re-rank
--     against. That is `AGENT.md`'s third lessons row again: a described state with nowhere in
--     the schema to keep it.
--
--     Decided: a forecast revision is one distinct `valid_time` among the cell-level rows of
--     `weather.csv`, numbered from 0 in chronological order, and each revision is a COMPLETE
--     grid — a cell with no row at that time keeps the value it was last issued, carried
--     forward once at load. Carrying forward is a parse-time decision about what a revision
--     contains; it is NOT the read-time fallback `technical-spec.md` §7.3 forbids, and the
--     cell keeps the `valid_time` it was ISSUED at so a carried value cannot claim to be
--     current (BR-003).
--
--   CHG-026 nothing stopped an earlier revision being rewritten.
--     AC-005's second half is "the previous order remains retrievable", and `risk_scores`
--     had `unique (scenario_id, asset_id, forecast_revision)` — which refuses a SECOND row for
--     a revision and says nothing at all about an `UPDATE` to the first. The rule lived in the
--     absence of a statement, which is the shape ADR-002 exists to refuse: "never implement a
--     check in the service layer that the store could refuse". A ranking is written whole and
--     read; nothing in this application has ever updated one. The trigger at the end of this
--     file makes that a property of the database.
--
-- BOTH decision_records TRIGGERS ARE RE-ASSERTED AT THE END OF THIS FILE (ADR-004, BR-004).
-- Neither is dropped, disabled or recreated here.

begin;

-- 1. One row per revision. `valid_time` lives HERE and not only on the cells, because "one
--    revision is one forecast time" is a rule the schema can hold: the primary key refuses a
--    second row for a revision, and `unique (scenario_id, valid_time)` refuses two revisions
--    claiming one forecast time — which is what would happen if the loader ever stopped
--    collapsing duplicate times.
create table scenario_forecast_revisions (
    scenario_id       text not null references scenarios (id) on delete cascade,
    forecast_revision integer not null
                      check (forecast_revision >= 0),
                                              -- revision 0 is the forecast the storm was
                                              --   loaded at; there is no revision before it
    valid_time        text not null,
    created_at        text not null,

    primary key (scenario_id, forecast_revision),
    unique (scenario_id, valid_time)
);

-- 2. One row per grid cell per revision. `valid_time` here is when THIS VALUE was issued,
--    which is not always the revision's own time: a cell with no new row keeps the value it
--    last had, and BR-003 requires the age of a value to travel with it. A six-hour-old gust
--    presented as current is the kind of quiet wrongness REQ-NF-003 exists to prevent.
--
--    The foreign key is composite and carries the scenario, which is CHG-019's lesson applied
--    before it is needed rather than after: `references scenario_forecast_revisions
--    (forecast_revision)` alone would prove a revision number exists SOMEWHERE, never that it
--    belongs to this storm, and two storms blended into one ranking would look entirely
--    plausible.
create table scenario_forecast_cells (
    scenario_id       text not null,
    forecast_revision integer not null,
    grid_cell_id      text not null,
    valid_time        text not null,
    wind_gust_mph     real,                   -- nullable: a cell the file carries with no gust
                                              --   makes its assets UNSCORED, never scored low
    rainfall_in       real,

    primary key (scenario_id, forecast_revision, grid_cell_id),
    foreign key (scenario_id, forecast_revision)
        references scenario_forecast_revisions (scenario_id, forecast_revision)
        on delete cascade
);

-- 3. Backfill revision 0 for every storm already loaded, from the rows the loader wrote onto
--    `assets`. Derived entirely from stored data — no file is reopened, because
--    `technical-spec.md` §6 serves every read from stored rows and CHG-013 already decided
--    that a lost source file must leave the picture correct. A storm whose assets carry no
--    grid cell gets no revision row and therefore no forecast to re-rank against, which is the
--    honest answer rather than an invented one.
insert into scenario_forecast_revisions (scenario_id, forecast_revision, valid_time, created_at)
select s.id, 0, coalesce(s.forecast_issued_at, s.loaded_at), s.loaded_at
from scenarios s
where exists (
    select 1 from assets a where a.scenario_id = s.id and a.grid_cell_id is not null
);

insert into scenario_forecast_cells
    (scenario_id, forecast_revision, grid_cell_id, valid_time, wind_gust_mph, rainfall_in)
select a.scenario_id, 0, a.grid_cell_id,
       coalesce(s.forecast_issued_at, s.loaded_at),
       max(a.wind_gust_mph), max(a.rainfall_in)
from assets a
join scenarios s on s.id = a.scenario_id
where a.grid_cell_id is not null
group by a.scenario_id, a.grid_cell_id;

-- 4. CHG-026. A stored ranking is never rewritten.
--
--    Only UPDATE. There is deliberately no BEFORE DELETE twin: `risk_scores` is cascade-deleted
--    with its scenario and with its assets (§7.2's "delete or replace a scenario"), and a
--    delete guard would turn a supported operation into an integrity error. Deleting a whole
--    storm is not the failure AC-005 is about — rewriting the order a decision was made
--    against, while leaving the storm in place, is.
create trigger if not exists risk_scores_no_update
before update on risk_scores
begin
    select raise(abort, 'a stored ranking is never rewritten; a forecast change writes a new revision (REQ-F-004, AC-005)');
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
