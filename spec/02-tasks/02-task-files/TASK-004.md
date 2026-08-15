# TASK-004: Accept, change, or reject a recommendation, writing the append-only record

> Written from the template in `TASK-001.md` when the task was picked up.

---

**Task ID:** TASK-004
**Task title:** Accept, change, or reject a recommendation, writing the append-only record
**Priority:** P1
**Status:** Done — accepted 2026-08-15, `review-log.md`. AC-009 settled by **CHG-015**: the refusal goes to the security log, not the decision record.
**Assigned to:** AI agent

---

## Source requirement or spec section

REQ-F-006 · REQ-F-009 · BR-001 · BR-004 · REQ-R-002 · SEC-Z-003 · SEC-Z-004 · ADR-004

## Business reason

**BR-001 is the rule the whole product is governed by.** Remove it and the product changes
category — from decision support to automation, with a different regulator and a different
liability. This task is where that rule becomes code: a decision is *recorded*, and nothing
moves.

**BR-004 is what makes the record worth having.** An audit trail its own subjects can rewrite
proves nothing, and its value is realised exactly when someone would most want to change it.

## What a "recommendation" is, and why

**One delivered ranking is one recommendation.** Three things agree on this and it is written
down here because the wording elsewhere invites a per-asset reading:

- FF-005 says *every delivered **ranking** has a matching `decision_records` row of kind
  `recommendation`* — per delivery, not per row of the list.
- US-008 wants a person to accept, change or reject *the advice*, so the system "stays
  something that advises me".
- The per-asset action already exists separately: **TASK-007** records a crew placement against
  the ranking (REQ-F-005). Folding placements into this endpoint would give one action two
  homes.

## Goal

Delivering a ranking appends a `recommendation` row. A person accepts, changes or rejects it,
which appends a second row naming them. Neither can afterwards be altered, by anyone, including
an admin — **because the database refuses the statement**, not because the code declines to
issue one.

## Expected files or components

**Backend:** migration 006 — `decision_records` with its `BEFORE UPDATE` and `BEFORE DELETE`
triggers. `store/decisions.py` — append-only writes and the admin read. `api/` gains
`POST /api/v1/recommendations/{recommendation_id}/decision` and
`GET /api/v1/scenarios/{scenario_id}/decisions`, plus the recommendation row on ranking
delivery.
**Frontend:** `views/RecommendationDecision`.
**Gate:** FF-004 and FF-005 wired into `ci/fitness.py`, mutation-checked first.

## Step-by-step instructions

1. Migration 006 exactly as `database-design.md` §3 specifies, **including both triggers**.
2. Append a `recommendation` row when a ranking is delivered (`api-specification.md`, side
   effects of `GET /risks`).
3. The decision endpoint: `accept` | `change` | `reject`; a note **required** on change and
   reject, trimmed, up to 2000 characters; `409` on a second decision, naming the first.
4. `GET /decisions` — **admin only** (SEC-Z-003).
5. `RecommendationDecision`: the note survives a failed write; a second decision shows the
   first rather than overwriting it.
6. Wire FF-004 (both triggers present **and** an `UPDATE` refused by the database) and FF-005
   (no delivered ranking without its row). Mutation-check both before the register says they run.

## Constraints / Boundaries

- **Never write `UPDATE` or `DELETE` against `decision_records`.** A correction is a new row.
- **Never drop, disable or recreate either trigger** inside an unrelated migration.
- **The response is a record, never an action** (BR-001). No crew is moved, no job assigned, and
  nothing leaves the platform as a result of this call.
- The decision endpoint is **not** privileged — deciding is the product, not an admin action.
  Only *reading* the record is admin-only.
- Do not build crew placement (TASK-007) or dismissal (TASK-008).

## Acceptance check / Done criteria

1. Delivering a ranking appends exactly one `recommendation` row carrying enough to reconstruct
   what was shown.
2. A decision appends a row with its timestamp and acting user.
3. A second decision on the same recommendation returns **409**, names the existing decision,
   and leaves the first row **byte-identical**.
4. An `UPDATE` and a `DELETE` issued **directly against the database** are both refused by the
   triggers — asserted against the store, not the service layer (STEST-008, FF-004).
5. A non-admin reading the decision record gets 403 and zero rows (STEST-007).
6. A forced write failure shows no success, writes no row, and keeps the typed note on screen
   (FTEST-005).
7. No decision path issues any outbound action (BR-001).
8. FF-004 and FF-005 run, and were seen to fail first.

## Tests to run or create

| Test ID | Defined in |
|---|---|
| ATEST-006, ATEST-008 | `03-tests/02-functional/acceptance-tests.md` |
| ITEST-002 | `03-tests/02-functional/integration-tests.md` |
| FTEST-005, FTEST-006 | `03-tests/04-failure/failure-tests.md` |
| STEST-007, STEST-008 | `03-tests/03-non-functional/security-tests.md` |
| STEST-005 (the refusal-record half, owed from TASK-002) | `03-tests/03-non-functional/security-tests.md` |

## Out of scope

Crew placement (TASK-007) · dismissing a false alarm (TASK-008) · re-ranking (TASK-006)

## Stop condition

**Stop and ask** if a decision appears to require editing an existing row, if a migration
appears to need either trigger dropped, or if anything suggests the platform should act on a
decision rather than record it.

---

> Written from: blueprints/02-tasks/02-task-files/TASK-001.md
