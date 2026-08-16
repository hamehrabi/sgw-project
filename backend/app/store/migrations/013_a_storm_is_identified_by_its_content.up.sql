-- 013 — a loaded storm is identified by the content it came from, carries the note a person
--       reads it by, and has a place in the order storms are listed in (TASK-009)
--
-- CHG-031 and CHG-032, raised rather than assumed and left **proposed**. TASK-009 is the first
-- task that reads `scenarios` as a **list** and shows it to somebody, and two things broke as
-- soon as it did.
--
--   (a) **`source_note` was holding a SHA-256 digest.** `database-design.md` §3 defines the
--       column as *"which prepared dataset this is, and where it came from"*, and
--       `data-and-integration-spec.md` §3 has the admin supply it in the multipart body. But §5
--       also requires that *"loading a scenario whose content is identical to one already loaded
--       replaces that one in place"*, and the digest that rule turns on had no column — so
--       `api/scenarios.py` wrote it into `source_note` and threw the admin's note away.
--       `ScenarioSwitcher`'s specified third field was 64 characters of hex.
--
--       Worse for the rule itself: *identical content is one storm* lived entirely in
--       `find_by_content_key` — a `select` in front of an `insert`. A direct insert produced two
--       rows for one upload, each with its own ranking of the same weather, and a decision
--       recorded against one of them was a decision about a list the other reader never saw.
--       That is ADR-002's exact prohibition — *never implement a check in the service layer that
--       the store could refuse* — and `review-log.md`'s standing Block condition.
--
--   (b) **`scenarios` had no total order.** CHG-018 gave `repair_jobs`, `damage_reports` and
--       `decision_records` a monotonic `seq`, because `datetime.now(UTC).isoformat()` resolves to
--       about 15.6 ms on this platform (1,999 of 2,000 consecutive calls return an identical
--       string) and a random UUID is not a tiebreak. `scenarios` was left out because nothing
--       read it as a list. This task reads it as a list, so two storms loaded inside one tick
--       came back in coin-flip order.
--
-- **`scenarios` is NOT rebuilt, and that is a decision rather than a convenience.** Six tables
-- reference it with `on delete cascade` — assets, risk_scores, scenario_forecast_revisions,
-- scenario_forecast_cells, damage_reports, repair_jobs — plus decision_records and
-- scenario_uploads. The standard SQLite rebuild (create, copy, `drop table scenarios`, rename)
-- would fire every one of those cascades and empty the database on the way past. A `check`
-- constraint is therefore unavailable, and the rules go in triggers: CHG-026, CHG-028(b) and
-- CHG-029's argument reused — *a rule the schema cannot express without destroying something
-- else is a trigger, and it says the true and narrower thing: what may be written.*
--
-- **Declined, in writing:**
--   * *leaving §5's rule in `api/scenarios.py`* — that is the finding, not a fix.
--   * *a `unique` index on `source_note`* — it would make two storms from different files
--     collide because an admin typed the same note twice, and leave two loads of one file apart
--     because they typed different ones. The note is prose; the digest is identity.
--   * *making `content_key` `not null` by `alter table`* — SQLite requires a default for that,
--     and any default is a value two rows could share. The trigger states the real rule (a
--     64-character lower-case hexadecimal digest) and the unique index enforces distinctness.
--   * *a `before delete` guard on `scenarios`* — §7.2's *delete or replace a scenario* is a
--     supported admin action, and CHG-024 records why a delete guard on a cascade root turns a
--     supported operation into an integrity error.
--   * *allowing a storm to be renamed* — nothing in the product renames one, and an identity
--     that can move is an identity a switcher cannot be read against. If a rename is ever
--     wanted, this trigger is where the decision goes.
--
-- BOTH decision_records TRIGGERS ARE RE-ASSERTED AT THE END OF THIS FILE (ADR-004, BR-004).
-- Neither is dropped, disabled or recreated here, and this migration adds nothing to that table.

begin;

-- 1. CHG-032. The sequence, backfilled from the rowid the rows were already written in, so the
--    order that existed by accident becomes the order that exists on purpose. `unique` is what
--    makes two storms claiming one place in the history a refusal rather than a coin flip.
alter table scenarios add column seq integer not null default 0;
update scenarios set seq = rowid;
create unique index scenarios_seq on scenarios (seq);

-- 2. CHG-031. The identity gets its own column, and the note column gets its meaning back.
alter table scenarios add column content_key text;

