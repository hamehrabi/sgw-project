-- 019 — the table CHG-015 decided and nothing built, and the findings that used to vanish
-- (CHG-046, CHG-047).
--
-- `security_log`: sign-in, sign-out, refused upload, permission denial. CHG-015's reasoning
-- holds — a refused upload is an access-control event, not a decision, so it must not be in
-- `decision_records` and must not need a `scenario_id`. It is NOT append-only by trigger,
-- deliberately: ADR-004's guarantee is about the regulatory record, and extending trigger
-- machinery to a second table dilutes what FF-004 proves about the first.
--
-- `data_findings`: the seven defect rules run at load, and their findings went to the log and
-- the upload response and nowhere else — so the data-quality screen could only exist in the
-- seconds after an upload. Written in the same transaction as the scenario; read forever.

create table security_log (
    id            text primary key,
    actor_user_id text,                       -- null when nobody was signed in — a refused
                                              --   sign-in has no actor to name
    event         text not null
                  check (event in ('sign_in', 'sign_out', 'upload_refused',
                                   'permission_denied', 'password_changed')),
    detail        text not null,              -- plain words; never a credential, never a
                                              --   session value (CON-003, Q-007)
    occurred_at   text not null,
    seq           integer not null unique     -- the order IS the history (CHG-018): this
                                              --   clock cannot separate two rows in 15.6 ms
);

create index security_log_recent on security_log (seq desc);

create table data_findings (
    id           text primary key,
    scenario_id  text not null references scenarios (id) on delete cascade,
    defect       integer not null
                 check (defect between 1 and 7 or defect = 0),
                                              -- 1..7 are `data-and-integration-spec.md` §4's
                                              --   rows; 0 is the bonus class (an unrecognised
                                              --   flood zone is real and is none of the seven)
    code         text not null,
    subject      text not null,               -- the row it traces to — a flag nobody can
                                              --   trace is a warning nobody can act on
    message      text not null,               -- plain words, shaped at load
    affected_file text not null,              -- read from the parse result, never hard-coded:
                                              --   defect 3 lives in whichever file carried
                                              --   the gusts
    needs_decision integer not null default 0,
                                              -- CHG-047's screen rule: at most three of these
                                              --   render as actions; the rest collapse
    resolution   text,                        -- what the reviewing human chose, if anything
    resolved_by  text references users (id),
    resolved_at  text,
    seq          integer not null,

    check ((resolution is null) = (resolved_by is null)
           and (resolution is null) = (resolved_at is null)),
                                              -- a resolution is never anonymous and never
                                              --   undated — half a record is worse than none
    unique (scenario_id, seq)
);

create index data_findings_by_scenario on data_findings (scenario_id, needs_decision, seq);

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
