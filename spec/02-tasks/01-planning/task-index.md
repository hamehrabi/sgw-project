# Task Index

> Source: Ch. 4 §4.9 (Step 5) — "Create `task-index.md` so every future task has a record."
> Keeping tasks as separate files creates a useful history of what the project attempted.
> It makes review easier and prevents the same unclear request from being repeated.

---

| Task ID | Title | Requirement | Priority | Depends on | Status | Owner (human / agent) | Test IDs |
|---|---|---|---|---|---|---|---|
| TASK-001 | Sign in with two roles, and the application shell | REQ-NF-002, SEC-A-001…003, SEC-Z-001 | P0 | — | **Done** | agent | STEST-001…004, UTEST-001 |
| TASK-002 | Upload and parse a prepared storm into the joined asset view — **and wire FF-001 and FF-006** | REQ-F-001, REQ-F-010, REQ-NF-003, SEC-Z-002, FF-001, FF-006 | P0 | TASK-001 | **Done** | agent | ATEST-001, ATEST-002, ATEST-009, ATEST-010, UTEST-002…008, ITEST-001, FTEST-001…003, STEST-005…007, E2E-002 |
| TASK-003 | Ranked risk list with plain-words reasons, scored by a deterministic rule (ADR-005) | REQ-F-002, REQ-F-003, BR-002, FF-007 | P0 | TASK-002 | **Done** | agent | ATEST-003, ATEST-004, UTEST-009, UTEST-010, FTEST-004, EVAL-001, PTEST-001 |
| TASK-004 | Accept, change, or reject a recommendation, writing the append-only record | REQ-F-006, REQ-F-009, BR-001, BR-004, FF-004, FF-005 | P1 | TASK-003 | **Done** | agent | ATEST-006, ATEST-008, ITEST-002, FTEST-005, STEST-008 |
| TASK-005 | Dispatch board — one shared damage and repair list | REQ-F-007, REQ-NF-007 | P1 | TASK-002 | **In review** | agent | ATEST-007, ITEST-003, PTEST-002, UTEST-012, ITEST-002 (the ordering half) |
| TASK-006 | Re-rank on a forecast change, keeping the previous order | REQ-F-004 | P1 | TASK-003 | Not started | agent | ATEST-005, ITEST-004 |
| TASK-007 | Record a crew placement against the ranking | REQ-F-005 | P1 | TASK-003 | Not started | agent | E2E-001 |
| TASK-008 | Dismiss a false alarm in one action | REQ-F-008 | P1 | TASK-005 | Not started | agent | UTEST-011 |
| TASK-009 | Switch between several loaded storms | REQ-F-010 | P2 | TASK-002 | Not started | agent | ITEST-005 |
| TASK-010 | Wire the **remaining** fitness function into the build gate | FF-003 | P1 | — | Not started | human | — (the register is the assertion) |

**Status values:** Not started · In progress · Blocked · In review · Done · Rejected

**Priority (Ch. 14 §14.5):**

| Priority | Meaning | Example |
|---|---|---|
| P0 | Must exist before related work can begin. | User model, database table, API contract. |
| P1 | Required for the feature to be usable. | Login endpoint, form validation, error behavior. |
| P2 | Useful improvement after core behavior works. | Remember-me option, better loading state. |
| P3 | Future or polish item. | Animation, theme variation, optional shortcut. |

> When using an AI agent, start with P0 and P1. Do not give it P2 or P3 work until the
> foundation is implemented, tested, and reviewed.

## Nothing is blocked any more

**TASK-002 was blocked by Q-017 and no longer is** (CHG-006). A prepared scenario is a manifest
plus four CSVs, under 5 MB at demo scale, with the column list in `data-and-integration-spec.md`
§1 and the limits in `.env.example`. Eight of the ten tasks sat downstream of that one answer.

**Every task in the table above can now be started.** What remains open — Q-018's unmeasurable
baseline, Q-026's absent owners, Q-028's unrehearsed restore — blocks *claiming* things, not
*building* them.

**TASK-003 was blocked by Q-023 and no longer is.** ADR-005 settled it during this round: a
deterministic weighted rule for version one, behind the boundary that keeps the swap to a
trained model one module wide. What is still open is Q-025 — *which* factors and weights, and
who confirms the ranking is sane. That does not block starting the task, because the boundary,
the contract, and the reasons requirement are all fixed; it blocks calling the ranking
trustworthy, which is a different gate.

**TASK-001 is Done.** Accepted at review on 2026-08-15 with follow-up, by a reviewer who was also
its author — `review-log.md` records why (Q-026) rather than letting the signature imply
otherwise. The paragraph that stood here said its done criteria were incomplete because Q-021 had
not set a session duration; **ADR-006 answered it**, and both limits are read from configuration
with a test that uses a value other than the default.