--    Rows loaded through the upload path carry the digest in `source_note`; it moves.
--
--    What replaces it is the note the admin actually typed, recovered from `scenario_uploads` —
--    the row that recorded the upload, which carries `name` and `source_note` as supplied. That
--    matters twice over: it makes this migration's **round trip lossless**, because rolling 013
--    back has to put the digest back in `source_note` for the older code to find it, and a
--    roll-forward that then wrote a placeholder would destroy a real fact by way of an ops
--    procedure.
--
--    Where the upload row carries a digest too — every storm loaded before 013 first ran, since
--    the pre-013 code wrote the digest into both — there is nothing to recover, and what goes in
--    is a sentence saying the note was never recorded rather than an invented one. Migration
--    010's backfill dating was made loud for exactly the same reason: a fabricated fact on a
--    column somebody reads is worse than an absent one.
update scenarios
   set content_key = source_note,
       source_note = coalesce(
           (select u.source_note from scenario_uploads u
             where u.scenario_id = scenarios.id
               and not (length(u.source_note) = 64
                        and u.source_note not glob '*[^0-9a-f]*')
             limit 1),
           '(not recorded: this storm was loaded before migration 013)')
 where length(source_note) = 64
   and source_note not glob '*[^0-9a-f]*';

--    Any other row predates the upload path entirely. It is identified by itself, and the prefix
--    says so rather than letting a non-digest pass for one.
update scenarios set content_key = 'no-upload:' || id where content_key is null;

--    §5, in the schema. **This statement aborts the migration if two rows share one upload** —
--    deliberately. Choosing which of two rankings to destroy is not a migration's decision, and
--    a loud failure inside a transaction that rolls back whole costs a retry.
create unique index scenarios_content_key on scenarios (content_key);

-- 3. What may be written. One `raise` per clause, each with its own sentence, so a test can read
--    the refusal out of the message rather than out of the exception type — five assertions in
--    this repository have passed for a rule other than the one they named.
create trigger scenarios_identity_shape
before insert on scenarios
begin
    -- (a) The identity. `unique` permits any number of NULLs in SQLite, so without this clause
    --     two storms with no identity at all coexist happily and §5 holds for every row except
    --     the ones written around the endpoint. The case clause is not decoration: `hexdigest()`
    --     never produces upper case, so an upper-case key is a second spelling of one storm and
    --     `unique` cannot see past a spelling (CHG-023, one column over).
    select raise(abort, 'a storm is identified by the content it was loaded from: content_key is a 64-character lower-case hexadecimal digest (REQ-F-010, data-and-integration-spec.md 5)')
    where coalesce(
        typeof(new.content_key) = 'text'
        and length(new.content_key) = 64
        and new.content_key not glob '*[^0-9a-f]*',
        0) = 0;

    -- (b) The label a person chooses the storm by. The whitespace is enumerated rather than left
    --     to `trim()`: SQLite's one-argument `trim()` strips **spaces only**, which is how a
    --     tab-and-newline location was storable while a spaces-only one was refused (CHG-023).
    --
    --     There are exactly two length bounds in this trigger, written as ranges, and
    --     `test_TASK-009-AC5` reads both back out of `sqlite_master` and ties them to
    --     `store/scenarios.py` — otherwise the endpoint's specified 400 becomes a 500. Comments
    --     are stored in `sqlite_master` with the statement, so neither bound is repeated in
    --     prose anywhere in this trigger; the test found that by counting three.
    select raise(abort, 'a storm carries a name of 1 to 200 characters that is not blank, because a name is what somebody picks it out by (REQ-F-010)')
    where coalesce(
        typeof(new.name) = 'text'
        and length(new.name) between 1 and 200
        and length(trim(new.name, ' ' || char(9) || char(10) || char(11) || char(12) || char(13))) >= 1,
        0) = 0;

    -- (c) §3's *which prepared dataset this is, and where it came from*, `required`. A blank one
    --     is a switcher row that claims to say where a storm came from and does not.
    select raise(abort, 'a storm carries a source note of 1 to 500 characters saying which prepared dataset it is and where it came from (REQ-F-010, database-design.md 3)')
    where coalesce(
        typeof(new.source_note) = 'text'
        and length(new.source_note) between 1 and 500
        and length(trim(new.source_note, ' ' || char(9) || char(10) || char(11) || char(12) || char(13))) >= 1,
        0) = 0;
end;

-- 4. The insert guard says what may be written; without this one an `UPDATE` walks around all of
--    it. A storm given another storm's digest, or renamed to blank, is the same defect arriving
--    through a different statement — and the pointer this table exists to move is untouched,
--    because `forecast_revision` is not one of the three columns named here.
create trigger scenarios_identity_is_fixed
before update on scenarios
when new.content_key is not old.content_key
  or new.name is not old.name
  or new.source_note is not old.source_note
begin
    select raise(abort, 'a loaded storm''s identity is fixed at load: what it was loaded from, what it is called and where it came from are never rewritten (REQ-F-010)');
end;

commit;

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
