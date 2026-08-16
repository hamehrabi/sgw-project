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
| TASK-006 | Re-rank on a forecast change, keeping the previous order | REQ-F-004, AC-005 | P1 | TASK-003 | **In review** | agent | ATEST-005, ITEST-004 |
| TASK-007 | Record a crew placement against the ranking | REQ-F-005, BR-001 | P1 | TASK-003 | **In review** | agent | E2E-001, FTEST-005 (the placement half) |
| TASK-008 | Dismiss a false alarm in one action | REQ-F-008, REQ-F-009, AC-008 | P1 | TASK-005 | **In review** | agent | UTEST-011 |
| TASK-009 | Switch between several loaded storms | REQ-F-010 | P2 | TASK-002 | **In review** | agent | ITEST-005 |
| TASK-010 | Wire the **remaining** fitness function into the build gate | FF-003 | P1 | — | **Done** | agent | — (the register is the assertion) |

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

**The re-review happened on 2026-08-16 and the decision was Block again.** The gate was green —
264 tests over three runs, no red — and the CHG-018 ordering fix held. But **done criterion 3
was not met**: `unique (scenario_id, location_key)` refuses only a byte-identical key, so the
case- and spacing-insensitivity that *defines* "the same location" lived only in
`store/dispatch.py`, and a second job for one neighbourhood inserted directly against the
database was **accepted**. That is this log's pre-declared Block condition for the second review
running. Two smaller failures — the durable `seq` order asserted only inside one process
lifetime, and a clause of the store's location check that no test ever violated — and one new
proposed entry, **CHG-022**. All four checks and their mutations are in `review-log.md`.

**All four findings and both observations were fixed the same day, and TASK-005 is still not
Done.** Migration 009 puts the normalisation in the schema (**CHG-023**): `repair_jobs` refuses
a `location_key` that is not already lower-cased, trimmed and singly-spaced, so the unique
constraint has no second spelling left to miss. CHG-022 is implemented. The restart the durable
order was never crossed is now crossed by three cases. Writing the missing test for the
unexercised length clause **found that clause was also wrong** — SQLite's `trim()` strips spaces
only, so a tab-and-newline location was storable while a spaces-only one was refused — and 009
closes that too. **CHG-024** records the `on delete cascade` observation with its alternatives
rather than changing it inside a remediation for something else. Suite 294 + 1 skipped over four
runs, whole gate green, every fix mutation-checked (`TASK-005.md`, *What the third review
found*). **TASK-006 must not be started on the assumption that TASK-005 is accepted** — three
reviews have each found something the previous one did not.