**TASK-005 was signed off as Done, blocked at a second review, and is now In review again.**
The second review found that **the gate was not green** — 5 of 15 clean `pytest` runs were red —
and that three of the task's own done criteria were proven by nothing. All eight findings are
fixed and mutation-checked (`TASK-005.md`, *What the second review found*), and the suite has
been run twelve times without a red. **It is not Done until somebody who did not fix it says so.**

**The re-review happened on 2026-08-16 and the decision was Block again.** The gate is green —
264 tests over three runs, no red — and the CHG-018 ordering fix holds. But **done criterion 3
is not met**: `unique (scenario_id, location_key)` refuses only a byte-identical key, so the
case- and spacing-insensitivity that *defines* "the same location" lives only in
`store/dispatch.py`, and a second job for one neighbourhood inserted directly against the
database is **accepted**. That is this log's pre-declared Block condition for the second review
running. Two smaller failures — the durable `seq` order is asserted only inside one process
lifetime, and the store's location check has a clause no test ever violates — and one new
proposed entry, **CHG-022**. All four checks and their mutations are in `review-log.md`.
**TASK-006 must not be started on the assumption that TASK-005 is accepted.**

**The ordering defect was never TASK-005's alone**, which is why this row matters to TASK-004 as
well: `decision_records` has been intermittently mis-ordered since migration 006, and
`latest_recommendation` could return the wrong recommendation outright. That is fixed by the
same migration.

**Seven change entries are open against this task and none is accepted.** **CHG-016** (no endpoint
creates a damage report), **CHG-017** (`repair_jobs` had nowhere to keep the location it
answers, and `damage_reports.location` had no fixed resolution), **CHG-018** (a monotonic `seq`,
because a timestamp is not a total order), **CHG-019** (composite foreign keys — a foreign key
proved an asset existed, never that it was in this storm), **CHG-020** (a job's location
survives the dismissal of the report it came from), **CHG-021** (`duplicate` given a reader) and
**CHG-022** (a damage report belonging to no repair job is on no screen and in no figure — raised
at the third review, and **not implemented**). All are **proposed**: the build could not proceed
without deciding them, and none of the decisions is the agent's to accept. The row above gains **REQ-NF-007** and **UTEST-012** for a
different reason — `traceability.md` already puts that requirement on TASK-002 and TASK-005, and
this is the first task in which a damage location exists to be aggregated, so it is the first
task where the rule can be broken.

**TASK-010 shrank, and TASK-002 grew, at that review** (CHG-010). FF-001 and FF-006 move into
TASK-002, which is the task that first creates enough modules for an import cycle to exist and
the seven-defect fixture FF-006 checks against — wiring them there is cheaper than retrofitting a
gate over four tasks of drift. What remains in TASK-010 is blocked on the code it inspects rather
than on TASK-001, so its dependency moves too. **FF-002 was restated** in the same change: under
ADR-008 its old form could not fail, and a gate that cannot fail governs nothing.

---

## Dependency map

Draw the build order. If a task cannot be *tested correctly* without an earlier task,
there is a dependency (Ch. 14 §14.4).

```
TASK-001 (sign in + shell)
    ├── TASK-010 (wire the fitness-function gate)
    └── TASK-002 (upload + parse + joined asset view)
             ├── TASK-005 (dispatch board)
             │        └── TASK-008 (dismiss a false alarm)
             ├── TASK-009 (switch between storms)
             └── TASK-003 (ranked risk list + reasons)    [ADR-005 + ADR-007]
                      ├── TASK-004 (accept / change / reject + decision record)
                      ├── TASK-006 (re-rank on forecast change)
                      └── TASK-007 (record a crew placement)
```

**The shape is deliberate.** Every task from TASK-002 onward is a thin vertical slice — data,
rule, endpoint and screen for one capability — so each one is reviewable by using it. That is
the only review that catches *built the wrong thing*, which is the exact risk assumptions A2 and
A3 name.

## Only TASK-001 is written as a file, on purpose

`02-tasks/02-task-files/` holds one task file, not ten. With thin vertical slices and an agent
working one task at a time, TASK-003's detail depends on what TASK-002 actually produced —
writing all ten now would be layer-by-layer planning wearing a vertical-slice label, and most of
it would be stale by the third task.

Each task file is written from the template in `TASK-001.md` when its task is picked up. The row
above carries what is needed to start: the requirement, the dependency, the tests, and the
priority.

---

## Task breakdown checklist (Ch. 14)

- [x] Each task has one clear outcome.
- [x] Each task points back to a requirement, specification, or design decision.
- [x] Each task has done criteria that can be checked.
- [x] Dependencies are listed before implementation begins.
- [x] P0 and P1 tasks are completed before optional improvements.
- [x] Each task says what is out of scope.
- [x] No task gives the agent permission to rewrite unrelated code.
- [x] Tests are planned before or alongside implementation.

---

> Blueprint: blueprints/02-tasks/01-planning/task-index.md
