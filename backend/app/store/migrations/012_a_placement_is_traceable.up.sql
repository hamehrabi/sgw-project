-- 012 — a crew placement is a decision record, and one the store can refuse (TASK-007)
--
-- CHG-029, raised rather than assumed and left **proposed**.
--
-- `decision_records.kind` has permitted `'placement'` since migration 006 and until this task
-- nothing wrote one, nothing read one, and no document said what the row contained. That is the
-- shape CHG-021 named one task earlier — an enumerated value with no writer and no reader — and
-- a value the schema permits is a state a screen can reach.
--
-- `product-spec.md` §10 is the only place the feature is written out, and it makes one claim
-- this migration exists to hold: a placement is *"traceable to the ranking and forecast revision
-- it was made against"*. Traceable is not a property of a response body. It is a property of the
-- stored row, and `review-log.md`'s standing **Block** condition is *a rule enforced in the
-- service layer that the store could refuse* — which has fired twice, on a foreign key that
-- proved existence rather than membership (CHG-019) and on a `unique` constraint that could not
-- see the normalisation in front of it (CHG-023). Both were found by asking what a **direct
-- insert** can put in a column.
--
-- WHY A TRIGGER AND NOT A CHECK CONSTRAINT, WHICH IS WHAT ADR-002 WOULD ORDINARILY PREFER.
--
-- SQLite cannot add a `check` to an existing table. Adding one means rebuilding
-- `decision_records` — `create table … new`, copy, `drop table`, rename — and dropping that table
-- drops **both append-only triggers with it**, so the rebuild would have to create them again.
-- ADR-004 forbids exactly that, CLAUDE.md lists it under *Never*, and `database-design.md` §3
-- says removing either is a change requiring a superseding ADR. Migration 008 met the same wall
-- when it added `seq` and used `alter table … add column` to stay clear of it; there is no
-- `alter table … add check`, so the way clear here is a trigger.
--
-- It is also the honest statement of the rule. A `check` cannot see another table, and the
-- load-bearing clause below — *every asset named is on the ranking this placement claims to have
-- been made against* — is a join. That is the same argument CHG-026 and CHG-028(b) made for
-- `risk_scores`, and the same limit applies and is recorded rather than implied away: the trigger
-- says what may be **written**, not what may **exist**, so deleting a ranking afterwards leaves a
-- placement pointing at a list that is gone. Nothing deletes a ranking except a scenario delete,
-- which takes the assets with it; and `decision_records` deliberately does not cascade with its
-- scenario, because an audit row must outlive the thing it describes (migration 006).
--
-- **012 MUST BE ROLLED BACK BEFORE 011 AND NOT AFTER**, and rolled forward after it — which is
-- the ordinary reverse order, stated because the consequence of getting it wrong is loud and
-- surprising. The trigger below reads `risk_scores`, and 011 **rebuilds** that table: `drop
-- table risk_scores` then `alter table risk_scores_new rename to risk_scores`. Since SQLite 3.25
-- a rename reparses every trigger in the schema to fix up its references, and in the window
-- between those two statements the table does not exist — so with this trigger still applied,
-- 011 aborts, up or down. It aborts inside a transaction that rolls back whole, so nothing is
-- lost and the operator retries in the right order; `test_TASK-007-AC10` asserts both halves,
-- the same way `test_TASK-006-AC13` asserts 011-before-010. The cost is recorded rather than
-- worked around: **any future migration that rebuilds `risk_scores` must drop this trigger
-- first and recreate it afterwards**, exactly as 011 does with its own three.
--
-- BOTH decision_records TRIGGERS ARE RE-ASSERTED AT THE END OF THIS FILE (ADR-004, BR-004).
-- Neither is dropped, disabled or recreated here, and this migration does not rebuild the table.

