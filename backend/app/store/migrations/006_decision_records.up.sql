-- 006 — decision_records, and the two triggers that are BR-004's only enforcement (TASK-004)
--
-- READ THIS BEFORE WRITING ANY LATER MIGRATION.
--
-- Append-only cannot be expressed as a check constraint, so it is enforced by the store
-- refusing the statement: BEFORE UPDATE and BEFORE DELETE, each aborting (ADR-004, CHG-002).
-- **Every migration from here on must end with both triggers present.** A migration that
-- drops one removes the entire enforcement of BR-004 and no functional test would notice —
-- which is why FF-004 attempts a real UPDATE and requires the refusal, rather than inspecting
-- the schema.
--
-- This was originally a role grant: the application role holding INSERT and SELECT and neither
-- UPDATE nor DELETE. ADR-002 chose an embedded store with no role system, so the mechanism
-- changed. One property did not survive and is recorded rather than glossed: a grant separates
-- the power to change the rule from the power to change the data; a trigger does not, because
-- anyone who can run a migration can drop it. Removing either is a change requiring a
-- superseding ADR.

create table decision_records (
    id            text primary key,
    scenario_id   text not null references scenarios (id),
                                              -- deliberately NOT "on delete cascade": an audit
                                              --   row must outlive the thing it describes
    occurred_at   text not null,
    actor_user_id text references users (id),
                                              -- null when the actor is the system making a
                                              --   recommendation rather than a person deciding
    kind          text not null
                  check (kind in ('recommendation', 'accept', 'change',
                                  'reject', 'dismiss', 'placement')),
    subject_type  text not null,
    subject_id    text not null,
                                              -- referenced by type and id rather than by
                                              --   foreign key, on purpose: a foreign key would
                                              --   either block deleting a scenario or cascade
                                              --   away the record of what was decided about it
    payload       text not null,              -- json

    check (kind = 'recommendation' or actor_user_id is not null)
                                              -- BR-001: a decision is always somebody's. Only
                                              --   the system's own recommendation is actorless
);

create index decision_records_by_scenario on decision_records (scenario_id, occurred_at);
create index decision_records_by_subject on decision_records (subject_type, subject_id);

-- BR-004. These two are the enforcement. Nothing else is.
create trigger decision_records_no_update
before update on decision_records
begin
    select raise(abort, 'decision_records is append-only (BR-004, ADR-004)');
end;

create trigger decision_records_no_delete
before delete on decision_records
begin
    select raise(abort, 'decision_records is append-only (BR-004, ADR-004)');
end;
