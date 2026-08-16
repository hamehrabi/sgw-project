-- 016 — the one blank alphabet reaches the three columns CHG-037 did not (TASK-007, TASK-009;
-- remediation of the finding recorded in `review-log.md` on 2026-08-16, at the round that
-- reviewed TASK-007 and TASK-009 for the first time).
--
-- One change entry, raised rather than assumed and left **proposed**: CHG-039. It invents no
-- requirement. CHG-037 already decided *what counts as blank*; this puts that decision on the
-- three columns it did not reach, in the place ADR-002 says it has to live.
--
--   CHG-039  ONE ALPHABET WAS DECIDED AND THREE COLUMNS NEVER GOT IT, AND BOTH DEFECTS WERE
--            LIVE ON AN UNTOUCHED TREE WITH NO MUTATION REQUIRED.
--
--     `POST /api/v1/scenarios/{id}/placements` with a crew of one U+200B ZERO WIDTH SPACE, or
--     one U+FEFF, was answered **201** and that character is what `decision_records.payload`
--     then holds — a placement recorded under a person's name, naming a crew nobody can see, in
--     the one table BR-004 forbids correcting. A correction is a new row, so the invisible one
--     stays in the regulator's artefact for ever.
--
--     `POST /api/v1/scenarios` with a name of one U+00A0 was answered **201** and stored, and
--     `ScenarioSwitcher` — whose entire purpose under REQ-F-010 is letting a person pick one
--     storm out of several — renders that row with no visible label. The same for
--     `source_note`, which §3 requires to say *which prepared dataset this is and where it came
--     from*.
--
--     `'   '` is refused at all three. THE SAME NON-ANSWER WEARING A DIFFERENT WHITESPACE
--     CHARACTER — CHG-023's sentence, for the fourth and fifth time, and the second time it has
--     needed no mutation to find. The reason it keeps recurring is the reason `AGENT.md` gives:
--     a rule that has to be re-derived at each boundary is a rule that will be missed at one.
--     CHG-037 tied three copies of the alphabet together and tied nothing to the columns it did
--     not name, so the next column written reached for its own language's idea of blank again.
--
--     AND THE BROWSER WAS THE STRICT ONE AGAIN, IN BOTH CASES, WHICH IS WHY NOBODY SAW IT.
--     `PlacementForm` and `ScenarioUploadPanel` both used `String.prototype.trim()`. It removes
--     U+00A0 and U+FEFF and does not remove U+200B; Python's `str.strip()` removes U+00A0 and
--     removes neither invisible; SQLite's one-argument `trim()` removes spaces alone. Three
--     languages, three sets, and the strictest sat in the layer ADR-002 says must never hold
--     the rule — so every screen looked correct and only a caller reaching the API met the hole.
--
--     DECLINED, in writing:
--       * *widening `str.strip()` and `trim()` instead of enumerating* — that is the defect. A
--         rule written as *whatever this language calls blank* is three rules, and this
--         migration is the fourth time that sentence has been paid for.
--       * *refusing the characters anywhere in the value rather than at its ends* — a crew
--         called `Nord­team` and a Japanese storm name are legitimate. What is refused is a
--         value made of nothing, never a character.
--       * *fixing only the crew label* — `decision_records` is the worse of the two because it
--         cannot be corrected, but `scenarios.name` is the one on the screen the requirement is
--         about, and leaving it would be the fifth instance waiting to be found.
--       * *a `check` constraint instead of a trigger, on `decision_records`* — it cannot be done
--         without rebuilding the table, which drops both append-only triggers. ADR-004 forbids
--         it and CHG-029 already routed around it.
--
-- BOTH decision_records TRIGGERS ARE RE-ASSERTED AT THE END OF THIS FILE (ADR-004, BR-004).
-- Neither is dropped, disabled or recreated here, and this migration rebuilds no table:
-- `decision_records_placement_shape` and `scenarios_identity_shape` are ordinary triggers, and
-- replacing one of those is not what the migration checklist treats as requiring a superseding
-- ADR. Nothing in this file touches `decision_records_no_update` or `decision_records_no_delete`
-- except to state them again.
--
-- THE ALPHABET IS THE SAME 31 CODEPOINTS 015 WROTE, IN THE SAME ORDER, AND
-- `test_one_alphabet_decides_what_is_blank_in_every_layer` is what fails when a copy moves.
-- It is repeated as a literal rather than built by the loader for the reason ADR-008 gives for
-- hand-written migrations: a migration is the schema's history and has to be readable as raw
-- SQL by somebody who is not running Python.

-- 1. The crew label on a placement (TASK-007, migration 012 clause 1).
--
--    The old clause was `crew = trim(crew)` — spaces only — beside a five-way `replace` chain
--    that removed char(9)…char(13). Between them they refused a label of one space and a label
--    of one tab, and accepted a label of one zero-width space. The `= trim(crew, <alphabet>)`
--    form does both jobs at once: it refuses a padded label AND, because trimming an all-blank
--    label yields `''` which is not equal to it, refuses a label made of nothing. The `not glob`
--    keeps the *on one line* half — a control character in the middle of a label is still
--    refused, and the space is left out of the character class deliberately, because a crew
--    label may legitimately contain one.
drop trigger if exists decision_records_placement_shape;

create trigger decision_records_placement_shape
before insert on decision_records
when new.kind = 'placement'
begin
    select raise(abort, 'a placement carries a crew display label of 1 to 120 characters, trimmed and on one line (CON-003, REQ-F-005)')
    where coalesce(
        json_valid(new.payload)
        and json_type(new.payload, '$.crew') = 'text'
        and json_extract(new.payload, '$.crew')
            = trim(json_extract(new.payload, '$.crew'),
                   char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760,
                        8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200,
                        8201, 8202, 8203, 8232, 8233, 8239, 8287, 12288, 65279))
        and length(json_extract(new.payload, '$.crew')) between 1 and 120
        and json_extract(new.payload, '$.crew')
            not glob '*[' || char(9, 10, 11, 12, 13, 28, 29, 30, 31, 133, 160, 5760,
                                  8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200,
                                  8201, 8202, 8203, 8232, 8233, 8239, 8287, 12288, 65279)
                          || ']*',
        0) = 0;

    -- Clauses 2 to 7 are migration 012's, unchanged, restated because SQLite has no way to
    -- alter one statement of a trigger. Changing any of them here would be smuggling a change
    -- inside a remediation for something else, which is CHG-024's rule.
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

-- 2. A storm's name and source note (TASK-009, migration 013 clauses b and c).
--
--    Clause (a), the content key, is unchanged: a 64-character lower-case hex digest cannot
--    contain a blank of any alphabet, so widening it would be a clause that cannot fail, which
--    is the thing this register exists to catch.
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
        and length(trim(new.name,
                        char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760,
                             8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200,
                             8201, 8202, 8203, 8232, 8233, 8239, 8287, 12288, 65279))) >= 1,
        0) = 0;

    select raise(abort, 'a storm carries a source note of 1 to 500 characters saying which prepared dataset it is and where it came from (REQ-F-010, database-design.md 3)')
    where coalesce(
        typeof(new.source_note) = 'text'
        and length(new.source_note) between 1 and 500
        and length(trim(new.source_note,
                        char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760,
                             8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200,
                             8201, 8202, 8203, 8232, 8233, 8239, 8287, 12288, 65279))) >= 1,
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
