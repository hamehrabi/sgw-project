-- 017 — the second role is named `operator`, and a temporary password behaves like one
-- (CHG-045, CHG-053).
--
-- `user` was never a role; it was the absence of one. Every other document calls the person
-- an operator, the client's build prompt freezes `admin | operator` in the type system, and
-- a label that disagrees with the value behind it is a second definition — a sentence this
-- register has now paid for five times (CHG-023, CHG-037, CHG-039).
--
-- CHG-004's admin-set temporary password gains the two properties that make it temporary:
-- it expires (`temp_password_expires_at`, set from TEMP_PASSWORD_EXPIRY_HOURS — a lifetime,
-- so read from the environment and never defaulted, per ADR-006), and its holder must change
-- it before any other route answers (`must_change_password`, enforced by the same guard that
-- enforces the roles rather than by a redirect a browser could skip).
--
-- The role lives in a check constraint, and SQLite cannot edit one: this is a table rebuild.
-- `users` carries no triggers, so nothing here is near ADR-004's ground — but `sessions`
-- references `users (id)`, so foreign keys are off for exactly the width of the rebuild.
-- `create → copy → drop old → rename` rather than `rename old first`: a rename rewrites the
-- FK clauses of every referencing table to follow it, and `sessions` must keep saying
-- `references users`.

pragma foreign_keys = off;

create table users_new (
    id                       text primary key,
    name                     text not null,
    email                    text not null unique,
    password_hash            text not null,
    role                     text not null
                             check (role in ('admin', 'operator')),
                                              -- REQ-R-001: exactly two roles, renamed by
                                              --   CHG-045. A third arrives by migration only
    created_at               text not null,
    must_change_password     integer not null default 0,
                                              -- CHG-053: 1 while the password is an
                                              --   admin-set temporary one. Every route but
                                              --   the password change refuses while set
    temp_password_expires_at text             -- CHG-053: single-use window. Null for a
                                              --   password its holder chose
);

insert into users_new (id, name, email, password_hash, role, created_at,
                       must_change_password, temp_password_expires_at)
select id, name, email, password_hash,
       case role when 'user' then 'operator' else role end,
       created_at, 0, null
from users;

drop table users;
alter table users_new rename to users;

pragma foreign_keys = on;

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
