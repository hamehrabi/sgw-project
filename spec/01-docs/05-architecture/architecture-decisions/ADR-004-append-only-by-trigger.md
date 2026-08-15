# ADR-004: Enforce the append-only decision record with database triggers

**ADR ID:** ADR-004
**Status:** Accepted
**Date:** 2026-08-15
**Decision owner:** Tech lead (not yet named)
**Review date:** At any change to the store (ADR-002) or to the migration process

---

## Context

BR-004 says the decision record is append-only: a correction is a new row, never an edit. It is
not a tidiness rule. Auditability is one of the three driving characteristics, the record exists
to be produced to a regulator, and its value is realised precisely when somebody would most like
to change it — which is why the enforcement must not sit with the people it records.

`database-design.md` §3 originally enforced this with a **role grant**: the application's
database role would hold `INSERT` and `SELECT` on `decision_records` and neither `UPDATE` nor
`DELETE`, and FF-004 would assert the grant's absence.

ADR-002 then chose an embedded relational database, which **has no role system**. The specified
enforcement is unavailable, and a decision is needed rather than a silent downgrade.

Round 5 also declined *"the decision record proves un-editable"* as an explicit release gate,
so nothing else in the workspace would have caught the loss.

## Options considered

1. **Application-layer check** — no repository method issues an `UPDATE` or `DELETE` against
   the table, enforced by code review and a source-scanning test. Cheapest, and it is exactly
   the layer BR-004 exists to distrust: one refactor, one convenience method, and the rule is
   gone with every functional test still green.
2. **Database triggers** — `BEFORE UPDATE` and `BEFORE DELETE` on `decision_records`, each
   raising an abort. The store refuses the statement whatever issued it. Costs two lines of
   migration and the discipline of not dropping them.
3. **Reintroduce a server-based store for its role system** — reverses ADR-002 to recover the
   original mechanism. Buys a genuinely stronger separation, at the price of the operational
   component ADR-002 removed and a week that does not have room for it.

*Compared on:* which interface is simpler · which is more general · which forces callers
to do work that should be inside · which is cheaper to reverse.

## Decision

Enforce append-only with **`BEFORE UPDATE` and `BEFORE DELETE` triggers on `decision_records`**,
each aborting the statement. FF-004's check changes from *the role holds no grant* to *the
database refuses the statement*; what FF-004 guarantees does not change.

## Reason

It keeps the rule inside the store, which is the whole property option 1 gives away. The
assertion stays the same shape as before — issue an `UPDATE` against `decision_records` and
require that the **database** refuses it, not the service layer — so the test that proves
BR-004 is unchanged in intent and still meaningful.

Option 3 is stronger and was rejected on cost, not on merit: a role system separates *who may
change the rule* from *who may change the data*, and a trigger does not — anyone who can run a
migration can drop it. That residual weakness is real and is named below rather than hidden.

## Consequences

- **Positive:** BR-004 survives the change of store. The rule is enforced where it belongs, and
  FF-004 remains a database-level assertion rather than becoming a code-review convention.
- **Trade-off or limitation:** A migration can drop a trigger, and the migration path is the
  same path a developer uses every day. The role-grant version separated those two powers; this
  does not. Mitigation: the migration checklist must treat removing either trigger as a change
  requiring a superseding ADR, and FF-004 fails the build if either is missing — so dropping
  one is visible rather than silent.
- **Rule the AI assistant must follow during implementation:** Never write an `UPDATE` or
  `DELETE` against `decision_records`. Never drop, disable, or recreate either trigger as part
  of an unrelated migration. A correction to a recorded decision is a new row.

> **If no trade-off is visible, keep looking.** A choice with no downside was never a
> choice — you are comparing in the abstract instead of weighted for this context.

## Compliance

| Enforced by | Where |
|---|---|
| FF-004 | [`../../04-technical-spec/fitness-functions.md`](../../04-technical-spec/fitness-functions.md) |

FF-004 now checks two things: that both triggers exist, and that an `UPDATE` issued against
`decision_records` is refused by the database. The second is what makes the first meaningful —
a trigger that exists and does not fire proves nothing.

## Revisit when

The store changes (superseding ADR-002), **or** the migration process gains more than one person
able to run it. The second is the trigger for this decision's known weakness becoming material.

## Impact

| Dimension | Impact |
|---|---|
| Security | Recovers most of what ADR-002 gave up. Weaker than a role grant in one specific way: it does not separate the power to change the rule from the power to change the data. |
| Reliability | Neutral. A trigger that aborts is a failed statement, handled like any other write failure (`technical-spec.md` §9.3). |
| Performance | Negligible. Two triggers on a table that is only ever inserted into. |
| Cost | Zero. |
| Maintainability | Slight cost: the migration checklist gains a rule, and FF-004 gains a second assertion. |

## Related

- Related requirements: BR-004, REQ-F-009, REQ-R-002
- Related technical spec sections: §5 Database Requirements, §12 Deployment Approach
- Supersedes / superseded by: — (forced by ADR-002)

---

> Blueprint: blueprints/01-docs/05-architecture/architecture-decisions/ADR-000-template.md
