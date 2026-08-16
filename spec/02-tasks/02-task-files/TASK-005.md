# TASK-005: Dispatch board — one shared damage and repair list

> Written from the template in `TASK-001.md` when the task was picked up.

---

**Task ID:** TASK-005
**Task title:** Dispatch board — one shared damage and repair list
**Priority:** P1
**Status:** **Done** — accepted 2026-08-16 at a fourth review, by a run that neither wrote, fixed nor previously reviewed this task (`review-log.md`; the Q-026 conflict is recorded in the row rather than left to the signature). Built 2026-08-16, blocked at a second review the same day, remediated, blocked again at a third, and those four findings and two observations fixed (*What the third review found*, below). The accepting round's directed check — *which refusal, not how many* — **held**, and one observation was fixed in place: `test_an_unknown_storm_is_404_rather_than_a_new_board` asserted a status code and nothing else, so it went red for the `500` the mutation produced rather than for the rule. It reads the sentence now. Nine change entries are open against this task and **none is accepted**: **CHG-016**, **CHG-017**, **CHG-018**, **CHG-019**, **CHG-020**, **CHG-021**, **CHG-022**, **CHG-023**, **CHG-024**. **Done is not the same as decided.**
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
   figure it logs is an aggregate for that neighbourhood (REQ-NF-007, UTEST-012) — **neither
   the whole storm's figure, which is coarser, nor one asset's, which is finer and is the thing
   the requirement exists to forbid.** All three must be different numbers in the fixture.
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
11. **A damage report may only name an asset and a repair job from its own storm, and the
    *store* is what refuses the rest** (ADR-002, CHG-019). Asserted by an insert issued
    directly against the database, never through the endpoint.
12. **Every chronological read is ordered by a key that is total** (CHG-018). Asserted with the
    clock frozen, so a tie is certain rather than a one-in-two chance — and the suite is run
    more than once before the gate is called green.
13. `DispatchBoard` is driven in a browser: two reports at one location under one job, and an
    empty board that reads *no damage reported* (done criterion 7, `e2e/ATEST-007.spec.ts`).

## What the second review found, and what was changed

**The gate was not green, and four of the ten criteria above were not proven by anything.** The
review was run by a later agent invocation that had not written this code — not independence
(Q-026), but a reader who did not already know where the code was careful. Its four checks are
in `review-log.md`; three failed and one held with two dead sub-assertions. Every fix below was
mutation-checked: the behaviour broken, the named tests seen red, the break reverted.

| Finding | Fix | Made red by |
|---|---|---|
| **The gate is not green.** 5 of 15 clean `pytest` runs red. Every chronological read was `order by <timestamp>, id`; the clock resolves to ~15.6 ms and `id` is a random UUID. Not this task's alone — `decision_records` had it from migration 006, and `latest_recommendation` could return the wrong row outright. | **CHG-018**: a monotonic `unique` `seq` on `repair_jobs`, `damage_reports` and `decision_records` (migration 008). Reads order by it. | Four new cases with the clock **frozen**, so the collision is certain rather than likely: ATEST-007 (12 reports, 6 jobs) and ITEST-002 (25 records, and the `latest` pick). Each asserts one shared timestamp first, so the tiebreak is provably what is under test. |
| **Block — a rule in the service layer the store could refuse.** `api/dispatch.py`'s `find_asset` lookup was the only thing scoping a report's `asset_id` to its own storm. Disabling it left 248 tests green. | **CHG-019**: composite foreign keys over `(id, scenario_id)`, with the unique parent keys SQLite needs (migration 008). The lookup stays as the legible 400 in front of the constraint. | Three ITEST-003 cases issuing the insert **directly against the database** — cross-storm asset, cross-storm job, and the permitted case beside them. |
| **Done criterion 5 unasserted in both directions.** Every UTEST-012 case filed into one neighbourhood with no asset, so the area figure, the storm figure and the per-asset figure were the same number. | The fixtures keep the three apart: 5 in the storm, 3 in the area, 1 for the asset. | Both mutations the review found green — count the storm, count per asset — now fail two tests each. |
| **A described state with nowhere to render.** A job whose only report is dismissed came back as `location: {"neighbourhood": null}`, `report_count: 0`. | **CHG-020**: the location is the first report **filed**, whatever its status — which is what CHG-017 already said — plus `dismissed_report_count`. | Two ITEST-003 cases, one of them the silent case: a dismissed report must not take a *neighbouring* job's location with it. |
| Minor — `repair_jobs_scenario_status` was named by PTEST-002 and guarded by nothing (two other indexes serve the query). | The plan assertion pins the index **name**. The new parent-key indexes are ordered `(id, scenario_id)` so they cannot serve `where scenario_id = ?` and re-create the problem. | Dropping either named index now turns the query-plan test red. |
| Minor — `statements_during` compared two counts with no positive guard; `0 == 0` would pass. | The helper asserts it captured something, and the test asserts **both board statements are in the list it counted**. | Silencing the tracer turns it red. |
| Minor — `DispatchBoard` had no executable coverage; done criterion 7 was satisfied by reading the source. | `frontend/e2e/ATEST-007.spec.ts` — five browser cases against both processes. | — (new coverage, not a fix) |
| Minor — `damage_reports.status` permits `duplicate` with no reader and no writer. | **CHG-021**: a duplicate stays on the board carrying its status, and is not counted as open work in its area. | Marking a report `duplicate` changes the area figure and the board's rendering, both asserted. |