create trigger decision_records_placement_shape
before insert on decision_records
when new.kind = 'placement'
begin
    -- 1. The crew. CON-003 permits **a display name and a role** and forbids everything else
    --    about a person, so this column is a label and is bounded like one. `coalesce(…, 0) = 0`
    --    rather than `not (…)`: `json_type` answers SQL null for a key that is absent, and
    --    `where not null` selects nothing — an absent crew would have been accepted by the
    --    obvious spelling of this clause.
    --
    --    The whitespace is enumerated rather than left to `trim()`. Writing the missing cases
    --    for `damage_reports.location` found that `length(trim(x)) between 1 and 120` refused
    --    `'   '` and **stored** `char(9) || char(10)`, because SQLite's `trim()` strips spaces
    --    and nothing else (CHG-023). The same clause written the same way would have the same
    --    hole.
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

    -- 2. The where. `product-spec.md` §10: *which crews wait where — against **named assets***.
    --    A placement naming nothing is a row that says a crew exists. The upper bound is the
    --    same kind of statement a file-size limit is: a legitimate placement never reaches it
    --    and an unbounded payload cannot pass. Written with two comparisons rather than
    --    `between`, so the one `between 1 and 120` in this trigger is unambiguously the crew
    --    label's bound — which is the number `test_TASK-007-AC4` reads back out of
    --    `sqlite_master` and ties to `decisions.CREW_LABEL_MAX`.
    select raise(abort, 'a placement names at least one asset and no more than 500 (REQ-F-005)')
    where coalesce(
        json_type(new.payload, '$.asset_ids') = 'array'
        and json_array_length(new.payload, '$.asset_ids') >= 1
        and json_array_length(new.payload, '$.asset_ids') <= 500,
        0) = 0;

    -- 3. A crew waits at a place once. Two entries would double the asset in every count built
    --    on this row, and a count is the only thing anyone will ever aggregate here.
    select raise(abort, 'a placement names each asset once (REQ-F-005)')
    where json_array_length(new.payload, '$.asset_ids')
          <> (select count(distinct value) from json_each(new.payload, '$.asset_ids'));

    -- 4. Half of *traceable to the ranking AND forecast revision*, and the half no reader can
    --    reconstruct afterwards — `scenarios.forecast_revision` is a pointer and it moves.
    select raise(abort, 'a placement names the forecast revision it was made against (REQ-F-005)')
    where coalesce(json_type(new.payload, '$.forecast_revision') = 'integer', 0) = 0;

    -- 5. The subject is the ranking, spelled exactly the way the `recommendation` row for that
    --    ranking spells it, so `decision_records_by_subject` answers "what was recommended here,
    --    and what did people decide about it" in one lookup. A row whose subject says one
    --    revision and whose payload says another answers differently depending on which half is
    --    read.
    select raise(abort, 'a placement is recorded against the ranking it was made against (REQ-F-005)')
    where new.subject_type <> 'ranking'
       or new.subject_id <> new.scenario_id || ':' || json_extract(new.payload, '$.forecast_revision');

    -- 6. The note, bounded in the store as well as in the request model — for the reason the
    --    crew label is: a request model is not what a direct insert passes through.
    select raise(abort, 'a placement note is text of up to 2000 characters, or null (REQ-F-005)')
    where coalesce(
        json_type(new.payload, '$.note') = 'null'
        or (json_type(new.payload, '$.note') = 'text'
            and length(json_extract(new.payload, '$.note')) <= 2000),
        0) = 0;

    -- 7. The load-bearing clause. Every asset named is on the ranking this placement claims to
    --    have been made against — which is membership rather than existence, on **caller-supplied
    --    input**, which is what made CHG-019 a Block rather than an observation. It subsumes the
    --    storm scope: a row in `risk_scores` for this scenario at this revision is by
    --    construction one of this storm's own assets.
    --
    --    An **UNSCORED** asset satisfies it. It has a `risk_scores` row with a null score and a
    --    reason why, it is in the ranking and not ranked, and the entire purpose of keeping it on
    --    the list is so a person can plan around it (FTEST-004). Refusing to let a crew be placed
    --    at one would be the review log's first pre-declared Block condition wearing a
    --    validation rule's clothes.
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
