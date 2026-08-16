-- 016 down.
--
-- Restores migration 012's and migration 013's triggers **verbatim**, six-ASCII holes included.
-- A down migration returns the schema to the state the version before it shipped; writing a
-- partial widening here would leave a third state that no migration produced and no test covers.
--
-- ROLLING THIS BACK RE-OPENS BOTH DEFECTS. A crew label of one U+200B and a storm named U+00A0
-- become storable again, and the placement is written into a table BR-004 forbids correcting.
-- Said plainly rather than implied, because `database-design.md` §8 requires every migration to
-- ship a down and does not require running one to be free.
--
-- 016 HAS NO ORDERING CONSTRAINT AGAINST ITS NEIGHBOURS, unlike 011-before-010 and
-- 012-before-011: it creates no table, reads none, and rewrites two triggers whose own
-- dependencies (`risk_scores` for the placement's clause 7, `scenarios` for the identity shape)
-- are the same before and after. It must still be rolled back before 012 and before 013, for
-- the ordinary reason that those two drop the triggers this file replaced.

drop trigger if exists decision_records_placement_shape;

create trigger decision_records_placement_shape
before insert on decision_records
when new.kind = 'placement'
begin
    select raise(abort, 'a placement carries a crew display label of 1 to 120 characters, trimmed and on one line (CON-003, REQ-F-005)')
    where coalesce(
        json_valid(new.payload)
        and json_type(new.payload, '$.crew') = 'text'
        and json_extract(new.payload, '$.crew') = trim(json_extract(new.payload, '$.crew'))
        and length(json_extract(new.payload, '$.crew')) between 1 and 120
        and length(json_extract(new.payload, '$.crew')) = length(
            replace(replace(replace(replace(replace(
                json_extract(new.payload, '$.crew'),
                char(9), ''), char(10), ''), char(11), ''), char(12), ''), char(13), '')),
        0) = 0;

    select raise(abort, 'a placement names at least one asset and no more than 500 (REQ-F-005)')
    where coalesce(
        json_type(new.payload, '$.asset_ids') = 'array'
        and json_array_length(new.payload, '$.asset_ids') >= 1
        and json_array_length(new.payload, '$.asset_ids') <= 500,
        0) = 0;

    select raise(abort, 'a placement names each asset once (REQ-F-005)')
    where json_array_length(new.payload, '$.asset_ids')
          <> (select count(distinct value) from json_each(new.payload, '$.asset_ids'));

    select raise(abort, 'a placement names the forecast revision it was made against (REQ-F-005)')
    where coalesce(json_type(new.payload, '$.forecast_revision') = 'integer', 0) = 0;

    select raise(abort, 'a placement is recorded against the ranking it was made against (REQ-F-005)')
    where new.subject_type <> 'ranking'
       or new.subject_id <> new.scenario_id || ':' || json_extract(new.payload, '$.forecast_revision');

    select raise(abort, 'a placement note is text of up to 2000 characters, or null (REQ-F-005)')
    where coalesce(
        json_type(new.payload, '$.note') = 'null'
        or (json_type(new.payload, '$.note') = 'text'
            and length(json_extract(new.payload, '$.note')) <= 2000),
        0) = 0;

    select raise(abort, 'a placement may name only assets on the ranking it was made against (REQ-F-005)')
    where exists (
        select 1 from json_each(new.payload, '$.asset_ids') as named
        where not exists (
            select 1 from risk_scores rs
            where rs.scenario_id = new.scenario_id
              and rs.asset_id = named.value
              and rs.forecast_revision = json_extract(new.payload, '$.forecast_revision')
        )
    );
end;

drop trigger if exists scenarios_identity_shape;

create trigger scenarios_identity_shape
before insert on scenarios
begin
    select raise(abort, 'a storm is identified by the content it was loaded from: content_key is a 64-character lower-case hexadecimal digest (REQ-F-010, data-and-integration-spec.md 5)')
    where coalesce(
        typeof(new.content_key) = 'text'
        and length(new.content_key) = 64
        and new.content_key not glob '*[^0-9a-f]*',
        0) = 0;

    select raise(abort, 'a storm carries a name of 1 to 200 characters that is not blank, because a name is what somebody picks it out by (REQ-F-010)')
    where coalesce(
        typeof(new.name) = 'text'
        and length(new.name) between 1 and 200
        and length(trim(new.name, ' ' || char(9) || char(10) || char(11) || char(12) || char(13))) >= 1,
        0) = 0;

    select raise(abort, 'a storm carries a source note of 1 to 500 characters saying which prepared dataset it is and where it came from (REQ-F-010, database-design.md 3)')
    where coalesce(
        typeof(new.source_note) = 'text'
        and length(new.source_note) between 1 and 500
        and length(trim(new.source_note, ' ' || char(9) || char(10) || char(11) || char(12) || char(13))) >= 1,
        0) = 0;
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