**Nothing here weakened a test.** UTEST-012's refusal cases were *strengthened* in passing: they
matched bare `IntegrityError`, and adding `seq not null` made every one of them raise for the
wrong reason — they now match `CHECK constraint failed`.

## What the third review found, and what was changed

**The full gate was green and three of four directed checks still failed** — 264 tests over
three runs, six fitness functions, ten evals and fourteen browser cases, all passing while a
second crew could be sent to one neighbourhood. The reviewer neither wrote nor fixed this task.
Its four checks are in `review-log.md`. Every fix below was mutation-checked: the behaviour
broken, the whole suite run, the named tests seen red, the break reverted, `git status --short`
empty after each one.

| Finding | Fix | Made red by |
|---|---|---|
| **Block — done criterion 3 was not met.** `unique (scenario_id, location_key)` refuses a **byte-identical** key; the casefold-and-collapse that *defines* "the same location" lived only in `store/dispatch.py`. A direct insert of `Northgate` beside a stored `northgate` was accepted, and so was `north  gate`. The suite's whole reach was one test, and it files both reports **through the endpoint**. | **CHG-023**: migration 009 rebuilds `repair_jobs` with a check that the stored key is **already normalised** — lower case, trimmed, no double space, no tab or newline. The only key the table will hold is the one `location_key()` produces, so the unique constraint has no second spelling left to miss. `collate nocase` was the review's named remedy and is **declined with its reasons** — it is unreachable beside the check, and unsound alone. | Six new ITEST-003 cases, one per spelling, each issuing the insert **directly against the database**; plus the silent case beside them — two genuinely different neighbourhoods are still two jobs. Removing the check turns eight tests red. |
| **The durable order was asserted only inside one process lifetime.** `AGENT.md`'s second lessons row, unapplied to the state this task created. The reviewer's mutation — a counter held beside the connection — left all 264 tests green while a restart made the first damage report anyone filed a `500`. | Nothing in the store changed: `seq` was already taken from the table inside the insert. What was missing was the assertion. `test_ADR-002_sequence_survives_restart.py` builds a second application over the same database file, with `conftest.build_application`, written for TASK-001's review and never used for this state. | Three cases: a report can still be filed after the restart; the board's order spans it and the numbers keep climbing; and `decision_records` — the half that carries regulatory evidence — does the same. The reviewer's mutation now fails two of them, and the same mutation in `store/decisions.py` fails the third. |
| **A damage report belonging to no repair job was on no screen and in no figure.** `board_body` grouped by `repair_job_id` and emitted one item **per job**, so a null link fell into a bucket nothing read; `open_reports_in_area` was an **inner** join and missed it too. Two open reports in one neighbourhood logged `open_reports_in_area=1`. | **CHG-022**, implemented: the board response carries `unattached_reports`, both counts include them, the area figure left-joins and falls back to the report's own neighbourhood, and `DispatchBoard` renders the group. The empty state now means *nothing on the board*, not *no job on it*. | Three ITEST-003 cases including the one that has no job at all, so the counts must carry the report; two UTEST-012 cases with three different numbers — 3 open in the storm, 2 in the area, 1 of them attached — and the silent case, an unattached report in a **different** neighbourhood that must not be counted here. |
| **One clause of the CON-003 location check was exercised by nothing.** `length(trim(…)) between 1 and 120` — no empty neighbourhood, no whitespace-only one, no over-length one, at the store or at the endpoint. The bound was three hard-coded copies with nothing tying them together. | **CHG-023(b)**: four new refusal cases at the store, the boundary asserted from the permitted side, the endpoint's `400`-not-`500` asserted at exactly one over — and `test_one_bound_governs_a_neighbourhoods_length`, which reads the bound out of `sqlite_master` and requires both schema copies to equal `NEIGHBOURHOOD_MAX`. Writing them found a real hole: `trim()` strips **spaces only**, so `"\t\n"` was a storable location while `"   "` was not. Migration 009 closes it. | The review's own mutation — relax the schema to `100000` **and** raise the constant to `5000` — now fails three tests. The other half of it, schema at 120 with the constant at 5000, fails three more, including the `400` that had become a `500`. |
| Observation — migration 008 changed `damage_reports.asset_id` from `on delete set null` to `on delete cascade`, contradicting §4 the day anything deletes a single asset. | **CHG-024**, proposed: the cascade is kept, and the three alternatives are recorded with why each is worse or unavailable (SQLite cannot null a composite child key by halves; `no action` can break §7.2's scenario delete on an undefined cascade order; reverting the composite key reinstates the CHG-019 Block). What is owed is a decision about §4's sentence, which is about an **unmatched** report rather than a deleted asset. | — (no code change; the entry is the record) |
| Observation — `STEST-001`'s `DATA_ROUTES` never listed `POST /api/v1/scenarios/{id}/damage-reports`, so done criterion 9's first half rested on the generic unknown-path case. | The row is added, **and the drift is closed rather than patched**: a new test reads the published OpenAPI paths and requires every endpoint the application exposes to be either in `DATA_ROUTES` or in a short, reasoned `PUBLIC` list. A future endpoint that nobody guards is now red. | Removing the row turns the new test red, naming the endpoint. |

**Nothing here weakened a test.** Two were strengthened in passing: `DATA_ROUTES` gained a
coverage guard it never had, and UTEST-012's parametrised refusal list gained the four shapes
that reach the clause nothing reached.

## Tests to run or create

| Test ID | Defined in |
|---|---|
| ATEST-007 | `03-tests/02-functional/acceptance-tests.md` — API level, plus `frontend/e2e/ATEST-007.spec.ts` for done criterion 7 |
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
