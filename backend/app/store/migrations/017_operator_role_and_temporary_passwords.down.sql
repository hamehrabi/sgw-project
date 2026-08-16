-- 017 down — restore the `user` role name and drop the temporary-password columns.

pragma foreign_keys = off;

create table users_old (
    id            text primary key,
    name          text not null,
    email         text not null unique,
    password_hash text not null,
    role          text not null
                  check (role in ('admin', 'user')),
    created_at    text not null
);

insert into users_old (id, name, email, password_hash, role, created_at)
select id, name, email, password_hash,
       case role when 'operator' then 'user' else role end,
       created_at
from users;

drop table users;
alter table users_old rename to users;

pragma foreign_keys = on;
