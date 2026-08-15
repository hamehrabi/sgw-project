-- 002 — scenarios and assets (TASK-002)
--
-- Raw SQL, per ADR-008. decision_records still does not exist (TASK-004 creates it with its
-- two append-only triggers), so there is still nothing for this migration to re-assert.

create table scenarios (
    id                text primary key,
    name              text not null,
    source_note       text not null,          -- which prepared dataset, and where it came from
    loaded_by         text not null references users (id),
    loaded_at         text not null,
    forecast_revision integer not null default 0
                                              -- REQ-F-004: a forecast change increments this
                                              --   rather than overwriting what was ranked
);

create table assets (
    id                    text primary key,
    scenario_id           text not null references scenarios (id) on delete cascade,
    external_ids          text not null,      -- json: the code each source system uses
    type                  text not null
                          check (type in ('substation', 'line', 'plant', 'pump')),
    location              text not null,      -- json
    connections           text,               -- json, optional
    condition             text,
    condition_source      text,
    condition_observed_at text,
    condition_estimated   integer not null default 0,
                                              -- BR-003 display half: an estimated value must
                                              --   render distinctly from a measured one
    grid_cell_id          text,
    wind_gust_mph         real,
    rainfall_in           real,
    install_year          integer,
    flood_zone            text,
    name                  text,
    match_status          text not null
                          check (match_status in ('matched', 'needs_review')),
                                              -- AC-001: records the join could not resolve go
                                              --   to a person, never to a guess
    created_at            text not null,

    check (condition is null
           or (condition_source is not null and condition_observed_at is not null))
                                              -- BR-003: a condition value may not be stored
                                              --   without its source and its age
);

create index assets_scenario_match on assets (scenario_id, match_status);
