-- 012 down.
--
-- Back to 011's shape: `decision_records` with its two append-only triggers and no opinion about
-- what a `placement` payload contains.
--
-- Rolling this back reinstates one defect knowingly, and it is worth saying out loud rather than
-- leaving to be discovered: `product-spec.md` §10's *"traceable to the ranking and forecast
-- revision it was made against"* goes back to resting on `api/placements.py` remembering to look.
-- A placement naming an asset from another storm, from no storm at all, or from a revision this
-- storm has never ranked is accepted again, and rows written while the trigger was gone are not
-- revisited when it comes back — the guard says what may be **written**, and BR-004 means nothing
-- can go back and tidy them.
--
-- **The decision_records triggers are not touched here.** 012 did not create them, it re-asserted
-- them, and a down migration that removed BR-004's enforcement as a side effect of rolling back a
-- payload rule is exactly the failure ADR-004 exists to prevent. `test_TASK-007-AC10` issues a
-- real `UPDATE` after this file has run and requires the refusal, rather than reading two names
-- out of `sqlite_master` — a trigger can be present and wrong.
--
-- **This must run before 011's down migration and not after.** `decision_records_placement_shape`
-- reads `risk_scores`, and 011 rebuilds that table — `drop table` then `alter table … rename to`
-- — while SQLite reparses every trigger in the schema during a rename to fix up its references.
-- With the trigger still applied, 011's rollback lands in the window where `risk_scores` does not
-- exist and aborts. It aborts inside a transaction that rolls back whole, so the loud failure
-- costs nothing but a retry in the right order, and `test_TASK-007-AC10` asserts it rather than
-- leaving it to be met during an incident. Migrations roll back in reverse order for exactly this
-- reason, which is what 011's own down migration says about 010.

drop trigger if exists decision_records_placement_shape;

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
