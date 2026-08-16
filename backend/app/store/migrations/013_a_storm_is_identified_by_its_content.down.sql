-- 013 down.
--
-- Back to 012's shape: `scenarios` with no sequence, no content key, and no opinion about what a
-- storm's identity is.
--
-- **The digest goes back into `source_note` before the column holding it is dropped.** This is
-- the half a rollback of this migration has that its predecessors did not. Before 013,
-- `find_by_content_key` selected `where source_note = ?`; leaving the admin's note in that
-- column would make the older code unable to recognise an identical re-load at all, so the next
-- upload of a storm already loaded would create **a second copy with its own ranking of the same
-- weather**. A rollback that quietly turns idempotency off is worse than one that fails.
--
-- Rolling this back reinstates two defects knowingly, and they are worth saying out loud rather
-- than leaving to be discovered:
--
--   * §5's *identical content replaces in place* goes back to resting on a `select` in front of
--     an `insert` in `api/scenarios.py`. Two rows for one storm are accepted again by any
--     statement that does not go through it.
--   * The list of storms goes back to being ordered by a clock that cannot separate two rows
--     written in one 15.6 ms tick, with a random UUID as the tiebreak (CHG-018's finding).
--
-- The admin's typed source note has nowhere to go in the older shape — it has one column for two
-- facts, which is the defect this migration exists to fix — but it is **not lost**: it is still
-- on the `scenario_uploads` row that recorded the upload, and 013's up migration recovers it from
-- there. The round trip is therefore lossless, which is asserted rather than claimed
-- (`test_TASK-009-AC10`). What the older code cannot do is *show* it.
--
-- **The decision_records triggers are not touched here.** 013 did not create them, it re-asserted
-- them, and a down migration that removed BR-004's enforcement as a side effect of rolling back a
-- scenario rule is exactly the failure ADR-004 exists to prevent. `test_TASK-009-AC10` issues a
-- real `UPDATE` after this file has run and requires the refusal, rather than reading two names
-- out of `sqlite_master` — a trigger can be present and wrong.
--
-- **The triggers come off before the columns do.** SQLite refuses to drop a column any trigger or
-- index references, so the order below is required rather than tidy.

drop trigger if exists scenarios_identity_shape;
drop trigger if exists scenarios_identity_is_fixed;

update scenarios
   set source_note = content_key
 where length(content_key) = 64
   and content_key not glob '*[^0-9a-f]*';

drop index if exists scenarios_content_key;
drop index if exists scenarios_seq;

alter table scenarios drop column content_key;
alter table scenarios drop column seq;

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
