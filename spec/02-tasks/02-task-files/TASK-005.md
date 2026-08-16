# TASK-005: Dispatch board — one shared damage and repair list

> Written from the template in `TASK-001.md` when the task was picked up.

---

**Task ID:** TASK-005
**Task title:** Dispatch board — one shared damage and repair list
**Priority:** P1
**Status:** Done — built 2026-08-16, `review-log.md`. Two change entries raised and **proposed, not accepted**: **CHG-016** (no endpoint creates a damage report) and **CHG-017** (the job had nowhere to keep the location it answers, and the report's location had no fixed resolution).
**Assigned to:** AI agent

---

## Source requirement or spec section

REQ-F-007 · AC-007 · REQ-NF-007 · CON-003 · CON-007 · US-009 · ADR-002 ·
`database-design.md` §3 (`repair_jobs`, `damage_reports`) · `api-specification.md` endpoint index ·
`frontend-component-spec.md` (`DispatchBoard`)

## Business reason

**This is the during-storm half of the product.** The planning view is used before the storm;
this is the screen a dispatcher works while it is happening, and `product-spec.md` §persona is
explicit about what it replaces: *a damage picture assembled in one person's head from radio,
alarms and a whiteboard, while new reports arrive faster than they can be written down.*

**AC-007 is the whole point, not a detail of it.** Two reports about the same place must
resolve to one repair job, because the failure this feature exists to prevent is two crews
arriving at one location during a storm while somewhere else waits. Success metric 2 —
*one full damage picture in under five minutes* — is a consequence of that, not a separate goal.

## What "one location" means here, and why it is decided in this task

**CON-003 forbids storing any premise-level record.** So the finest location this platform is
allowed to hold is the **neighbourhood**, and `damage_reports.location` is constrained by the
schema to carry exactly that and nothing else. Two consequences follow, and both are load-bearing:

- **"The same location" means the same neighbourhood** — that is what AC-007's grouping key can
  be, because nothing finer legally exists in the model.
- **REQ-NF-007 becomes structural rather than procedural.** "Damage locations are aggregated to
  neighbourhood level in every log and export" is normally a rule every log line has to
  remember. Here there is nothing finer stored to leak: the aggregation happened before the
  write, and the store refuses a location that carries anything else.

That resolution is not stated in `database-design.md` §3, which says only `location: json,
required`. It is raised as **CHG-017**, status *proposed*.

## Goal

A dispatcher records damage as it is reported and reads one shared list. Two reports at one
location appear as two reports under **one** repair job — and a second job for that location is
refused **by the database**, not by the code that forgot to look first. No log line and no
response body carries a location finer than a neighbourhood.

## Expected files or components

**Backend:** migration **007** — `repair_jobs` and `damage_reports` per `database-design.md` §3,
plus `repair_jobs.location_key` with `unique (scenario_id, location_key)` (CHG-017), and both
`decision_records` triggers re-asserted with `create trigger if not exists`.
`store/dispatch.py` — file a report, find or create its job, read the board.
`api/dispatch.py` — `POST /api/v1/scenarios/{scenario_id}/damage-reports` (CHG-016) and
`GET /api/v1/scenarios/{scenario_id}/jobs`.
`api/views.py` gains the board's response shapes.
**Frontend:** `views/DispatchBoard.tsx`, wired into `ScenarioView`; `lib/api.ts` gains `dispatch`.
**Gate:** no new fitness function — FF-003 is TASK-010's and nothing here reaches it.

## Step-by-step instructions

1. **Read the schema against the documents first** (`AGENT.md`, third lessons row). Two gaps
   were found this way and raised before any code: nothing creates a damage report, and
   `repair_jobs` has no column that can hold the location it answers.
2. Write ATEST-007, ITEST-003, PTEST-002 and UTEST-012 **first**, from their rows in
   `03-tests/`, and run them: each must fail because the feature is absent.
3. Migration 007, both tables exactly as §3 specifies — including the dismissal columns and
   check TASK-008 will use, which are §3's and not this task's to invent or omit.
4. **Every constraint that can live in the schema lives there** (ADR-002):
   `unique (scenario_id, location_key)` on `repair_jobs` is AC-007; the `location` check
   constraint is CON-003 and REQ-NF-007; the dismissal check is REQ-F-008's, written now
   because §3 says so.
5. Filing a report: validate the neighbourhood, reject every unknown field outright, find the
   open job for that location or create one, attach the report to it, return the job.
6. The board: one query for jobs, one for reports, grouped in the response. **No query inside a
   loop** — `performance-tests.md` names that as the live risk, and PTEST-002 asserts the
   statement count is constant in the number of reports.
7. `DispatchBoard`: two reports at one location render under one job; the empty state reads
   *no damage reported*, never *all clear*.
8. Mutation-check every test written here before believing any of them.

## Constraints / Boundaries

- **Never store, log or return a location finer than a neighbourhood** (CON-003, REQ-NF-007).
  Not an address, not a meter or account number, not a household, not a coordinate. The board
  names an asset by `asset_id` only (STEST-009).
- **The board records; it dispatches nothing** (BR-001, BR-005). Creating a job assigns no crew
  and sends no message. `assigned_to` is a note about what people did, never an instruction.
- **Never let a rank, band or score decide the board's order.** Criticality badges the dispatch
  queue; risk orders the planning list, and they are different lists (ADR-007). The board is
  ordered by when the work arrived.
- **No scoring rule and no matching rule in a route handler** (FF-001).
- Do not build dismissal (TASK-008) or crew placement (TASK-007). The `dismissed_by` /
  `dismissed_reason` columns are created because §3 defines them; no endpoint writes them here.
- Nothing under `01-docs/` is edited. Both gaps became change entries instead, **proposed**.

## Acceptance check / Done criteria

1. Two damage reports for one location produce **exactly one** `repair_jobs` row, and both
   reports carry the same `repair_job_id` (AC-007, ITEST-003).
2. Both reports are **visible** on the board, under that one job — one job is not one report
   (AC-007's first half, which a de-duplicating implementation would silently fail).
3. A second job for the same location, inserted **directly against the database**, is refused
   by the store — not by the service layer (ADR-002).
4. A location carrying anything beyond a neighbourhood — an address, a coordinate, a household —
   is refused by the store, and the endpoint refuses the field before it gets there (UTEST-012).
5. No log line written by this task carries a location finer than a neighbourhood, and the
   figure it logs is an aggregate for that neighbourhood (REQ-NF-007, UTEST-012).
6. A single report in a sparse area still aggregates — one report in a neighbourhood is a
   neighbourhood figure of one, never a pointer to a household.
7. The board query uses `damage_reports(scenario_id, status, repair_job_id)` rather than
   scanning, and issues a **constant** number of statements regardless of report count
   (PTEST-002).
8. First usable screen under 2 s and reasons visible under 300 ms at 220 assets — the reasons
   arrive with the rank and are never re-fetched (PTEST-002, REQ-NF-001).
9. A signed-out caller reaches neither endpoint (STEST-001 already lists `/jobs`).
10. Every test written here was mutation-checked: the behaviour broken, the test seen red, the
    break reverted.

## Tests to run or create

| Test ID | Defined in |
|---|---|
| ATEST-007 | `03-tests/02-functional/acceptance-tests.md` |
| ITEST-003 | `03-tests/02-functional/integration-tests.md` |
| PTEST-002 | `03-tests/03-non-functional/performance-tests.md` |
| UTEST-012 (owed by REQ-NF-007, which this task is the first to make reachable) | `03-tests/02-functional/unit-tests.md` |

**UTEST-012 is not in the register's row for TASK-005 and is written anyway.** `traceability.md`
puts REQ-NF-007 on TASK-002 and TASK-005; TASK-002 built no damage report, so this is the first
task where a damage location exists to be aggregated. Writing the requirement's code without its
test would leave the row Planned against shipped behaviour.

**STEST-009 stays Planned.** Its other half — *no asset location or connection appears in full*
— covers export paths this task does not build, and the part of it that is reachable now
(the board carries `asset_id` only, never a coordinate) is asserted inside UTEST-012 rather than
claimed by an id nobody wired.

## Out of scope

Dismissing a false alarm (TASK-008) · crew placement (TASK-007) · re-ranking (TASK-006) ·
ordering the board by risk or criticality · assigning crews · any notification of any kind.

## Stop condition

**Stop and ask** if anything requires storing a location finer than a neighbourhood, if the
board appears to need a score, rank or band to order itself, if a report seems to need to reach
a system outside the platform, or if AC-007 appears to require deleting or overwriting a report
rather than attaching it to an existing job.

---

> Written from: blueprints/02-tasks/02-task-files/TASK-001.md
