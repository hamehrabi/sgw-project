-- 002 down. Every migration ships an up and a down (database-design.md §8).

drop index if exists assets_scenario_match;
drop table if exists assets;
drop table if exists scenarios;
