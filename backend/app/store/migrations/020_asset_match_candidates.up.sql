-- 020 — the withheld merge, kept instead of thrown away (CHG-048).
--
-- `loader/matching.py` withholds a merge where type and position agree and the name does not,
-- because a wrong merge deletes an asset from the ranking invisibly while a wrong split costs
-- a person ten seconds in a queue. This is the queue. Until now `assets.match_status`
-- recorded THAT a record needs review and nothing about what it would have been merged with,
-- so the person the loader deferred to had nothing to look at.
--
-- The resolution lives on this row — actor, decision, time — and not in `decision_records`:
-- the audit table's `kind` alphabet is frozen in a check constraint, CHG-036 ruled out the
-- rebuild that could widen it, and CHG-015's line governs anyway — deciding two source rows
-- describe one asset is a decision about data identity, not about a recommendation.

create table asset_match_candidates (
    id              text primary key,
    scenario_id     text not null references scenarios (id) on delete cascade,
    asset_id        text not null,
    scenario_check  text not null,            -- mirrors scenario_id so the composite key
                                              --   below can hold CHG-019's rule: existence is
                                              --   not membership, and a candidate must belong
                                              --   to the storm it names
    map_record      text not null,            -- json: the side already in the registry
    candidate_record text not null,           -- json: the side the merge was withheld from
    confidence      text not null
                    check (confidence in ('high', 'moderate')),
                                              -- words, never a percentage: the rule is a
                                              --   threshold on position and a name comparison,
                                              --   and `87%` would invent a precision the
                                              --   arithmetic does not have
    resolution      text not null default 'pending'
                    check (resolution in ('pending', 'match', 'not_match')),
    resolved_by     text references users (id),
    resolved_at     text,
    seq             integer not null,

    check ((resolution = 'pending') = (resolved_by is null)
           and (resolution = 'pending') = (resolved_at is null)),
                                              -- a resolution is never anonymous and never
                                              --   undated; pending is never either
    check (scenario_check = scenario_id),
    unique (scenario_id, seq),
    foreign key (asset_id, scenario_check) references assets (id, scenario_id)
);

create index asset_match_candidates_queue
    on asset_match_candidates (scenario_id, resolution, seq);

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
