-- 026 — a per-asset summary is phrased once and stored (CHG-059).
--
-- The cache is the constraint, not a code path: `unique (scenario_id, asset_id,
-- forecast_revision)` means a repeat request can only ever find the stored row, and a
-- re-rank gets a fresh summary for the new revision rather than a stale one relabelled.
--
-- The composite foreign key carries the scoping root (CHG-019's rule): `references
-- assets (id)` alone would prove the asset exists, never that it is in *this* storm.

create table asset_summaries (
    id                text primary key,
    scenario_id       text    not null references scenarios (id) on delete cascade,
    asset_id          text    not null,
    forecast_revision integer not null check (forecast_revision >= 0),
    text              text    not null check (length(text) > 0),
    -- Which path produced it: the model's draft survived verification, or the figures
    -- wrote it themselves. The reader is always told which.
    label             text    not null check (
        label in ('Phrased from computed factors', 'Assembled from computed factors')
    ),
    source_figures    text    not null,
    verification      text    not null,
    created_at        text    not null,
    created_by        text    not null references users (id),
    unique (scenario_id, asset_id, forecast_revision),
    foreign key (asset_id, scenario_id) references assets (id, scenario_id)
        on delete cascade
);

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
