-- 001 down. Every migration ships an up and a down (database-design.md §8). Version one
-- holds no production data, so a down is cheap — the rule is set now precisely because it
-- stops being cheap later.

drop index if exists sessions_user_id;
drop table if exists sessions;
drop table if exists users;
