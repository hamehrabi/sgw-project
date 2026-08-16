-- 023 — rank movement is real, and stored (CHG-044).
--
-- The "Since you last looked" strip is the genuine diff between two DELIVERED rankings —
-- revision n against revision n-1, read out of stored risk_scores rows when a forecast
-- change is applied. Never a second scoring pass: a pass that exists only to decorate a
-- strip would put arrows beside the table that disagree with the ranks they sit next to,
-- and would need an exception to FF-005's "one recommendation row per delivered ranking".
--
-- At revision 0 this table is empty for that storm and the screen says so plainly —
-- "first ranking for this storm, nothing to compare yet" — because there is no earlier
-- order, and inventing one is the faked delta the client's prompt forbids by name.
--
-- Rows are appended per revision and never rewritten — the same read stability §6
-- requires and FF-003 drives against every screen.

create table rank_movement (
    scenario_id       text not null references scenarios (id) on delete cascade,
    forecast_revision integer not null,       -- the revision this movement leads TO
    asset_id          text not null,
    previous_rank     integer,                -- null: unranked in the earlier pass
    current_rank      integer,                -- null: unranked now (unscored is not "safe")
    band              text
                      check (band is null or band in ('High', 'Medium', 'Low')),
    reason_factor     text not null,          -- the factor whose contribution grew most —
                                              --   derived from the same arithmetic as the
                                              --   two scores, never authored (BR-002's shape)
    reason_detail     text not null,          -- that factor's plain-words sentence
    previous_label    text not null,          -- what the earlier pass WAS, said honestly:
                                              --   'the 48-hour window' at load, the previous
                                              --   revision's valid time after an apply
    computed_at       text not null,

    unique (scenario_id, forecast_revision, asset_id)
);

create index rank_movement_read on rank_movement (scenario_id, forecast_revision);

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
