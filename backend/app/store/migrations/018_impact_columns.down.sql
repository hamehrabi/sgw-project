-- 018 down — SQLite drops columns directly since 3.35.

alter table assets drop column is_critical_facility;
alter table damage_reports drop column customers_out;
