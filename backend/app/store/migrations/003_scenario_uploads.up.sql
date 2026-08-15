-- 003 — scenario_uploads (TASK-002, CHG-012)
--
-- The parse job's own state. It cannot live on the scenario row, because §9.1 requires that a
-- parse failing partway creates no scenario at all — so during the only period anyone is
-- watching, and forever if it fails, there is no scenario to hang it from.
--
-- decision_records still does not exist (TASK-004). Nothing to re-assert.

create table scenario_uploads (
    id            text primary key,           -- §9.5's "stored upload identifier"
    status        text not null
                  check (status in ('uploading', 'parsing', 'ready', 'failed')),
    uploaded_by   text not null references users (id),
    uploaded_at   text not null,
    name          text not null,
    source_note   text not null,
    storage_path  text not null,              -- a GENERATED identifier, never any part of a
                                              --   supplied filename (security-spec §7)
    scenario_id   text references scenarios (id) on delete set null,
    failed_file   text,
    failed_reason text,
    finished_at   text,

    check (status <> 'ready' or scenario_id is not null),
                                              -- a ready upload with no scenario is a success
                                              --   nobody can open
    check (status <> 'failed' or failed_file is not null)
                                              -- REQ-NF-003: a failure that does not name the
                                              --   file is an error page with extra steps
);

create index scenario_uploads_by_user on scenario_uploads (uploaded_by, status);
