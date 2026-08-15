# Database Migration Plan

> Source: Ch. 23 §23.6.
> **Deployment caution:** never treat database changes as ordinary code changes. A broken
> file can be fixed and redeployed. A careless database change can damage production data.

AI-generated code may create models or queries but forget the release path. Require
migration planning in the specification.

---

## Migration entries

```
Migration ID:
Date:
Related requirement / task:  REQ-### / TASK-###

Change:                      [add table / add column / rename / add index / change type]
Reason:

Up migration:                [what it does]
Down migration:              [how to reverse it — or why it cannot be reversed]

Existing data impact:        [will old rows break? backfill needed?]
Backfill plan:
Deploy order:                [schema first, then code — or code first, then schema]
Downtime required:           Yes / No — [why]
Lock risk:                   [large table? staged migration needed?]
Verification query:          [how you confirm it worked]
Rollback procedure:
Tested on:                   [local / staging with production-like data]
```

| ID | Date | Change | Reversible? | Deploy order | Downtime | Status |
|---|---|---|---|---|---|---|
| MIG-001 | — | Create `users`, with `check role in ('admin','user')` | Yes | schema → code | No | Planned — TASK-001 |
| MIG-002 | — | Create `scenarios`, `assets`, with the BR-003 condition check | Yes | schema → code | No | Planned — TASK-002 |
| MIG-003 | — | Create `risk_scores`, with the BR-002 reasons check and the revision uniqueness | Yes | schema → code | No | Planned — TASK-003 |
| MIG-004 | — | Create `decision_records` **and its two append-only triggers** | Yes, but see below | schema → code | No | Planned — TASK-004 |
| MIG-005 | — | Create `repair_jobs`, `damage_reports`, with the dismissal check | Yes | schema → code | No | Planned — TASK-005 |

**Every migration here creates a constraint that enforces a business rule.** That is ADR-002
being spent: BR-002 is a check constraint in MIG-003, BR-003 is a check constraint in MIG-002,
and BR-004 is two triggers in MIG-004. A migration that ships the table without its constraint
ships a rule that exists only in prose.

---

## MIG-004 is the one to be careful with

```
Migration ID:               MIG-004
Related requirement / task: BR-004, REQ-F-009, REQ-R-002 / TASK-004
Change:                     Create decision_records, plus BEFORE UPDATE and BEFORE DELETE
                            triggers that abort (ADR-004)
Reason:                     The append-only guarantee. ADR-002 removed the role system
                            the original design relied on; triggers replace it.

Up migration:               Create the table, then both triggers.
Down migration:             Technically trivial — drop both, drop the table.
                            OPERATIONALLY THIS IS NOT AN ORDINARY DOWN MIGRATION. Running
                            it destroys the audit record, which is evidence for a
                            regulator. It is a decision, not a deployment step.

Existing data impact:       None on first creation. On any LATER migration touching this
                            table, both triggers must exist afterwards.
Backfill plan:              None.
Deploy order:               Schema first. The code that appends must never run against a
                            table whose triggers are absent — every row written in that
                            window is silently editable afterwards.
Downtime required:          No.
Lock risk:                  None at this size.
Verification query:         Confirm BOTH triggers exist by name, then attempt an UPDATE
                            against the table and assert the database refuses it. The
                            second half is the one that matters — a trigger that exists
                            and does not fire proves nothing.
Rollback procedure:         Roll the CODE back. Never drop a trigger to reverse a release.
Tested on:                  [TODO: has a restore been performed and timed? — see Q-028]
```

**The standing rule this migration creates, which applies to every future one:** after any
migration runs, both `decision_records` triggers must still exist. FF-004 checks it in the gate,
the deployment plan checks it after step 5, and `security-review.md` checks it before release —
three places, because there is no fourth thing that would notice.

---

## The four questions (Ch. 23 §23.6)

| Migration question | Why it matters | Spec example |
|---|---|---|
| Is the migration reversible? | Rollback is harder if the schema cannot return to a previous state. | Provide an **up** and **down** migration. |
| Will existing data break? | Old rows may not fit new rules. | Backfill missing values **before** making a field required. |
| Can code and database deploy safely? | A code change may expect a column that does not exist yet. | Deploy the schema change **before** the code that depends on it. |
| Is downtime required? | Some changes lock tables or interrupt users. | Use a staged migration for large tables. |

A fifth question belongs on this project, asked of every migration: **does this change, drop, or
recreate a constraint or trigger that enforces a business rule?** If yes, name the rule in the
migration and in the pull request. A dropped check constraint looks like a schema tidy-up and is
a rule silently removed.

---

## Safe pattern for adding a required column

1. Add the column as **nullable** with a default.
2. Backfill existing rows.
3. Deploy the code that writes the new value.
4. Only then add the `NOT NULL` constraint.

Each step is independently reversible. A single "add NOT NULL column" migration is not.

**Nothing needs this pattern yet**, because there is no data — and ADR-002 records exactly why
that matters: a down migration is cheap now and stops being cheap the first time a real storm's
decision record is in the file. The pattern is written down now so it is available then.

---

## Pre-migration checklist

- [ ] Migration tested on staging data that resembles production.
- [ ] Down migration exists **or** the irreversibility is documented and accepted.
- [ ] Backfill plan written for existing rows.
- [ ] Deploy order (schema vs. code) is explicit.
- [ ] Backup or restore point confirmed before running in production.
- [ ] Verification query written before, not after.
- [ ] Rollback owner named (see [`rollback-plan.md`](rollback-plan.md)).
- [ ] Database design spec updated (`../docs/database-design.md`).

Plus, for every migration after MIG-004:

- [ ] **Both `decision_records` triggers exist after this migration runs** — verified by
      attempting an `UPDATE` and confirming the database refuses it, not by reading the schema.

---

> Blueprint: blueprints/07-ops/01-deployment/database-migration-plan.md
