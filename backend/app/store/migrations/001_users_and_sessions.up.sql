-- 001 — users and sessions (TASK-001)
--
-- Raw SQL, per ADR-008: a schema-first generator cannot be trusted with the
-- decision_records triggers, so migrations on this project are written by hand.
--
-- decision_records does not exist yet — TASK-004 creates it, with its two append-only
-- triggers. There is therefore nothing for this migration to re-assert. The moment that
-- table exists, every migration after it must end by re-asserting both triggers
-- (ADR-004): they are BR-004's only enforcement, and dropping one is silent.

create table users (
    id            text primary key,
    name          text not null,
    email         text not null unique,          -- one account per address
    password_hash text not null,                 -- never plain text (database-design.md §6)
    role          text not null
                  check (role in ('admin', 'user')),
                                                 -- REQ-R-001: exactly two roles. A third
                                                 --   cannot arrive by accident, only by a
                                                 --   migration
    created_at    text not null
);

-- CHG-008. Required by ADR-003 (a session created, checked and ended server-side),
-- ADR-006 ("a session lookup per request against a local store") and ADR-002 (nothing
-- durable lives in process memory, so a restart is not an incident).
create table sessions (
    id           text primary key,
    token_hash   text not null unique,           -- the session VALUE is never stored (Q-007)
    user_id      text not null references users (id),
    created_at   text not null,                  -- ADR-006: the 12-hour absolute cap
    last_seen_at text not null,                  -- ADR-006: the 240-minute idle limit
    ended_at     text                            -- ADR-003: sign-out ends it in the store
);

create index sessions_user_id on sessions (user_id);