**TASK-006 is built and In review, and it was started without assuming TASK-005 is accepted** —
it touches none of TASK-005's tables and none of its code. `TASK-006.md` is written, ATEST-005
and ITEST-004 exist as 25 executable cases, migration **010** is shipped with an up and a down
(008 and 009 were already taken by TASK-005's two remediations), and the whole gate is green.
**Every one of the 25 cases was mutation-checked and one of them was wrong** — the store-level
*never rewrites n* test raised the right exception type for the wrong reason, and passed with
the new trigger removed. It is fixed and now reads the rule out of the refusal.

**Two change entries were opened when TASK-006 was built, bringing the total to eleven at that
point, and none is accepted.**
**CHG-025** (a scenario's forecast series had nowhere to live, and nothing decided what "the
next forecast change" is — `weather.csv`'s `valid_time` column and the ~5,000 forecast rows the
fixture is sized at were parsed and thrown away) and **CHG-026** (nothing stopped an earlier
revision being rewritten: `unique (scenario_id, asset_id, forecast_revision)` refuses a *second*
row and says nothing about an `UPDATE` to the first, so AC-005's *"the previous order remains
retrievable"* rested on no code happening to issue one).

**TASK-006 was reviewed on 2026-08-16 by a run that did not write it, and the decision was
Block.** The gate was green — 323 tests over **four** clean runs, `ruff`, six fitness functions,
ten evals, `tsc`, `lint`, `build` and 14 Playwright specs — and **three of four directed checks
failed**, each confirmed by a mutation the gate did not notice. Criterion 11's restart test
asserts the pointer and the two stored orders and **nothing about the forecast values**: with the
cells non-durable, a restarted application re-ranks the whole storm to `ranked: 0, unscored: 5`
and all 25 cases stay green. CHG-025's *"numbered from 0 in chronological order"* is asserted by
nothing — the fixture's forecast times are already in file order, so numbering by file order
passes all 323, and on a file that is not pre-sorted the storm is walked **backwards** through
its own forecasts. Criterion 12 is covered by nothing executable — no browser case was added,
deleting the whole revision list leaves the frontend gate green, and in a real browser
`ForecastRevisionControl` offers revisions that have no ranking, which puts the entire screen
into an error state it never leaves. The store/service check **held**, with two invariants named
as observations. No finding needs a specification decision, so **no change entry is raised** and
the eleven proposed entries stand unchanged. All four checks and their mutations are in
`review-log.md`.

**All three findings and all three observations were fixed the same day, and TASK-006 is still
not Done.** The chronology now rests on a fixture where the answers **differ**:
`storm-with-a-forecast-change/weather.csv` lists its three forecast times 06:00, 12:00, 00:00, so
file order, text order and chronological order are three different answers and a new unit file
names all three — the mutation that used to leave 323 green now fails **17** tests. The restart
case compares the whole ranking rather than the order, so the per-connection cells mutation fails
both restart tests instead of none. Criterion 12 has its first browser case, and the defect
behind it is fixed in the **response**: `forecast_revisions[]` carries `ranked` (**CHG-027**), the
control disables a revision that has no order behind it, and `ScenarioView`'s three reads settle
independently so one failed read is one failed panel rather than a blank screen with
accept/change/reject still on it. Migration **011** puts the rest of *never rewrites n* in the
schema with two further keys (**CHG-028**) — and the foreign key the review named was written,
run and **withdrawn in writing**, because it makes 010's rollback destroy every stored ranking.
PTEST-001 measures the endpoint REQ-NF-001 actually names, and migration 010's backfill dating is
now loud instead of silent. Suite **346 + 1 skipped over four runs**, whole gate green, every fix
mutation-checked (`TASK-006.md`, *What the review found, and what was done about it*).

**Thirteen change entries are open and none is accepted**, after **CHG-027** (a forecast the
prepared file carries is not the same thing as a revision that can be read back, and one response
reported them as one list) and **CHG-028** (three invariants on `risk_scores` the store could hold
and did not — delete-and-reinsert, a ranking of a forecast that does not exist, and CHG-019's
remaining existence-not-membership key).

**TASK-007 is built and In review, and it was started without assuming TASK-005 or TASK-006 is
accepted** — it adds no table, changes no existing one, and touches neither task's code except to
extend the migration round-trip test that its own migration reorders. `TASK-007.md` is written,
E2E-001 exists as an API half and a browser half, migration **012** is shipped with an up and a
down (009, 010 and 011 were already taken by the two previous remediations), and the whole gate is
green. **Every case written for it was mutation-checked, and two of the mutations were themselves
wrong before they were right** — one anchored on a `setState({ stage: 'error' … })` that turned out
to be the *validation* branch rather than the `catch` branch, and one dropped a
`decision_records` trigger three lines before the same file re-asserted it. A mutation that does
not mutate reports a clean bill, which is the third and fourth time this repository has recorded
that trap. **One directed check found a real weak assertion:** removing the unknown-storm lookup
altogether left `test_the_endpoint_refuses_what_the_contract_says_it_refuses` green, because the
request was refused three checks later for having no ranking and the test read only the status
code. It now reads the refusal out of the message.

**A fourteenth change entry is open, and it is the first raised against TASK-007.** **CHG-029** —
`decision_records.kind` has permitted `'placement'` since migration 006 with no writer, no reader
and no decided shape, while `product-spec.md` §10 requires a placement to be *traceable to the
ranking and forecast revision it was made against*. The payload's shape, its subject, and a
`before insert` guard that refuses a placement naming an asset that is not on that ranking are all
decided there, along with the two alternatives that were declined in writing: a `placements` table
(it would split one decision across an append-only table and an ordinary one) and a rebuild of
`decision_records` to carry a `check` (it cannot be done without dropping both append-only
triggers, which ADR-004 forbids).

**TASK-009 is built and In review, and it was started without assuming any earlier task is
accepted** — it adds no table, and the only existing code it changes is what the switcher needs:
one column's meaning, one list read, and one order. `TASK-009.md` is written, **ITEST-005** exists
as 22 executable cases, migration **013** is shipped with an up and a down (010 and 011 went to
TASK-006 and 012 to TASK-007, so the number the brief reserved had drifted for the third time),
and the whole gate is green — suite **450 + 1 skipped over three runs**, `ruff`, six fitness
functions, ten evals, `tsc`, `lint`, `build` and **32** Playwright specs.

**Every case written for it was mutation-checked — 40 mutations — and five of them found a test
that could not fail.** The store's `asset_id` tiebreak on the ranking page order was invisible to
the whole suite, because each of the three shipped fixtures has exactly *one* unscored asset and
`rank is null, rank` is already total for them; the case that sees it now writes several unscored
rows directly, in an order that is not their asset-id order. `asset_count` was asserted as
`> 0`, so counting the whole database passed. `ranked` was asserted only where it was true.
`ScenarioView`'s clearing-on-switch was covered by an assertion the loading state satisfied on its
own, so the panels that actually fail to clear — the forecast control and the staleness banner,
both drawn from `scenario` — went unchecked. And a mutation of the down migration that added
`drop trigger` four lines above the file's own re-assertion **did not mutate**, which is the fifth
time this repository has recorded that trap.

**Three change entries are open against this task and none is accepted.** **CHG-030** (nothing
listed the loaded storms, so the component whose whole purpose is choosing among them had nothing
to choose from — CHG-009's shape, for the third time), **CHG-031** (`scenarios.source_note` was
holding a SHA-256 digest, because the content key §5's idempotency rule turns on had no column of
its own — and that rule lived in one service-layer lookup a direct insert walked straight past)
and **CHG-032** (`scenarios` had no total order, so a list of storms loaded inside one clock tick
came back in coin-flip order — CHG-018's decision, on the fourth table).

**TASK-008 is built and In review, and it was started without assuming any earlier task is
accepted** — it adds no table, and the only existing code it changes is what a dismissal needs:
one status constant moved into the store, one `_append` gaining the ability to write inside a
caller's transaction, and one report row on the board gaining a control. `TASK-008.md` is
written, **UTEST-011** exists as 44 executable cases, migration **014** is shipped with an up and
a down (010 and 011 went to TASK-006, 012 to TASK-007 and 013 to TASK-009, so the number the
brief reserved had drifted for the fourth time), and the whole gate is green — suite **499 + 1
skipped**, `ruff`, six fitness functions, ten evals, `tsc`, `lint`, `build` and **36** Playwright
specs.

**Every case written for it was mutation-checked — 20 mutations — and the most useful ones were
the two that proved a refusal was being read for the right reason.** With
`decision_records_dismiss_shape` removed, the actorless-dismissal case still raised
`IntegrityError` (migration 006's own check catches it) and the test went red anyway, because it
reads the sentence rather than the exception class — the discipline `review-log.md` recorded
after `POST /placements` answered `404` for two different reasons. And a `when` clause pointed at
the wrong status — *present and wrong* rather than absent — turned **27** tests red including the
silent case, where its absence turns only 3 red. The one-argument `trim()` mutation reproduced
CHG-023's exact hole on the new column: `'   '` refused, `char(9)||char(10)` **stored**.

**Three change entries are open against this task and none is accepted.** **CHG-033** (`is not
null` is satisfied by a reason that is not one — an empty, whitespace-only or untrimmed string
was a storable reason for a dismissal, which is CHG-023's hole in the same table one column
over), **CHG-034** (a dismissal could be rewritten by a direct `UPDATE`, so *who dismissed it and
why* meant *whoever wrote it last* — CHG-026's finding one table over) and **CHG-035**
(`decision_records.kind` has permitted `'dismiss'` since migration 006 with no writer, no reader
and no shape, while AC-008 requires **any** human decision to be appended — the third instance of
CHG-021's pattern, after `duplicate` and `placement`).

**TASK-008 was reviewed twice on 2026-08-16, blocked both times, and the second review found the
tree byte-identical to the first — so seven findings stood open at once.** The Block, in both
rounds, was done criterion 7: *exactly one `decision_records` row of kind `dismiss`* lived in the
endpoint's `409` branch and one `where` clause, and with both removed an **identical** retry was
answered `201` twice and left two audit rows for one human decision. The re-review added that a
test *required* that behaviour — inserting a second `dismiss` row directly and asserting
`len(rows) == 2` — so the fix had to correct an assertion before it could add a rule. It also
found the first defect in this repository that needed **no mutation at all**: a dismissal reason
of one no-break space, em space, zero-width space or U+FEFF was answered `201` and stored, because
what counts as whitespace was written three times and the strictest of the three was the browser's.

**All seven findings and both observations are fixed, and TASK-008 is still not Done.** Migration
**015** puts *one human decision, one audit row* in the store as a partial `unique` index that
creates no table and drops no trigger (**CHG-036**), and replaces the six-ASCII whitespace
alphabet with one list held identically by the schema, `store/dispatch.py` and
`frontend/lib/dismissal.ts`, tied by a test that fails when any two disagree (**CHG-037**). The
same alphabet closes the identical hole in `damage_reports_location_is_a_neighbourhood`, which was
being held shut by `json.dumps`' `ensure_ascii` default one module away. The `coalesce` clause now
has the state it was written for — a report belonging to no repair job, dismissed through the
endpoint — the `dismiss` row is asserted at `GET /scenarios/{id}/decisions`, the storm clause has a
case of its own, the dismissal's area figure has UTEST-012's three-way assertion, and the bound's
third and fourth copies are tied to the server's. **One defect was found while fixing and is in
neither review:** the browser suite was racing itself — `fullyParallel: false` keeps one *file*
serial while seven files ran in seven workers against one SQLite database, so ATEST-007's
empty-board case had been racing TASK-008's first case ever since TASK-008 was written, and won
only by luck. Suite **534 + 1 skipped**, whole gate green, every fix mutation-checked
(`TASK-008.md`, *What the two reviews found, and what was done about it*).

**Twenty-two change entries are open and none is accepted**, after **CHG-036** and **CHG-037** —
and **two of them contradict each other**: CHG-035 says a dismissed report and its audit row
*"can never disagree — neither can move afterwards"*, while CHG-034 says the narrowness that still
lets a direct `update` move that report's `location` and `repair_job_id` is deliberate. Whoever
decides them should see both sentences.

**The ordering defect was never TASK-005's alone**, which is why this row matters to TASK-004 as
well: `decision_records` has been intermittently mis-ordered since migration 006, and
`latest_recommendation` could return the wrong recommendation outright. That is fixed by the
same migration.

**Nine change entries are open against this task and none is accepted.** **CHG-016** (no endpoint
creates a damage report), **CHG-017** (`repair_jobs` had nowhere to keep the location it
answers, and `damage_reports.location` had no fixed resolution), **CHG-018** (a monotonic `seq`,
because a timestamp is not a total order), **CHG-019** (composite foreign keys — a foreign key
proved an asset existed, never that it was in this storm), **CHG-020** (a job's location
survives the dismissal of the report it came from), **CHG-021** (`duplicate` given a reader),
**CHG-022** (a damage report belonging to no repair job is on no screen and in no figure —
raised at the third review, **now implemented**), **CHG-023** (the store, not the service, is
what decides that two spellings are one location — and one length bound governs both columns
and the service constant) and **CHG-024** (what happens to a damage report when the asset it
names is deleted; the cascade is kept and the alternatives recorded). All are **proposed**: the build could not proceed
without deciding them, and none of the decisions is the agent's to accept. The row above gains **REQ-NF-007** and **UTEST-012** for a
different reason — `traceability.md` already puts that requirement on TASK-002 and TASK-005, and
this is the first task in which a damage location exists to be aggregated, so it is the first
task where the rule can be broken.

**TASK-010 is Done, and FF-003 is wired — the question it was set was whether it could be.**
`fitness-functions.md` said clause (a) *cannot fail*: nothing on a render path opens a file, so
removing one changes nothing an assertion can see. That is still true of the clause as CHG-013
read it, and the honest answer turned out to be that the failure comes from the **other**
direction. Clause **(c)** can fail and was made to: a `fs.readFileSync` in `app/page.tsx` — a
server component, a real Next.js render path — leaves `tsc`, `lint`, `build` and all 36 browser
cases **green**, and `views.integrity()` reading `manifest.json` on the render path of
`GET /scenarios/{id}` leaves all **534** tests green. Clause **(a)** can fail too, once clause
(b) makes the removal observable: `if not integrity["intact"]: rows = []` in the ranking read
empties the risk list on a lost `outages.csv` with the whole suite still green — the empty screen
CLAUDE.md forbids reading as safety. **Nothing in `backend/` or `frontend/` was changed by this
task**; every application edit in it was a mutation, applied and reverted.

**The check's own two ways of passing for nothing are guarded, and the guards were mutation-checked
too.** The storm's five files must be on disk before their absence from the reads means anything;
the recorder is shown a real source file through all three of Python's open doors before its
silence is believed. And the route walk found the lesson `AGENT.md` recorded on 2026-08-16 while
this check was being written: a flat read of `application.routes` sees four documentation routes
and **none** of the seventeen endpoints, because this FastAPI wraps `include_router` in a
`_IncludedRouter` whose own `path` is `None`. Five named routes must now be in what the walk found.

**One change entry is open against this task and it is not accepted.** **CHG-038** — moving
FF-003's `Runs` cell required deciding three things the register does not decide: what *open every
screen* is when the views are in another process, how clause (a) is measured now that its original
sense cannot occur, and — the one that is a real contradiction if left undecided — that *reads a
source file* means an `open` and not a `stat`, because `integrity()` must stat all five files on a
render path to satisfy clause (b). Twenty-three entries are now open and none is accepted.

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

## Only TASK-001 is written as a file, on purpose — and every task since has written its own

`02-tasks/02-task-files/` now holds ten, one per task, each written when its task was picked up.
The paragraph below is why there was one at the start, and it still governs: the detail of a task
depends on what the task before it produced.

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
