-- 027 — assign, restore, reopen: appended, never rewritten (CHG-063).
--
-- The dispatch worklist's three actions are records about a job — BR-001 stands, nothing
-- is dispatched — and a record of who moved a job matters exactly as long as it cannot be
-- edited afterwards. So this table gets the decision record's walls: its own BEFORE
-- UPDATE and BEFORE DELETE triggers, a per-scenario monotonic seq (CHG-018 — a timestamp
-- is not a total order), and a composite scope so an action cannot name another storm's
-- job (CHG-019's rule).

create table dispatch_actions (
    id            text primary key,
    scenario_id   text not null references scenarios (id) on delete cascade,
    repair_job_id text not null references repair_jobs (id) on delete cascade,
    action        text not null check (action in ('assign', 'restore', 'reopen')),
    -- The crew label people chose. Present exactly when the action is an assignment.
    crew          text check (
        (action = 'assign') = (crew is not null)
        and (crew is null or length(crew) between 1 and 120)
    ),
    actor_user_id text not null references users (id),
    occurred_at   text not null,
    seq           integer not null,
    unique (scenario_id, seq)
);

create trigger dispatch_actions_no_update
before update on dispatch_actions
begin
    select raise(abort, 'dispatch_actions is append-only (CHG-063)');
end;

create trigger dispatch_actions_no_delete
before delete on dispatch_actions
begin
    select raise(abort, 'dispatch_actions is append-only (CHG-063)');
end;

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
