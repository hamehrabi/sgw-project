-- 005 — risk_scores (TASK-003)
--
-- decision_records still does not exist (TASK-004). Nothing to re-assert.

create table risk_scores (
    id                 text primary key,
    scenario_id        text not null references scenarios (id) on delete cascade,
    asset_id           text not null references assets (id) on delete cascade,
    forecast_revision  integer not null,
    score              real,                  -- null for an UNSCORED asset (FTEST-004): it is
                                              --   in the ranking, not ranked, and never low
    band               text
                       check (band is null or band in ('High', 'Medium', 'Low')),
    rank               integer,
    reasons            text not null,         -- json
    unscored_reason    text,
    weight_set_version text not null,         -- CHG-014 / TASK-003 done criterion 5: a later
                                              --   recalibration must not silently rewrite
                                              --   history. A rank read next month still says
                                              --   which numbers produced it
    computed_at        text not null,

    check (json_array_length(reasons) >= 1 or score is null),
                                              -- BR-002, the core subdomain's rule: the store
                                              --   refuses a rank that carries no reasons. An
                                              --   UNSCORED row has no score to explain, and
                                              --   the next constraint makes it explain itself
    check (score is not null or unscored_reason is not null),
                                              -- FTEST-004: an asset with no score must say why.
                                              --   Silence must never be readable as safety
    unique (scenario_id, asset_id, forecast_revision)
                                              -- REQ-F-004 / AC-005: re-ranking writes a new
                                              --   revision and the previous order stays
                                              --   retrievable
);

create index risk_scores_ranking on risk_scores (scenario_id, forecast_revision, rank);
