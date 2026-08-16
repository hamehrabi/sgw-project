# Review Log

> Source: Ch. 4 §4.3 — `/review` folder: "Stores review notes and decision records."
> A running record of what was **accepted, rejected, or changed**, and why.

---

| Date | Item reviewed | Task / Req | Reviewer | Layers checked | Findings | Decision | Follow-up |
|---|---|---|---|---|---|---|---|
| 2026-08-15 | TASK-001 output — the FastAPI service (`api`, `store`, and empty `scoring`/`loader`), the Next.js `views`, 001 migration, seeding command | TASK-001 / REQ-NF-002, REQ-R-001 | The developer (**also the author** — see the note below) | Requirement fit · Architecture fit · Security & validation · Test evidence · Change scope | Three specification gaps, all raised as change entries rather than guessed: **CHG-008** (`sessions` table), **CHG-009** (`GET /api/v1/auth/session`), **CHG-010** (FF-002 was a gate that could not fail). Four directed checks run at review, all passing — see below. No finding against the code. | **Accept with follow-up** | TASK-002 wires FF-001 and FF-006; the rate limiter's in-memory state is revisited when the platform leaves SGW's network |

| 2026-08-15 | TASK-002 output — the loader and its seven defect rules, the fixture, migrations 002–004, the upload endpoint and parse job, both read endpoints, four views | TASK-002 / REQ-F-001, REQ-F-010, REQ-NF-003 | The developer (**also the author** — same Q-026 conflict as TASK-001) | Requirement fit · Architecture fit · Security & validation · Test evidence · Change scope | **Two defect checks were firing for the wrong reason** — found by the directed checks, not by the suite. Three change entries raised: CHG-011, CHG-012, CHG-013. E2E-002 owed. | **Accept with follow-up** | Playwright setup, then E2E-002; TASK-003 wires FF-005 and FF-007 |

| 2026-08-15 | TASK-003 output — the deterministic scorer, migration 005, the risks endpoint, `RiskList` and `ReasonPanel`, the eval harness, the demo-scale generator | TASK-003 / REQ-F-002, REQ-F-003, BR-002 | The developer (**also the author** — same Q-026 conflict) | Requirement fit · Architecture fit · Security & validation · Test evidence · Change scope | **The eval harness found a real disclosure gap on its first run**: 47 of 185 stale ranks said nothing about resting on data over a year old. CHG-014 raised for two reference values ADR-007 compares against but never supplies. | **Accept with follow-up** | The recall floor stays unearned (A7); `reasons_are_faithful` is owed a human pass |

| 2026-08-15 | TASK-004 output — migration 006 with both triggers, `store/decisions.py`, the decision and decision-record endpoints, `RecommendationDecision`, FF-004 and FF-005 wired | TASK-004 / REQ-F-006, REQ-F-009, BR-001, BR-004 | The developer (**also the author** — same Q-026 conflict) | Requirement fit · Architecture fit · Security & validation · Test evidence · Change scope | All four checks held. **One acceptance criterion could not be met as written** — AC-009's refusal record had nowhere to live — raised rather than quietly dropped, and settled by the developer as **CHG-015**. | **Accept** | TASK-010 is now FF-003 alone |

| 2026-08-16 | TASK-005 output — migration 007 (`repair_jobs`, `damage_reports`), `store/dispatch.py`, the report and board endpoints, `DispatchBoard`, four executable tests | TASK-005 / REQ-F-007, REQ-NF-007, AC-007 | The developer (**also the author** — same Q-026 conflict, fifth time) | Requirement fit · Architecture fit · Security & validation · Test evidence · Change scope | **One of the four tests written for this task could not fail, and the mutation check is what found it.** Two specification gaps raised and left **proposed** rather than self-accepted: **CHG-016** (no endpoint creates a damage report) and **CHG-017** (`repair_jobs.location_key` + the resolution of `damage_reports.location`). | **Accept with follow-up** | CHG-016 and CHG-017 need a human decision; TASK-008 writes the dismissal against columns 007 already carries |

| 2026-08-16 | TASK-005 output, **reviewed a second time against its own done criteria** — migration 007, `store/dispatch.py`, `api/dispatch.py`, `views.repair_job_item` / `board_body`, `DispatchBoard`, and the four executable tests | TASK-005 / REQ-F-007, REQ-NF-007, AC-007, ADR-002, CON-003 | A later agent run, which **did not write TASK-005** — but author and reviewer are still the same process (**Q-026**, see the note below) | Requirement fit · Architecture fit · Security & validation · Performance · Test evidence · Change scope | **The gate is not green.** Two tests fail intermittently on an unmodified tree — **5 of 15 clean `pytest` runs were red** — from a single root cause that reaches `decision_records` as well as the board. **Three of four directed checks failed**, each confirmed by a mutation the suite did not notice: REQ-NF-007's *aggregate for that neighbourhood* is unasserted in **both** directions; the storm-scope of a report's `asset_id` lives only in service code, which is this log's pre-declared **Block** condition; and a repair job's location has nowhere to live once its only report is dismissed. No finding requires a specification decision, so **no change entry is raised** — CHG-016 and CHG-017 remain the only two proposed. | **Block** | Fix the ordering tiebreak first — it is `decision_records`' order as much as the board's; then move the scope rule into the schema; the third finding is evidence bearing on the still-open **CHG-017** |

| 2026-08-16 | **TASK-005 remediation** — migration 008, `store/dispatch.py`, `store/decisions.py`, `api/views.py`, `api/dispatch.py`, `lib/api.ts`, `DispatchBoard.tsx`, four executable test files and a new Playwright spec | TASK-005 / REQ-F-007, REQ-NF-007, REQ-F-009, AC-007, ADR-002, BR-004 | The agent that fixed the Block — **not a reviewer, and this row is not an acceptance** (see below) | Requirement fit · Architecture fit · Security & validation · Performance · Test evidence · Change scope | All eight defects closed, each with the mutation that now makes it red recorded in `TASK-005.md`. **The ordering fix reaches further than TASK-005**: `decision_records` had been intermittently mis-ordered since migration 006 and `latest_recommendation` could return the wrong row outright. Four change entries raised and left **proposed**: **CHG-018** (a monotonic `seq`), **CHG-019** (composite foreign keys — the Block), **CHG-020** (a job's location survives its report's dismissal), **CHG-021** (`duplicate` given a reader). Suite 264 + 1 skipped, run 12 times with no red. One instance of CHG-019's shape is knowingly **not** fixed and is named in the entry: `risk_scores.asset_id`. | **Fixed — awaiting re-review** | The six proposed entries need a human decision; TASK-006 is next and must not be started on the assumption that this is accepted |

| 2026-08-16 | **TASK-005 re-reviewed after remediation**, against its own done criteria — migration 007 and 008, `store/dispatch.py`, `store/decisions.py`, `api/dispatch.py`, `api/views.py`, `DispatchBoard.tsx`, and the five executable test files including `e2e/ATEST-007.spec.ts` | TASK-005 / REQ-F-007, REQ-NF-007, AC-007, ADR-002, CHG-018 | A third agent run, which **neither wrote nor fixed** TASK-005 — but author, fixer and reviewer are still the same process (**Q-026**, see the note below) | Requirement fit · Architecture fit · Security & validation · Performance · Test evidence · Change scope | **The full gate is green — and three of four directed checks failed, each confirmed by a mutation the gate did not notice.** `pytest` 264 + 1 skipped, run **three** times with no red, so the CHG-018 ordering fix holds. **Done criterion 3 is not met**: `unique (scenario_id, location_key)` refuses only a byte-identical key, so the case- and spacing-insensitivity that *defines* "the same location" lives only in `store/dispatch.py` — this log's pre-declared **Block** condition, one review after the same condition blocked this task. Two smaller failures: the durable order CHG-018 introduced is asserted only inside one process lifetime, and the store's own location check has a clause no test ever violates. One specification gap raised and left **proposed**: **CHG-022** (a damage report belonging to no repair job is on no screen and in no figure). | **Block** | Put the normalised key in the schema, then close CHG-022; the seven proposed entries need a human decision; TASK-006 must not be started on the assumption that this is accepted |

| 2026-08-16 | **TASK-005 remediation, second time** — migration 009, `store/dispatch.py`, `api/views.py`, `api/dispatch.py`, `lib/api.ts`, `DispatchBoard.tsx`, three executable test files and one new one | TASK-005 / REQ-F-007, REQ-NF-007, AC-007, ADR-002, CON-003, CHG-018 | The agent that fixed the Block — **not a reviewer, and this row is not an acceptance** (see the note under the previous remediation row, which applies unchanged) | Requirement fit · Architecture fit · Security & validation · Test evidence · Change scope | All four findings and both observations closed, each with the mutation that now makes it red recorded in `TASK-005.md`. **The Block is answered in the schema**: `repair_jobs` carries a check that the stored `location_key` is already normalised, so `Northgate`, `north  gate` and a tab all bounce at the database — `collate nocase` was the named remedy and is **declined in writing**, because it is unreachable beside that check and unsound without it. CHG-022 is implemented. Writing the missing test for CON-003's fourth clause **found a further hole in it**: SQLite's `trim()` strips spaces only, so `"\t\n"` was a storable damage location while `"   "` was not; migration 009 closes that too. Suite 294 + 1 skipped, run **four** times with no red; `ruff`, `ci/fitness.py` (6 of 7), `ci/evals.py`, `tsc`, `lint`, `build` and all 14 Playwright specs pass. Two change entries raised and left **proposed**: **CHG-023** (the normalisation and the single bound) and **CHG-024** (the `on delete cascade` observation, kept with its reasons rather than changed inside a remediation for something else). | **Fixed — awaiting re-review** | Nine proposed entries now need a human decision; TASK-006 is next and must not be started on the assumption that this is accepted |

| 2026-08-16 | **TASK-006 output, reviewed against its own done criteria** — migration 010 (`scenario_forecast_revisions`, `scenario_forecast_cells`, `risk_scores_no_update`) and its down migration, `store/forecasts.py`, `store/rankings.py`, `store/scenarios.py`, `api/rerank.py`, `api/scenarios.py`, `api/views.py`, `loader/load.py`, `ForecastRevisionControl.tsx`, the new fixture, and the three executable test files (29 cases) | TASK-006 / REQ-F-004, AC-005, ADR-002, ADR-005, BR-003, CHG-025, CHG-026 | A later agent run, which **did not write TASK-006** — but author and reviewer are still the same process (**Q-026**, see the note below) | Requirement fit · Architecture fit · Security & validation · Performance · Test evidence · Change scope | **The full gate is green — `pytest` 323 + 1 skipped over four clean runs — and three of four directed checks failed, each confirmed by a mutation the gate did not notice.** Done criterion 4 is real: the store refuses the `UPDATE`, and the test reads the rule out of the refusal so it cannot pass for BR-002's reason. **Criterion 11 is half-proven** — the restart test asserts the pointer and the two stored orders and nothing about the forecast *values*; a series whose cells do not survive a restart re-ranks the whole storm to `ranked: 0, unscored: 5` with all 25 cases still green. **CHG-025's *"numbered from 0 in chronological order"* is asserted by nothing** — the fixture's three forecast times are already in file order, so numbering by file order passes all 323, and on a file that is not pre-sorted that mutation walks the storm backwards through time. **Criterion 12 is covered by nothing executable** — no Playwright case was added, deleting the whole revision list leaves `tsc`, `lint`, `build` and all 14 browser cases green, and in a real browser the control offers revisions that have no ranking, which puts the entire screen into an error state it never leaves. Two observations: PTEST-001 measures a proxy for the re-rank rather than the endpoint, and migration 010's backfill dates revision 0 from a different source than the loader does. **No finding requires a specification decision, so no change entry is raised** — the eleven proposed entries stand unchanged. | **Block** | Assert the chronology against an out-of-order fixture; extend the restart case to the forecast values it exists to protect; give `ForecastRevisionControl` a browser case and stop offering a revision that cannot be read; the eleven proposed entries still need a human decision |

| 2026-08-16 | **TASK-006 remediation** — migration 011, the reordered `storm-with-a-forecast-change` fixture, `store/forecasts.py`, `api/views.py`, `lib/api.ts`, `ForecastRevisionControl.tsx`, `ScenarioView.tsx`, four executable test files, one new unit file and the first Playwright spec this task has had | TASK-006 / REQ-F-004, AC-005, ADR-002, BR-003, CHG-025…CHG-028 | The agent that fixed the Block — **not a reviewer, and this row is not an acceptance** (see the note under TASK-005's remediation rows, which applies unchanged) | Requirement fit · Architecture fit · Security & validation · Performance · Test evidence · Change scope | All three findings and all three observations closed, each with the mutation that now makes it red recorded in `TASK-006.md`. **The chronology now has a fixture where the right answer and the wrong one differ**: `weather.csv` lists its three forecast times 06:00, 12:00, 00:00, so file order, text order and chronological order are three different answers and a new unit file names all three — `enumerate(observed)` fails **17** tests and the plain text sort fails the UTC-offset case. **The restart case now compares the whole ranking rather than the order**, so the temp-table mutation that left all 25 cases green fails both restart tests. **Criterion 12 has a browser case**, and the defect behind it is fixed in the response rather than in the screen: `forecast_revisions[]` carries `ranked` (**CHG-027**), the control disables what has no order behind it, and `ScenarioView`'s three reads settle independently so one failed read is one failed panel. Migration **011** puts the other half of *never rewrites n* in the schema together with two further keys (**CHG-028**) — and the foreign key the review named was written, run and **withdrawn in writing**, because it makes 010's rollback destroy every stored ranking. PTEST-001 now measures the endpoint REQ-NF-001 names, and the backfill's dating is loud instead of silent. Suite **346 + 1 skipped over four runs**, `ruff`, `ci/fitness.py` (6 of 7), `ci/evals.py`, `tsc`, `lint`, `build` and all **17** Playwright specs pass. Two change entries raised and left **proposed**: **CHG-027** and **CHG-028**. | **Fixed — awaiting re-review** | Thirteen proposed entries now need a human decision; a re-review should start with the two invariants CHG-028 declines and with `scenarios.forecast_revision`, which can still point at a revision nothing ranked |

| 2026-08-16 | **TASK-008 output, reviewed against its own done criteria** — migration 014 up and down (`damage_reports` rebuilt with `damage_reports_dismissal_is_attributed`; `damage_reports_dismissal_is_final`; `decision_records_dismiss_shape`), `store/dispatch.py`, `store/decisions.py`, `api/dismissals.py`, `api/views.py`, `views/DismissAlarmControl.tsx`, `DispatchBoard.tsx`, `lib/api.ts`, and the three executable files (UTEST-011's 44 cases, TASK-008-AC9, `e2e/TASK-008.spec.ts`) | TASK-008 / REQ-F-008, REQ-F-009, AC-008, ADR-002, ADR-004, CHG-033…CHG-035 | A later agent run, which **did not write TASK-008** — but author and reviewer are still the same process (**Q-026**, see the note below) | Requirement fit · Architecture fit · Security & validation · Test evidence · Change scope | **The full gate is green — `pytest` 499 + 1 skipped, `ruff`, `ci/fitness.py` (6 of 7, FF-006 at 7 of 7), `ci/evals.py`, `tsc`, `lint`, `build` and all 36 Playwright specs — and three of four directed checks failed, each confirmed by a mutation the gate did not notice.** **Criterion 7's *exactly one* row is service code, and that is this log's pre-declared Block condition:** `damage_reports_dismissal_is_final` refuses a *different* second dismissal and **accepts an identical one**, so with the endpoint's `409` branch and `dismiss_report`'s `status <> ?` guard removed a retrying client is answered `201` twice and **two `dismiss` audit rows exist for one human decision** — the failure `api/dismissals.py`'s own docstring says it prevents. No test issues an identical retry; both tests that go red under that mutation retry with different words. **`decision_records_dismiss_shape` has a clause no case violates:** deleting `and r.scenario_id = new.scenario_id` leaves **all 499 green**, and under that mutation a `dismiss` row naming storm A's report is accepted under storm B and served in storm B's `GET /decisions` while storm A's shows it too — the storm-blending bug CLAUDE.md calls a correctness failure, guarded by a clause nothing has ever read back. **REQ-NF-007's area figure is emitted at a second call site and asserted at neither:** replacing the dismissal log's `open_reports_in_area` with a whole-storm count leaves **all 499 green**; UTEST-012's three-way fixture proves the *filing* endpoint and stops at the module boundary. Two observations: CHG-035 states in writing that the report and its audit row *"can never disagree — neither can move afterwards"*, and a direct `update` moves a dismissed report's `location` and `repair_job_id` while the audit row keeps the old ones (CHG-034 says the narrowness is deliberate, so the two proposed entries contradict each other); and `DISMISSAL_REASON_MAX` has a **third** copy in `frontend/lib/api.ts` tied to nothing — set to 8, `tsc`, `lint`, `build` and all 36 browser specs stay green while the field silently truncates a dispatcher's sentence. **No finding requires a specification decision, so no change entry is raised** — CHG-033, CHG-034 and CHG-035 stand proposed, and two of the findings are evidence bearing on them. | **Block** | Put *one human decision, one audit row* in the store (a partial `unique` index on `decision_records (subject_id) where kind = 'dismiss'` needs no rebuild and touches neither append-only trigger); give the scenario clause a case of its own; give the dismissal's area figure the three-way assertion UTEST-012 already has; the twenty proposed entries still need a human decision |

| 2026-08-16 | **TASK-008 re-reviewed against its own done criteria, after the Block above** — and **on the same tree**: `git diff` between the build commit and this one touches `review-log.md` and nothing else, so nothing the previous review found has been remediated. Migration 014 up and down, `store/dispatch.py`, `store/decisions.py`, `api/dismissals.py`, `api/views.py`, `api/scenarios.py`'s decision-record read, `views/DismissAlarmControl.tsx`, `DispatchBoard.tsx`, `lib/api.ts`, and the three executable files | TASK-008 / REQ-F-008, REQ-F-009, AC-008, ADR-002, CON-003, CHG-033…CHG-035 | A third agent run, which **neither wrote TASK-008 nor reviewed it before** — but author and both reviewers are the same process (**Q-026**, see the note below) | Requirement fit · Architecture fit · Security & validation · Test evidence · Change scope | **The full gate is green — `pytest` 499 + 1 skipped over two clean runs, `ruff`, `ci/fitness.py` (6 of 7 wired, FF-006 at 7 of 7, FF-004 refusing a real `UPDATE`), `ci/evals.py`, `tsc`, `lint`, `build` and all 36 Playwright specs — and all four directed checks failed.** Three of the four are new, chosen deliberately away from the previous round. **The Block stands and its mutation reproduces exactly:** with the endpoint's `409` branch and `dismiss_report`'s `status <> ?` guard removed, an **identical** retry is answered `201` twice and leaves **2** `dismiss` rows; the two tests that go red retry with different words and fail on a `500`, not on a duplicate row. New evidence on the same finding: `test_the_store_accepts_a_dismissal_record_that_agrees_with_its_report` does not merely miss *one human decision, one audit row* — it **asserts its absence**, inserting a second `dismiss` row for an already-dismissed report directly and requiring `len(rows) == 2`. **A second clause nothing has ever read back**, and a different one from the previous round: `coalesce(r.repair_job_id, '') = coalesce(…)` exists so a report belonging to no repair job (CHG-022) can be recorded — replacing both `coalesce`s with plain equality leaves **all 499 green**, and under it dismissing an unattached report is a `500` while `DispatchBoard` goes on rendering a `DismissAlarmControl` on every one of them. **The `dismiss` row has a writer and no reader anyone has asked:** `and kind <> 'dismiss'` in `decisions.read_all` leaves **all 499 green** while `GET /scenarios/{id}/decisions` — REQ-F-009's artefact — silently omits every cleared false alarm. **And what counts as whitespace is written three times and the three disagree:** with **no mutation at all**, a dismissal reason of `" "`, `" "`, `"​"` or `"﻿"` is answered **`201`** and stored as the reason, while `'   '` is refused — *the same non-answer wearing a different whitespace character*, CHG-023's own sentence for the third time, on the column CHG-033 was written to close. Beside it, `DISMISSAL_REASON_MAX`'s third copy (`frontend/lib/api.ts`) set to `8` leaves `tsc`, `lint`, `build` and all 36 browser specs green — the previous round's observation, unremediated and re-run. **No finding requires a specification decision, so no change entry is raised** — CHG-033, CHG-034 and CHG-035 stand proposed, and the whitespace hole is evidence bearing on CHG-033 rather than a new entry. | **Block** | The three findings of the previous round, all still open, plus: extend CHG-033's `trim` alphabet past ASCII (or refuse a reason whose characters are all whitespace by a rule that does not enumerate them) and add the case for each; feed the `coalesce` clause the state it was written for and give the board's unattached report a dismissal test; assert the `dismiss` row at `GET /decisions`; tie the frontend's copy of the bound to the server's. The twenty proposed entries still need a human decision |

| 2026-08-16 | **TASK-008 remediation, answering both Blocks at once** — migration **015** up and down, `store/dispatch.py`, `frontend/lib/dismissal.ts` (new), `frontend/lib/api.ts`, `views/DismissAlarmControl.tsx`, `frontend/playwright.config.ts`, `e2e/TASK-008.spec.ts`, `test_UTEST-011_dismissal_never_anonymous.py`, `test_UTEST-012_damage_location_aggregated.py` and `test_TASK-008-AC9_migration_014_up_and_down.py` | TASK-008 / REQ-F-008, REQ-F-009, AC-008, REQ-NF-007, ADR-002, ADR-004, CON-003, CHG-033…CHG-037 | The agent that fixed both Blocks — **not a reviewer, and this row is not an acceptance** (the note under TASK-005's remediation rows applies unchanged) | Requirement fit · Architecture fit · Security & validation · Test evidence · Change scope | **All seven findings across the two rounds are closed, each with the mutation that now makes it red recorded in `TASK-008.md`.** **The Block is answered in the store**: `decision_records_one_dismissal_per_report`, a partial `unique` index that creates no table and drops no trigger (**CHG-036**) — with the two service guards removed, an identical retry is now a `500` and **one** audit row instead of `201` twice and two. The test that *required* the opposite — `len(dismiss_record(connection)) == 2` — was not deleted: its report is dismissed by direct statement, which writes no audit row, so the permitted control is the only row and it proves exactly what it proved before. **The live whitespace hole is closed at the layer ADR-002 names**: one alphabet in `dispatch.BLANK_CODEPOINTS`, repeated in the schema as `char(...)` and in `frontend/lib/dismissal.ts`, with a test that reads all three and fails when any two disagree (**CHG-037**) — and the same alphabet closes `damage_reports_location_is_a_neighbourhood`, whose whitespace-only hole was being held shut by `json.dumps`' `ensure_ascii` default one module away. The bound's third and fourth copies are tied to the server's by a test that walks every `.ts`/`.tsx` file. The `coalesce` clause has the state it was written for — a report belonging to **no repair job**, dismissed through the endpoint — in both directions. The `dismiss` row is asserted at `GET /scenarios/{id}/decisions`. The storm clause has a case of its own. The dismissal's area figure has UTEST-012's three-way assertion, carried across the module boundary. **One defect was found while fixing and is in neither review:** the browser suite was racing itself — `fullyParallel: false` keeps one *file* serial while seven files ran in seven workers against one SQLite database, so ATEST-007's empty-board case was racing TASK-008's first case, which files a damage report; it won for two tasks and lost the moment the timing shifted. `workers: 1`. Suite **534 + 1 skipped**, `ruff`, `ci/fitness.py` (6 of 7 wired, FF-006 at 7 of 7, FF-004 refusing a real `UPDATE`), `ci/evals.py`, `tsc`, `lint`, `build` and all **36** Playwright specs pass. Two change entries raised and left **proposed**: **CHG-036** and **CHG-037**. | **Fixed — awaiting re-review** | Twenty-two proposed entries now need a human decision, and two of them contradict each other — CHG-035 says a dismissed report *“cannot move afterwards”* and CHG-034 says the narrowness that lets its `location` and `repair_job_id` move is deliberate; a re-review should start with the partial index against a concurrent second writer, and with `store/scenarios.py`, which still holds the six-ASCII alphabet CHG-037 replaced one module over |

| 2026-08-16 | **TASK-010 output** — `ci/fitness.py` (FF-003 in two halves, the `OpenProbe` recorder, the route walk, the two vacuity guards), `fitness-functions.md`'s FF-003 row and its two paragraphs, `cicd-pipeline.md` stage 4, `TASK-010.md` | TASK-010 / FF-003, REQ-NF-003, AC-002, AC-010, CHG-013, CHG-038 | The developer (**also the author** — same Q-026 conflict, eleventh time) | Requirement fit · Architecture fit · Test evidence · Change scope | **The task was set as a question — can clause (c) be wired as a check that could really fail — and the answer is yes, in both processes.** A `fs.readFileSync` in `app/page.tsx`, which is a server component and a real Next.js render path, leaves `tsc`, `lint`, `build` and all **36** browser specs green; `views.integrity()` reading `manifest.json` on the render path of `GET /scenarios/{id}` leaves all **534** tests green. Both are red at the gate. **Clause (a) is failable too, and not in the sense CHG-013 examined**: its original reading — a screen breaks for want of a file — still cannot happen, but `if not integrity["intact"]: rows = []` in the ranking read empties the risk list on a lost file with the whole suite green, which is the empty screen CLAUDE.md forbids reading as safety, and clause (b) is what makes the removal observable enough to catch it. **Eight mutations, each applied, run, and reverted**, with `git status --short` checked after each; three of them are mutations of the check's own guards, because a canary that cannot be seen to fail is the same decoration as the gate it protects. **No application file was changed by this task.** One specification gap raised and left **proposed**: **CHG-038** — the register does not decide what *open every screen* means across a process line, how clause (a) is measured, or whether a `stat` is a read; left undecided, (b) and (c) contradict each other, because the notice (b) requires cannot be produced without looking at the filesystem (c) is read as forbidding. | **Accept** | CHG-038 and the twenty-two entries before it need a human decision; a later reviewer should start where this round is weakest — the frontend half of (c) is a text scan, and the picture comparison strips `integrity`, whose shape is asserted separately and only at baseline |

**Decision values:** Accept · Accept with follow-up · Revise · Reject · Block

### TASK-010 — the last fitness function, and the reason it took a decision rather than a script

**Author and reviewer are the same process, for the eleventh time, and this row is an acceptance
rather than a Block, which makes saying so more important rather than less.** Q-026 is unchanged:
no real people exist for this prototype, one person holds every decision-owner role, and there is
**no human between this work and its judgement**. What is offered instead of independence is
evidence a later reader can re-run — every mutation is named in `TASK-010.md` with what it turned
red and, more usefully, what it left **green**.

**The brief for this task was not *wire FF-003*. It was *decide honestly whether FF-003 can be
wired*, and leave it unwired with the reason if it cannot.** That is the right shape, and it is
worth writing down why the answer came out the other way. CHG-013's argument was about a *file
being read*: nothing on a render path opens one, so removing a file cannot break a screen. True,
and still true. But a fitness function is not a prediction about which mistakes will be made — it
is a fence around a decision, and the decision here (`technical-spec.md` §6, *every read is served
from stored results*) can be broken in two directions. **A render path can start reading a file**,
which clause (c) now catches in both processes. **And a screen can be made to depend on a file
being there**, which is clause (a) once clause (b) gives the removal an effect. The second is the
one this repository should expect: it is one line, it looks careful, and it fails safe-looking —
an empty list rather than an error.

**Three things had to be decided before the check could exist, and one of them was a real
contradiction.** They are in CHG-038. The contradiction is worth repeating here because a reviewer
will meet it before they meet the entry: `views.integrity()` calls `is_file()` on all five source
files on the render path of `GET /scenarios/{id}`, so a literal reading of *no view reads a source
file at render time* makes clause (c) forbid what clause (b) requires. The decision — **(c)
forbids a file's contents reaching a response; asking whether it exists is what (b) is** — is a
decision, not a discovery, and it is proposed rather than accepted.

**What this round did not do, stated so the next reader does not have to find it.** The frontend
half of (c) is a **text scan** of `frontend/app`, `frontend/views` and `frontend/lib` for ten
spellings of a filesystem reach; it is FF-002(b)'s shape and it has FF-002(b)'s weakness — a
render path determined to read a file can spell it in a way the list does not hold. The runtime
half has no such gap and covers the backend only, because the Next.js server is not the process
this gate starts. The picture comparison strips two keys: `data_age_hours`, which moves with the
clock, and `integrity`, which is what the check is changing — so a field **added** to the
integrity block is invisible to every clause except the shape assertion, which runs once, at
baseline. And `ci/evals.py`, the other quality stage, is untouched by this task and unaffected
by it.

**Six reviews across four tasks have now each found something the previous one did not.** This
row does not add to that count: it is a build, self-accepted, and the only reason it is `Accept`
rather than `In review` is that the task's whole output is a gate whose every clause was watched
to fail before its register row moved. **A gate that cannot fail governs nothing** — the sentence
CHG-010 and CHG-013 both record — and the way to earn the opposite claim is to break it on
purpose, eight times, and write down what stayed green.

### The remediation of both TASK-008 Blocks — seven findings, one migration, and a race nobody had looked for

**Two Blocks were open at once and this section answers both.** The re-review of 2026-08-16 was
run on a byte-identical tree, so its four checks stand beside the first round's three rather than
replacing them; two of the seven are the same finding re-run and are fixed once. **Every mutation
below was applied, the named stage of the gate run, and reverted, and `git status --short` showed
no unexpected file after each one.** The full table, with counts, is in `TASK-008.md`.

**The Block is in the store now, and the shape of the fix was decided by a test that had to be
corrected first.** `decision_records_one_dismissal_per_report` is a partial `unique` index on
`decision_records (subject_id) where kind = 'dismiss'` — the remedy the first review named,
chosen because it creates no table and drops no trigger, which is what keeps ADR-004 out of it.
The re-review's new evidence was that `test_the_store_accepts_a_dismissal_record_that_agrees_with
_its_report` did not merely miss *one human decision, one audit row*: it **asserted its absence**,
dismissing its report through the endpoint and then inserting a second `dismiss` row directly with
`assert len(rows) == 2`. **The test was not weakened and it was not deleted.** Its report is now
dismissed by a direct statement, which writes no audit row at all, so the permitted control is the
*only* row and the assertion is `== 1`. What the control proves is unchanged — it is still the
accepted shape without which the six refusals below it would be satisfied by a trigger that
refuses every `dismiss` row — and the store no longer has a property in the suite that
contradicts the requirement. The correction is written into CHG-036 rather than left to be
noticed, because a reviewer who finds an assertion inverted in a remediation is entitled to see it
argued rather than discovered.

**The whitespace hole is the third instance of one sentence and the first that needed no mutation
at all.** CHG-023 wrote it about a location, CHG-033 about a reason, and both times the fix
enumerated six ASCII characters — which is right about the alphabet it names and silent about
every other. What made this one different is *where* the strictest definition lived: in the
browser, whose `String.prototype.trim()` is Unicode-aware, so the button stayed disabled and
nobody could see that the API answered `201` to a reason of one no-break space. **An enforcement
that is strictest in the layer ADR-002 forbids is worse than one that is missing**, because the
screen is what everybody looks at. The alphabet is now one list, and the tie that fails when the
copies disagree is the same shape `AGENT.md` already carries for a bound.

**And the same alphabet closes a hole in a different column that nothing could reach.**
`damage_reports_location_is_a_neighbourhood` accepted a whitespace-only neighbourhood written as
raw UTF-8; the only thing refusing it was `json.dumps`' `ensure_ascii` default in a module one
directory away, which escaped the character and tripped an unrelated clause. `ensure_ascii=False`
is an ordinary tidy-up and the obvious one the day a neighbourhood needs an accent — so the
constraint is fixed **first** and the serialiser is deliberately left alone, which is CHG-024's
rule about not smuggling a change inside a remediation for something else.

**One defect was found while fixing and appears in neither review, and it is the most
uncomfortable of the eight.** `playwright.config.ts` carries the comment *"one backend, one
database, one storm at a time"* beside `fullyParallel: false` — and that setting does not deliver
the sentence. It keeps the tests inside one file serial; **separate files still run in parallel
workers**, and on this machine that was seven files in seven workers against one SQLite file.
Three of them load the same storm and TASK-008's first case files a damage report, so ATEST-007's
*the empty board reads "no damage reported"* — whose own docstring rests on *"nothing else in the
suite files a damage report"* — has been racing a file that does ever since TASK-008 was written.
It won three runs out of three on the untouched tree and lost two out of two here, on a change
that touches neither file's logic. **A green that depends on winning a race is not evidence**, and
the fix is `workers: 1`: 58 seconds instead of 30, and the same answer every time.

**What this round did not do.** `store/scenarios.py` still holds its own six-ASCII whitespace copy
for `name` and `source_note` (CHG-031) with the identical hole; it belongs to TASK-009, which is
in review, and widening an entry under review is the drift the change register exists to catch. It
is named here so the next reviewer does not have to find it twice.

### The re-review of TASK-008 — four checks, four of them failed

**This is a re-review of a Block, and the first thing it established is that there was nothing to
re-review.** `git diff 9b80d5d..HEAD --stat` between the commit that built TASK-008 and the commit
before this one lists exactly one file — `spec/05-review/01-logs/review-log.md`, +86 lines. No
remediation has been attempted, so the three findings of 2026-08-16 stand as written and the
Block's own mutation was re-run rather than taken on trust: it reproduces exactly.

**The four checks were chosen before this run read any of the code**, from the failure shapes
`AGENT.md`'s lessons table records, and deliberately **not** the twelve done criteria in the task
file, **not** the twenty mutations its author ran, and — for three of the four — **not** the four
the previous review used. Repeating a check against an unchanged tree confirms a known answer; the
point of a re-review is to be at least as sceptical, which means looking somewhere else as well.
**Every mutation below was applied, the named stage of the gate run, and reverted, and
`git status --short` was empty after each one.** The probe file the checks were written in
(`test_ZZPROBE_rereview.py`) was deleted before this entry was committed; it is not part of the
suite and none of its assertions is a test anybody now owns.

**The gate was run first and it is green.** `pytest -q` twice on the untouched tree — 499 passed,
1 skipped, both times. `ruff` clean over `backend`, `spec/03-tests/05-executable` and `ci`.
`ci/fitness.py` 6 of 7 wired, FF-006 at 7 of 7 and FF-004 refusing a real `UPDATE`. `ci/evals.py`
holds the floor, 5 scorers × 2 cases. `tsc`, `lint`, `build` and all **36** Playwright specs pass.

| Check | Result |
|---|---|
| **A rule enforced in service code that the store could have refused** | **Failed. The Block stands, and the suite is worse than silent about it — it certifies the opposite.** Done criterion 7 is *"**exactly one** `decision_records` row of kind `dismiss` is appended"*. Mutation, re-run from the previous round: `if False and report["status"] == …` in `api/dismissals.py` and `where id = ? and ? is not null` in `dismiss_report`, the two service-layer guards gone and nothing else touched. **2** tests red — `test_a_second_dismissal_is_a_409_that_names_the_first` and the restart case — and both fail on a **`500 internal_error`**, because both retry with *different* words and `damage_reports_dismissal_is_final` refuses that. An **identical** retry, which no test in the repository issues, is answered **`201` twice** and leaves **2** `dismiss` rows for one human decision. **What is new is why no test will ever catch it.** `test_the_store_accepts_a_dismissal_record_that_agrees_with_its_report` inserts a second `dismiss` row for an already-dismissed report **directly against the database** and asserts `len(dismiss_record(connection)) == 2`. It is there as the permitted control for the six refusals below it, and it is correct about the store — but it means the store's acceptance of two audit rows for one decision is now a **property the suite requires**. The partial `unique` index the previous review named — `create unique index … on decision_records (subject_id) where kind = 'dismiss'`, which creates no table and drops no trigger — would turn that test red, and whoever fixes this needs to know that before they start. |
| **A check that reports a condition but was never fed data without it** | **Failed, on a different clause from the previous round's.** `decision_records_dismiss_shape`'s `exists` ends `and coalesce(r.repair_job_id, '') = coalesce(json_extract(new.payload, '$.repair_job_id'), '')`, and the migration says exactly why the `coalesce` is there: *"a report may legitimately belong to none (CHG-022) and `null = null` is null, which a `where` clause reads as false — the row that most needs to be recordable would be the one refused."* Mutation: delete both `coalesce`s, leaving `r.repair_job_id = json_extract(new.payload, '$.repair_job_id')`. **499 passed, 1 skipped.** Under it, dismissing a report with no repair job is a `500 internal_error`, the alarm stays on the board, and nothing anywhere is red — while `DispatchBoard`'s `Unattached` section renders a `DismissAlarmControl` on **every** unattached report, so the screen offers an action whose only possible answer is a refusal, which is the TASK-006 defect one screen over. UTEST-011 feeds this clause only its violating direction: the `("repair_job_id", None)` case sets the payload to null against a report that *has* a job. **No test in the repository dismisses a report with no repair job at all**, and CHG-022 was raised precisely because that state exists and reaches a screen. |
| **A described state whose only reader has never been asked for it** | **Failed.** CHG-035's diagnosis of `decision_records.kind = 'dismiss'` was *no writer, no reader and no decided shape*. TASK-008 built the writer and the shape. The reader is `GET /api/v1/scenarios/{id}/decisions`, admin-only, which `technical-spec.md` calls *the artefact produced to a regulator afterwards* — and nothing asks it for a dismissal. Mutation: `and kind <> 'dismiss'` in `decisions.read_all`. **499 passed, 1 skipped**, with every cleared false alarm silently absent from the append-only record as anybody outside the database would read it. Eleven tests call that endpoint; every one of them calls it for a `recommendation`, an `accept`/`change`/`reject` or a `placement`. AC-008 is about **any** human decision, and the one kind this task exists to create is the one the reader has never been tested for. `AGENT.md`'s row applies literally — *prove the haystack is a haystack before reporting no needle* — with the halves reversed: the writer was proven and the haystack was not. |
| **One rule, several homes, and nothing that fails when the copies disagree** | **Failed twice, and the second needed no mutation.** **(a)** `DISMISSAL_REASON_MAX` is tied between the schema and `dispatch.DISMISSAL_REASON_MAX` by `test_one_bound_governs_a_dismissal_reason`, and has a **third** copy in `frontend/lib/api.ts` and a **fourth** as the literal `'N'.repeat(2001)` in `e2e/TASK-008.spec.ts`. Set the third to `8`: `tsc`, `lint`, `build` and all **36** browser specs pass while the field stops a dispatcher at eight characters. The browser case that exercises the bound calls `input.removeAttribute('maxlength')` before typing, so it cannot see the change by construction. Raised as an observation last round; unremediated, and re-run here. **(b) What counts as whitespace is written three times and the three disagree, and this one is a live hole rather than an untested clause.** The schema enumerates six ASCII characters (`' ' || char(9) || char(10) || char(11) || char(12) || char(13)`), `dispatch.WHITESPACE` repeats the same six, and the browser uses JavaScript `String.prototype.trim()`, which is Unicode-aware. **No mutation:** on the untouched tree, `POST /api/v1/damage-reports/{id}/dismiss` with a reason of `" "` (no-break space), `" "` (em space), `"​"` (zero-width space) or `"﻿"` is answered **`201`**, and the character is what `dismissed_reason` and the audit row then hold. `'   '` is refused and `' '` is stored — *the same non-answer wearing a different whitespace character*, which is CHG-023's sentence verbatim, for the **third** time, on the very column CHG-033 was written to close. The strictest of the three definitions is the one in the browser, which is the layer ADR-002 says must never be the enforcement, and it is why the hole is invisible on screen: the button stays disabled, so only a caller reaching the API meets it. |

**Two of the previous round's three findings were not re-run, and saying why is the point of this
sentence.** The tree is byte-identical to the one they were found on, so re-running them would
confirm an answer nobody has had a chance to change. `and r.scenario_id = new.scenario_id` is still
violated by no case in UTEST-011 — every `insert_dismiss_record` call passes the report's own storm
— and `api/dismissals.py` still emits `open_reports_in_area` into a log line that
`test_dismissing_sends_nobody_anywhere` reads for its event name and its `outcome` and not for its
number. Both stand exactly as written on 2026-08-16.

**What held, and it is still most of the task.** Everything the previous round listed under *what
held* was re-read and nothing contradicts it: CHG-033's named check with all six ASCII refusals
issued directly against the database, each paired with an acceptance differing in one field; the
two-argument `trim`, which is right about the alphabet it enumerates; the one-character reason
accepted; both silent cases; the bound read back out of `sqlite_master` behind a haystack
assertion; six of the seven clauses of the dismiss trigger, each read by its own sentence; the
atomicity case failed at `append_dismissal` itself; the `404` checked by its sentence; both roles
allowed and STEST-001 carrying the row; BR-001 in the log line and in the job that stays on the
board; migration 014's round trip with both append-only triggers proven still **refusing** by a
real `UPDATE` and a real `DELETE`; and the restart case, which this round re-read rather than
re-mutated and which remains the strongest test in the task — it asserts the actor, the reason and
the audit row after the restart, not the arrangement the screen is ordered by.

**Two observations, neither a finding.** The **CHG-034 / CHG-035 contradiction** the previous round
recorded is unchanged and still needs to reach whoever decides those two entries: CHG-035 says of
the report and its audit row that *"neither can move afterwards"*, and a direct `update` still
moves a dismissed report's `location` and `repair_job_id` while the record keeps the old ones. And
**the whitespace hole is not confined to the reason column.** `damage_reports_location_is_a_neighbourhood`,
which migration 014 re-declares verbatim, accepts `{"neighbourhood": " "}` on every clause
when the JSON is written as raw UTF-8. It is unreachable today for a reason that has nothing to do
with the rule: `store/dispatch.py` calls `json.dumps` with `ensure_ascii` at its default, so the
escaped ` ` trips the *unrelated* `json(location) = json_object(...)` clause instead. Adding
`ensure_ascii=False` — an ordinary tidy-up, and the obvious one the day a neighbourhood needs an
accent — makes a whitespace-only damage location storable with every test green. CON-003's guard
against *a location that is not a place* is being held up by a serialiser default.

### Author and reviewer are the same process, for the tenth time — and this row is the one most at risk of being read as a second opinion

**Q-026, stated in the row rather than left to the signature, and stated again here because this
is a re-review and a re-review is exactly where a reader starts believing the process is
adversarial.** It is not. This run did not write TASK-008 and did not review it the first time; it
chose its four checks from `AGENT.md`'s lessons table before reading the code, and three of the
four are aimed away from the previous round. That is worth something, and the evidence is above:
two failures nobody had found, in work its author mutation-checked twenty times and a reviewer
mutation-checked four more. It is **not** independence. It is the same model, under the same
account, following instructions from the same person, with **no human between the work and its
judgement**. **No real people exist for this prototype**; one person holds every decision-owner
role, and Q-026 records that as a deferral rather than resolving it with invented names. A third
invocation of one process is not a third pair of eyes, the *Reviewer* column above must not be read
as one, and the twenty change entries this log keeps calling *proposed* are proposed for the same
reason: there is nobody here who is entitled to accept them.

**And the count is worth writing down.** Five reviews across three tasks have now each found
something the previous one did not, every one of them by a directed mutation and none of them by
the gate. 499 tests, six fitness functions, ten evals and thirty-six browser cases were green
through all of it — through a retried request that files two audit rows for one human decision,
through a control the board draws on a report it cannot clear, through an audit record that could
drop the decisions this task exists to record, and through a dismissal reason made of nothing but
a no-break space, stored under a dispatcher's name.

### The review of TASK-008 — four checks, three of them failed

**Chosen before the code was read**, from the failure shapes `AGENT.md`'s lessons table already
records, and deliberately **not** the twelve done criteria in the task file and **not** the twenty
mutations its author had already run. Each was settled by a mutation: break the behaviour, run the
part of the gate that claims to cover it, revert. **Every mutation in this section was applied,
run, and reverted, and `git status --short` was empty after each one.**

**The gate was run first and it is green.** `pytest -q` — 499 passed, 1 skipped. `ruff` clean over
`backend`, `spec/03-tests/05-executable` and `ci`. `ci/fitness.py` passes 6 of 7 wired, FF-006 at
7 of 7 and FF-004 refusing a real `UPDATE`. `ci/evals.py` holds the floor, 5 scorers × 2 cases.
`tsc`, `lint`, `build` and all **36** Playwright specs pass, four of them TASK-008's own. A green
gate is the start of a review and the four checks below are about the difference.

| Check | Result |
|---|---|
| **A rule enforced in service code that the store could have refused** | **Failed, and this is the Block.** Done criterion 7 is *"**exactly one** `decision_records` row of kind `dismiss` is appended"*, and `api/dismissals.py` says why in its own comment: the `409` is *"decided **before** the write so a retrying client cannot produce two audit rows for one human decision."* The store holds half of it. `damage_reports_dismissal_is_final` fires `when old.status = 'dismissed'` and aborts only when `status`, `dismissed_by` or `dismissed_reason` **change** — so a *different* second dismissal is refused and an **identical** one is not: the `where` clause selects no row, the update succeeds, and `append_dismissal` writes a second audit row that `decision_records_dismiss_shape` then happily accepts, because it agrees with the report in every particular. Mutation: `if False and report["status"] == …` in the endpoint and `where id = ? and ? is not null` in `dismiss_report` — the two service-layer guards gone, nothing else touched. The identical retry answers **`201` twice** and the table holds **2** `dismiss` rows for one human decision. The suite notices only that the *conflict* path broke: **2** tests red, `test_a_second_dismissal_is_a_409_that_names_the_first` and the restart case, and **both retry with different words** (`"Mine now"`), which is the half the store does refuse. No test anywhere issues the same reason twice. This is the log's standing **Block** condition in its plainest form — *it works, it passes, and the first refactor silently removes it* — and the store can express it without the rebuild ADR-004 forbids: a partial `unique` index on `decision_records (subject_id) where kind = 'dismiss'` creates no table and drops no trigger (SQLite 3.49.1 here; partial indexes since 3.8.0). |
| **A check that was never fed data without the condition it reports** | **Failed, on a clause rather than on a check.** `decision_records_dismiss_shape`'s second statement is a seven-way `exists`, and six of its clauses have a case that violates that clause and no other — the subject, the fact of the dismissal, the actor, the reason, the neighbourhood and the repair job. The seventh, **`and r.scenario_id = new.scenario_id`**, is violated by nothing. Mutation: delete it. **499 passed, 1 skipped.** Under that mutation a `dismiss` row naming a report in storm A is **accepted** with `scenario_id` set to storm B, and `GET /api/v1/scenarios/{B}/decisions` then serves a dismissal that happened in another storm — *"two storms blended into one ranking would look entirely plausible"*, which CLAUDE.md calls a correctness bug and which this clause is the only thing preventing. The clause is right; nothing has ever read it back. `AGENT.md`'s row says why that matters beyond coverage: *the clause you never ran is the clause whose function you assumed* — and this repository has already had one such clause turn out to be not merely unproven but **wrong** (CHG-023's `trim()`). |
| **A figure that claims a resolution, at a call site nobody carried the lesson to** | **Failed.** REQ-NF-007 wants *an aggregate for that neighbourhood*, and `open_reports_in_area` now has **two** callers: `api/dispatch.py`, where UTEST-012's three-way fixture names all three answers (`3` for the area, `4` for the storm, `1` for the asset, with the wrong two asserted **absent**), and `api/dismissals.py`, added by this task, where nothing asserts the figure at all. Mutation: replace the dismissal's call with `select count(*) … where scenario_id = ? and status = 'open'` — the whole storm, the coarser wrong answer. **499 passed, 1 skipped.** `test_dismissing_sends_nobody_anywhere` reads that same log line and checks the event name, `outcome=recorded_not_dispatched` and the absence of the dispatcher's words; it says nothing about the number beside them. Mutating the shared function is red, because UTEST-012 covers it — mutating **this call site** is invisible, which is the distinction. Same shape as the `404`-that-names-which-refusal lesson: a discipline that is real in one module and stops at its boundary unless somebody carries it across. |
| **A property asserted only within one process lifetime, when the decision says the state is durable** | **Held, and it is the strongest test in the task.** Done criterion 10 is *"the dismissal and its record survive a restart, and a second dismissal is still refused after one"*, and `test_the_dismissal_and_its_record_survive_a_restart` builds a second application over the same file with `conftest.build_application`, then asserts **the state the restart was supposed to protect** — the status, the actor and the reason on the report, the audit row and its payload — and not merely that the board renders one fewer item. Mutation: delete `connection.commit()` from `dismiss_report`, the one-line way to make durable state live inside one process (the same connection keeps reading its own open transaction; a second one sees nothing). **5** tests red, the restart case among them, failing exactly where it should — `At index 0 diff: 'open' != 'dismissed'`, after the restart. This is the second lessons row finally being applied at build time rather than at review time, which is what `AGENT.md` asks for: *when a task introduces durable state, the restart test is part of the task, not part of its review.* |

**What held, and it is most of the task.** Both halves of REQ-F-008 through the endpoint; CHG-033's
named check, with all six refused reasons — `''`, `'   '`, `char(9)||char(10)`, `' \r\v\f '`,
`'  padded  '` and the over-length one — issued **directly against the database** and each paired
with an acceptance differing in exactly one field; the two-argument `trim`, which is the clause
CHG-023 proved the one-argument form gets wrong; the one-character reason accepted, because
brevity is not the rule; the silent case for the check (an open or `duplicate` report needs
neither column) and the silent case for CHG-034's trigger (a dismissed report's `reported_by` may
still move, and an open report may still become `duplicate`); the bound read back out of
`sqlite_master` with a haystack assertion in front of it; six of the seven clauses of the dismiss
trigger, each refused by its own sentence rather than by an exception class; the atomicity case,
failed at `append_dismissal` itself so the only window a half-done dismissal could exist in is the
one under test; the `404` checked by its sentence; both roles allowed and STEST-001 carrying the
row for the deny path; BR-001 in the log line and in the job that stays on the board reading
*explained*; migration 014's round trip, with both append-only triggers proven still **refusing**
by a real `UPDATE` and a real `DELETE` at every point of it, and the roll-forward aborting rather
than inventing a reason for a dismissal the older shape had allowed to be blank; and four browser
cases, including the one that presses a control the task drew itself and the one that proves
clearing one call is not clearing the job.

**Two observations, neither a finding.** **CHG-035 makes a claim the build does not hold.** It says
of the report and its audit row that *"they must be equal when the row is written, and neither can
move afterwards — the report because of CHG-034, the record because of BR-004."* The record cannot
move; the report can. Issued directly against the database after a dismissal,
`update damage_reports set location = json_object('neighbourhood','Saltmarsh')` and
`update damage_reports set repair_job_id = null` are both **accepted**, and the audit row goes on
saying `Northgate` and naming a job the report no longer belongs to — two of the three facts the
payload copies. CHG-034 says the trigger's narrowness is deliberate and lists the three columns it
freezes, so the two proposed entries disagree with each other about the same guarantee, and the
human deciding them should see that rather than read the stronger sentence. It is not this log's
Block condition: no code updates either column, and any code that did would turn the board's own
location assertions red as collateral. And **`DISMISSAL_REASON_MAX` has three copies, not two.**
The schema and `store/dispatch.py` are tied by `test_one_bound_governs_a_dismissal_reason`;
`frontend/lib/api.ts` holds a third, described in its own comment as *"mirrored from
`dispatch.DISMISSAL_REASON_MAX`"*, with nothing that fails when the mirror stops matching. Set to
`8`, `tsc`, `lint`, `build` and all **36** browser specs pass while the field silently truncates
every reason a dispatcher types to eight characters — a shorter reason than they meant, stored
under their name. `AGENT.md`'s row names the shape: *a bound written in more than one place needs
something that fails when the copies disagree*, and this repository has now paid for it twice
(CHG-023, CHG-033) on the two copies that were tied.

### Author and reviewer are the same process, for the ninth time — and this row must not be read as an independent one

**Q-026, stated in the row rather than left to the signature.** This run did not write TASK-008,
had not seen its code, and chose its four checks from `AGENT.md`'s lessons table before reading
any of it. That is worth something, and the evidence is above: three of the four failed in work
whose author had already run twenty mutations of their own and recorded every one. It is **not**
independence. It is the same model, under the same account, following instructions from the same
person, with **no human between the work and its judgement**. No real people exist for this
prototype; one person holds every decision-owner role, and Q-026 records that as a deferral rather
than resolving it with invented names. A later invocation of one process is not a second pair of
eyes, and the *Reviewer* column above must not be read as one.

**Two things are worth noticing about this particular round.** The first is that the check which
**held** is the one the last three reviews each found broken — the restart case. `AGENT.md`'s
instruction to build the restart test *into* the task rather than leave it to review was followed,
and it works: the one-line mutation that would have passed every earlier task's suite fails five
tests here. The second is that all three failures are the same lesson at a boundary. *One human
decision, one audit row* is real in `api/dismissals.py` and absent from the store; the seven-way
clause discipline is real for six clauses and absent for the seventh; the three-way area figure is
real in `api/dispatch.py` and absent one module over. Nothing here is careless. A rule that has to
be re-derived at each boundary is a rule that will be missed at one, which is the sentence this
log already wrote about the restart test and is now writing about three more things.

### The remediation of the TASK-006 Block — what was fixed, and the two places the review's own remedy was not taken

**Each fix names the mutation that turns it red, because that is the part a later reader can
check.** Every mutation below was applied, the relevant stage of the gate run, and reverted;
`git status --short` showed no unexpected file after each one.

| Finding | Mutation that is now red |
|---|---|
| CHG-025's *numbered from 0 in chronological order* | `enumerate(observed)` instead of `enumerate(sorted(observed, key=_chronological))` fails **17** tests, seven of them ATEST-005's, where it used to leave all 323 green. `sorted(observed)` — the plain text sort, which is the subtler wrong answer — fails the case built on two forecasts in different UTC offsets |
| Criterion 11, the forecast **values** across a restart | `save_series` writing the cells to a `create temp table` that shadows the real one — the review's own mutation — fails **both** restart cases and leaves the other 24 green |
| Criterion 12, `ForecastRevisionControl` | Deleting the whole `<ul className="revisions__list">` block fails **3** browser cases; removing `disabled={!entry.ranked}` fails 2; reporting every forecast as `ranked` from the store fails 2 in the browser and 2 in `pytest` |
| CHG-028(a), delete-and-reinsert | The `before delete` guard absent fails 1; **present and wrong** (pointed at `damage_reports`) fails the same 1; **unconditional**, with the `when` clause removed, fails the whole-scenario cascade case instead — which is the trade-off migration 010 declined the guard over, now held down by a test |
| CHG-028(b), a ranking of a forecast that does not exist | The `before insert` guard absent fails 1, and the refusal is read out of the message so it cannot pass for the unique constraint's reason |
| CHG-028(c), the asset key | `references assets (id)` instead of `(asset_id, scenario_id) → assets (id, scenario_id)` fails 1 — CHG-019's shape, on the table that entry named as knowingly unfixed |
| PTEST-001 measuring the endpoint | One lookup per asset inside `score_revision`: 122 statements around the write at 110 assets against 232 at 220, red on shape rather than on wall-clock, because five seconds is generous by design |

**The foreign key the review named was written, run, and withdrawn — and saying so plainly is the
point of this paragraph.** `foreign key (scenario_id, forecast_revision) references
scenario_forecast_revisions (…)` is the constraint the observation asked for, and it is the one a
reader would expect after CHG-019. With `on delete cascade` it hands `scenario_forecast_revisions`
the power to delete rankings — and migration 010's *down* drops that table, so **rolling 010 back
destroys every stored ranking in the database**. With `on delete restrict` it turns §7.2's scenario
delete into an integrity error, because a scenario reaches `risk_scores` by two paths whose order
SQLite does not define; that is CHG-024's argument unchanged. And it cannot be satisfied by data
that already exists after a 010 rollback, because the rankings survive and the forecast times do
not — the rebuild would abort the upgrade or invent a forecast time out of a computation time. So
the rule is a `before insert` trigger, which says the true and narrower thing: **what may be
written.** The limit is recorded rather than implied away — no orphan can be *created*, which is
not the same as none can *exist* — and it is in CHG-028 with the alternatives.

**The second place is `scenarios.forecast_revision`.** The review showed the pointer can be moved
directly to a revision nothing ranked, after which the default `GET /risks` is a 404 while every
screen reads *current*. A foreign key from `scenarios (id, forecast_revision)` into
`scenario_forecast_revisions` would be circular — that table's own key points back at `scenarios`
— and a deferred circular pair is a worse cure than the disease. What is done instead is CHG-027:
`ranked` is read out of `risk_scores`, so the screen no longer believes the pointer. A new test
reaches that state by a direct statement and requires the response to disagree with it.

**One thing was found while fixing rather than by the review, and it is the more interesting of
the two.** Migration 011's insert guard made `UTEST-009`'s *the store refuses a score with no
reasons* start passing for the **wrong reason**: without a forecast-revision row in its
hand-built scenario, the insert was refused by the new guard rather than by BR-002, and the test
would then have passed with BR-002's check constraint deleted. That is the sixth *assertion that
could not fail for the reason it claimed* in this repository, and the first found by adding a
constraint rather than by a mutation. Its setup now creates the revision row and it reads
`CHECK constraint failed` out of the refusal.

**And one that is worth more than either.** The reordered fixture is a three-line change to a CSV
and it turned a green suite red in seventeen places. Nothing about the code moved. The lesson row
`AGENT.md` already carries — *a figure that claims a resolution needs a fixture in which the
answers differ* — was written about a count and is really about **every** input a test is built
on: the fixture is an assertion, and a fixture in which the right and wrong implementations agree
asserts nothing at all.

### The review of TASK-006 — four checks, three of them failed

**Chosen before the code was read**, from the failure shapes `AGENT.md`'s lessons table already
records, and deliberately **not** the thirteen done criteria in the task file and **not** the
twenty-five mutations its author had already run. Each was settled by a mutation: break the
behaviour, run the part of the gate that claims to cover it, revert. **Every mutation in this
section was applied, run, and reverted, and `git status --short` was empty after each one.**

**The gate was run first and it is green.** `pytest -q` **four** times on the untouched tree —
323 passed, 1 skipped, every time — so CHG-018's ordering fix still holds across the 29 cases
this task adds. `ruff`, `ci/fitness.py` (6 of 7 wired, FF-006 at 7 of 7), `ci/evals.py`
(5 scorers × 2 cases), `tsc`, `lint`, `build` and all **14** Playwright specs pass. TASK-006
added 29 backend cases and **no** browser case, which is the subject of the fourth check.

| Check | Result |
|---|---|
| **A rule enforced in service code that the store could have refused** | **Held for the criterion that names it, with two invariants left outside the schema.** Done criterion 4 is real. Mutation: point `risk_scores_no_update` at a different table — *present and wrong*, not absent, because renaming a trigger does not disable it — and **2** tests turn red, and the refusal is checked by reading `never rewritten` out of the message, so it cannot pass for BR-002's reason the way it once did. Criterion 5's `unique (scenario_id, asset_id, forecast_revision)`, `scenario_forecast_cells`' composite foreign key and `unique (scenario_id, valid_time)` all refuse a **direct** insert with the permitted case beside them. **Two things the store does not hold, both issued directly against the database and both accepted.** `delete from risk_scores where forecast_revision = 0` followed by one re-insert rewrote revision 0 into a one-row list that `GET /risks?forecast_revision=0` then served with a **200** — the task's own Constraints say *"not by `UPDATE`, not by delete-and-reinsert"*, and only the first half is in the schema; the migration declines the `before delete` twin **in writing** because `risk_scores` is cascade-deleted with its scenario and its assets, which is a genuine trade-off honestly recorded rather than a slip. And `risk_scores` carries **no foreign key at all** on `(scenario_id, forecast_revision)`: a ranking at revision 42 of a storm that carries three forecasts is accepted and served with a 200, and the pointer can be moved to 42 directly, after which the default `/risks` read is a 404. `scenario_forecast_cells` was given exactly that composite key — *"CHG-019's lesson applied before it is needed rather than after"* — and the table AC-005 is actually about was not. Neither is reachable from caller input, which is what keeps this an observation rather than this log's pre-declared **Block**. |
| **A check that was never fed data without the condition it reports** | **Failed.** CHG-025 decides that revisions are *"numbered from 0 in chronological order"*, and `loader/load.py::_chronological` is a careful function whose docstring explains why sorting ISO-8601 as text is not enough — *"'usually' is how the rest of this repository ended up with an order that was not one"*. The fixture's `weather.csv` lists its three forecast times **already in chronological order**, so the right answer and the wrong one are the same list. Mutation: `enumerate(observed)` instead of `enumerate(sorted(observed, key=_chronological))` — dictionary insertion order, which is file order, and the obvious wrong implementation. **323 passed, 1 skipped.** Handed the same file with its three time blocks reversed, that mutation numbers revision 0 as the **06:00** forecast and revision 2 as the **00:00** one, so *"apply the scenario's next forecast change"* walks the storm backwards through time — and nothing anywhere is red. The code is right; the suite cannot tell. Same shape as REQ-NF-007's three-way figure one review ago: one fixture in which correct and incorrect agree. |
| **A property asserted only within one process lifetime, when the decision says the state is durable** | **Failed, on the half of the criterion that carries the data.** Done criterion 11 is *"the revision pointer **and the forecast series** survive a restart"*, and `test_the_revision_and_its_forecasts_survive_a_restart` does cross a restart with `conftest.build_application` — which is further than the two tasks before it managed unaided. What it asserts *after* the restart is the two earlier **orders**, served from stored `risk_scores.rank` that no restart could lose, and that the next apply answers `201` with `forecast_revision == 2`. It says nothing about the forecast **values**. Mutation: `save_series` writes the revisions to the database and the **cells** to a temp table, which shadows the real one for every unqualified read — the exact shape of a per-connection cache, and indistinguishable inside one process. **All 25 cases of ATEST-005 and ITEST-004 pass.** A second application over the same file then re-ranks the whole storm to `ranked: 0, unscored: 5`, every asset carrying *"no forecast covers this asset, so its wind exposure is unknown"* — still a 201, still revision 2, still green. A restart that silently makes every asset unrankable is the screen CLAUDE.md forbids reading as safety, and criterion 11 is the criterion that exists to catch it. (Three further failures under that mutation were collateral from the temp table colliding with the migration test's `drop table`, and are not the property under test.) |
| **A described state with nowhere to live — on a screen proven by nothing executable** | **Failed.** `GET /scenarios/{id}` returns `forecast_revisions: [0, 1, 2]` the moment a storm is loaded, because it lists the **forecasts the file carries**; only revision 0 has a ranking. Nothing in the response, and nothing in the schema, distinguishes *a forecast that exists* from *a revision that has been ranked* — and `ForecastRevisionControl` renders one selectable button per entry. Driven in a real browser: clicking **Revision 2** on a freshly loaded storm calls `GET /risks?forecast_revision=2`, which correctly answers 404, and `ScenarioView`'s single `catch` puts the whole screen into its error state. The ranking is replaced by *"We could not load the ranking… try again"*, which never succeeds; the asset table goes with it; the control still reads **Forecast revision 0 · current** with no indication of what happened; and `RecommendationDecision` stays on screen, still bound to revision 0's `recommendation_id`, offering *accept / change / reject* beside a ranking that is not there. Nothing tests any of it: TASK-006 added **no** Playwright spec, and deleting the entire revision list — AC-005's comparison half, and the whole of done criterion 12 — leaves `tsc`, `lint`, `build` and all **14** browser cases green. This is the observation the second review of TASK-005 made about `DispatchBoard`, recurring one screen later. |

**What held, and it is most of the task.** Both halves of AC-005 through the endpoint, with the
ALPHA/BRAVO swap resting on a fixture where the forecast is the only thing that can move them;
criterion 3's byte-identical revision-0 rows, asserted against the stored rows rather than the
response; the CHG-026 trigger, red under a present-and-wrong mutation; the `unique` refusal and
the composite foreign key, both issued directly against the database with the permitted case
beside them; the 409 that names the current revision and writes nothing; the 404 that is checked
by its body so it cannot be satisfied by an endpoint that does not exist; ITEST-004's
whole-database dump, with `test_the_dump_notices_a_write_when_one_happens` as the positive guard
the fourth lessons row demands; every revision's own `recommendation` row and the re-read that
does not create a second one; the unscorable asset present and unranked at all three revisions;
carry-forward keeping the `valid_time` it was issued at; both roles allowed; no
`decision_records` row for an apply; and the up-and-down round trip over a database that already
held a storm, with both append-only triggers proven still refusing afterwards.

**Two observations, neither a finding.** `PTEST-001` is listed in the task file as re-run because
*"the re-rank limit it measures is this task's operation"* — it is not: it times `load_scenario`
plus `rank_assets` in process and never touches `POST /forecast-revisions`, `score_revision`'s
join, or `save_revision`'s 220-row insert and pointer move, so REQ-NF-001's five-second budget is
measured against a proxy that excludes every database statement the operation now performs. And
migration 010's backfill dates revision 0 from `scenarios.forecast_issued_at` while the loader
dates it from the earliest `valid_time` in `weather.csv`; in this fixture those are the same
string, so the AC13 assertion cannot tell them apart, and a prepared storm whose manifest issue
time differs from its first forecast time would be re-dated by the rollback-and-forward trip.

### Author and reviewer are the same process, for the eighth time — and this row must not be read as an independent one

**Q-026, stated in the row rather than left to the signature.** This run did not write TASK-006,
had not seen its code, and chose its four checks before reading any of it — and that is worth
something: three of the four failed in work whose author had already mutation-checked all 29 of
its cases and found one of them wrong. It is **not** independence. It is the same model, under
the same account, following instructions from the same person, with **no human between the work
and its judgement**. No real people exist for this prototype; one person holds every
decision-owner role, and that was recorded as a deferral rather than resolved with invented
names. A later invocation of one process is not a second pair of eyes.

**The pattern this log has been tracking held again.** Four reviews across two tasks have now
each found something the previous one did not, every one of them by a directed mutation and none
of them by the gate. 323 tests, six fitness functions, ten evals and fourteen browser cases were
all green while a re-ranked storm could come back from a restart with every asset unrankable, a
prepared file could be walked backwards through its own forecasts, and the screen this task
delivers could be broken by pressing a button it draws itself.

### The second remediation — what was fixed, and the one place the review's own remedy was not taken

**Each fix names the mutation that turns it red, because that is the part a later reader can
check.** Every mutation below was applied, the **whole** suite run, and reverted;
`git status --short` showed no unexpected file after each one.

| Finding | Mutation that is now red |
|---|---|
| Done criterion 3 — the grouping rule in the store | Removing the normalisation check from migration 009 fails **8** tests, six of them the direct inserts `Northgate`, `NORTHGATE`, `northgate `, ` northgate`, `north  gate` and `north\tgate` |
| The durable order across a restart | The review's own mutation — `_SEQ[(id(connection), table)] += 1` beside the connection — fails 2 of the 3 new restart cases with `500 internal_error`, exactly as predicted; the same mutation in `store/decisions.py` fails the third |
| CHG-022 — a report with no repair job | Emptying the `None` bucket in `board_body` fails 3; restoring the inner join in `open_reports_in_area` fails 2 |
| The unexercised length clause | Relaxing the schema to `between 1 and 100000` **and** raising `NEIGHBOURHOOD_MAX` to 5000 fails 3; leaving the schema at 120 with the constant at 5000 fails 3, one of them the `400` that had become a `500` |
| STEST-001's missing row | Deleting the `damage-reports` row from `DATA_ROUTES` fails the new coverage test, naming the endpoint |

**The review named `unique (scenario_id, location_key collate nocase)` and it was not used.**
Saying so plainly is the point of this paragraph. The check constraint is the whole fix, and
the collation beside it would be **unreachable**: `nocase` folds ASCII `A–Z` and nothing else,
and every string the check admits is already ASCII-lower-cased, so no two keys the table can
hold collide under `nocase` without colliding under `binary` first. This log records four
gates that could not fail — FF-002, FF-003, TASK-002's two defect rules — and one ordinary test
that could not fail, and adding a fifth on purpose is not defence in depth. The collation is
also **not sufficient alone**, which is the other half of the argument: with only the index, a
direct `Northgate` into an empty table is *accepted*, and the next report filed for that
neighbourhood misses it on a `binary` lookup, tries to create a second job, and hands the
dispatcher a `500`. Both halves are in **CHG-023** with the alternatives declined.

**One thing was found while fixing rather than by the review, and it is the more interesting
of the two.** Writing the missing case for `length(trim(…)) between 1 and 120` — the clause
the review showed nothing reached — turned up that the clause was also *wrong*: SQLite's
`trim()` strips **spaces only**, so `{"neighbourhood": "   "}` was refused and
`{"neighbourhood": "\t\n"}` was stored. A whitespace-only location, admitted because it used a
different whitespace character. That is the review's fourth check paying twice: an unexercised
clause was not merely unproven, it was untrue.

### The third review of TASK-005 — four checks, three of them failed

**Chosen before the code was read**, from the failure shapes `AGENT.md`'s lessons table already
records, and deliberately **not** the four in the task file and **not** the four the second
review used. Each was settled by a mutation: break the behaviour, run the whole suite, revert.
**Every mutation in this section was reverted and `git status --short` was empty after each one.**

**The gate was run first and it is green**, which is the part of the remediation that holds.
`pytest` was run **three** times on the untouched tree — 264 passed, 1 skipped, every time — so
the intermittent failures the second review found are gone. `ruff`, `ci/fitness.py` (6 of 7
wired, FF-006 at 7 of 7), `ci/evals.py` (5 scorers × 2 cases), `tsc`, `lint`, `build` and all
**14** Playwright specs pass. A green gate is not the same as a proven claim, and the four
checks below are about the difference.

| Check | Result |
|---|---|
| **A rule enforced in service code that the store could have refused** | **Failed, and this is the Block.** Done criterion 3: *"a second job for the same location, inserted **directly against the database**, is refused by the store — not by the service layer."* It is not. `unique (scenario_id, location_key)` refuses only a **byte-identical** key, and the rule that makes two spellings one location — casefold, then collapse whitespace — lives entirely in `store/dispatch.py:location_key()`. Inserted directly beside a stored `northgate`, the store **accepts** `Northgate`, and it accepts `north  gate`; the board then renders `job_count: 2` at `['northgate', 'Northgate']` — two crews, one neighbourhood, which is the single failure AC-007 exists to prevent. The mutation shows exactly how far the tests reach: deleting `.casefold()` turns **one** test red, `ITEST-003::test_the_same_place_written_differently_is_still_one_place`, which files both reports **through the endpoint**. No store-level assertion exists, and `store/dispatch.py`'s own docstring — *"delete this module's find-first logic and the database still refuses the second job"* — is false for the case that matters. The store can express it: `unique (scenario_id, location_key collate nocase)`, or a `check` that the stored key is already normalised. |
| **A property asserted only within one process lifetime, when the decision says the state is durable** | **Failed.** CHG-018 makes `seq` the history and `read_all` calls that history *"the order it happened, not a view of it"* — durable state, and ADR-002's promise is that *a restart is not an incident*. Every test that asserts the order builds **one** application. Mutation: hold the sequence beside the connection (`_SEQ[(id(connection), table)] += 1`) instead of taking it from the table inside the insert — the obvious way to write a counter, and identical in behaviour within one process. **All 264 tests still pass.** A second application over the same database file then fails to file a damage report at all: the counter restarts at 1, `unique (seq)` refuses the row, and the dispatcher gets `500 internal_error` for the first thing they type after a restart. `AGENT.md`'s second lessons row already says what was owed here — *one test must cross a restart* — and `conftest.build_application` exists for exactly that, written for TASK-001's review. It was not used for the durable state this task introduced. |
| **A described state with nowhere in the schema to live** | **Failed — and it is the same shape the second review found, one link further out.** §3 makes `damage_reports.repair_job_id` **optional**; §1 says a report belongs *"to **at most** one repair job"*. `api/views.py`'s `board_body` groups reports by that column and then emits one item **per job**, so a report with no job lands in a bucket keyed `None` that nothing reads. Two open reports in one storm, one of them unattached: the board returns `report_count: 1`, the second report is on no screen, and `open_reports_in_area` — an **inner** join through `repair_jobs` — logs `open_reports_in_area=1` for a neighbourhood that has two, which is the REQ-NF-007 figure being wrong in the direction that under-reports. All 264 tests pass with that row in the table. Reachable only by a direct insert today, which is what was said about the storm-scope hole one review ago. Raised as **CHG-022**, proposed, because §3 permits the state and no document says what the board does with it. |
| **A check that was never fed data without the condition it reports** | **Failed.** The CON-003 location constraint done criterion 4 rests on has four clauses. Three are exercised by UTEST-012 — `json_valid`, `json_type(...) = 'text'`, and the `json_object` rebuild that catches an address, a meter id and a coordinate. The fourth, `length(trim(...)) between 1 and 120`, is exercised by **nothing**: no empty neighbourhood, no whitespace-only one, no over-length one, at the store or at the endpoint. Mutation: relax it to `between 1 and 100000` in migrations 007 and 008 **and** raise `NEIGHBOURHOOD_MAX` to 5000 — **264 pass**. The two numbers are also two hard-coded copies of one bound with nothing tying them together: leaving the schema at 120 and setting the service constant to 5000 turns the specified `400 validation_error` into `500 internal_error` for a 121-character neighbourhood, and the suite stays green through that too. |

**What held, and it is most of the remediation.** Both halves of AC-007 through the endpoint;
the `unique (scenario_id, location_key)` refusal for an identical key; the CHG-019 composite
foreign keys, refused directly against the database in both directions with the permitted case
beside them; `pragma foreign_keys = on`, without which every `references` clause would be
decorative; the CHG-018 ordering with the clock frozen, across three full runs; the three-way
neighbourhood / storm / asset figures, now genuinely different numbers; `dismissed_report_count`
and the `duplicate` reader; PTEST-002's named indexes and its positive guards; and the five new
Playwright cases, which are real coverage of a criterion that used to be satisfied by reading
source.

**Two observations, neither a finding.** Migration 008 changed `damage_reports.asset_id` from
`on delete set null` to `on delete cascade` — justified in the entry for `repair_job_id`, where a
composite child key cannot be nulled by halves, and applied to `asset_id` in the same breath.
Under 007 deleting an asset kept the report; under 008 it destroys it, which contradicts §4's
*a report naming no matching asset is still a report*. Inert today — **no `delete from` statement
exists anywhere in `backend/`** — and live the moment §7.2's *delete or replace a scenario* is
built. And `STEST-001`'s `DATA_ROUTES` still does not list
`POST /api/v1/scenarios/{id}/damage-reports`, the endpoint this task created; done criterion 9's
first half is covered only by the unknown-path case. The `SessionGuard` refuses before routing,
so the behaviour holds — but the row is free and the criterion names it.

### Author, fixer and reviewer are the same process, for the seventh time — and this row is the one most at risk of being read as a clean bill

**Q-026, stated plainly because the previous row said *Fixed — awaiting re-review* and this is
the review it was awaiting.** This run neither wrote TASK-005 nor fixed it, and had not seen the
code. That is worth something, and the evidence is in the table above: a reader who did not know
where the fixes were careful found three failures in work that had been mutation-checked
twenty-six times by its author and eight more times by its fixer. It is **not** independence. It
is the same model, under the same account, following instructions from the same person, with no
human between the work and its acceptance. **No real people exist for this prototype**; one
person holds every decision-owner role, and that was recorded as a deferral rather than resolved
with invented names. A third invocation of one process is not a third pair of eyes, and this
signature must not be read as one.

**What the pattern is starting to say is worth more than any single finding.** Three reviews of
one task have now each found something the previous one did not, and each new reviewer's checks
were chosen from the same short list in `AGENT.md`. That is not a story about this task being
unusually bad. It is a story about how much a directed mutation finds and how little a green
gate proves — 264 tests, six fitness functions, ten evals and fourteen browser cases were all
green while a second crew could be sent to one neighbourhood.

### The remediation row above is not a signature, and the difference matters here more than usual

**The agent that fixed the Block wrote the row recording that it is fixed.** That is one step
worse than the Q-026 problem the rest of this log carries: author and reviewer being the same
process is bad; author, reviewer and *the party judging whether the reviewer's finding was
addressed* being the same process is the whole loop closed on itself. So the row says **Fixed —
awaiting re-review** rather than Accept, because "the defects I was told to fix no longer
reproduce" is a statement about tests, and acceptance is a statement about judgement.

What the row is worth resting on is the **mutation evidence**, because it is checkable by
anyone: each fix names the change that turns its test red, and every one of those mutations was
applied, run, and reverted. The two mutations the second review used to prove `open_reports_in_area`
was unasserted now fail two tests each; disabling the service-layer scope check now fails a
test where it previously failed none; dropping either index PTEST-002 names now turns its
query-plan assertion red. **`git status --short` was empty after every mutation.**

**One finding was not fixed and is named rather than quietly closed.** `risk_scores.asset_id`
(migration 005) carries the same existence-not-membership foreign key that CHG-019 replaces on
`damage_reports`. It is written only from server-derived identifiers, never from caller input,
so it is not reachable the way the Block was — but it is the same defect, it is recorded in
CHG-019, and rewriting a fourth table inside a TASK-005 remediation would be scope this task
does not have.

### The second review of TASK-005 — four checks, three of them failed

**The four checks were chosen before the code was read**, from the failure shapes `AGENT.md`
already records, and deliberately **not** the four in the task file. Each was settled by a
mutation: break the behaviour, run the tests that claim to cover it, revert. Every mutation in
this section was reverted and `git status --short` is empty.

**Before any of the four, the gate itself failed.** The first `pytest -q` run on the untouched
tree passed; the second did not. Fifteen clean full-suite runs produced **five red ones**, and
two different tests were responsible:

- `ATEST-007::test_both_reports_are_visible_and_linked_to_one_job` — *"in the order they were
  called in — the queue is the history"*
- `ITEST-002::test_an_admin_may_read_the_decision_record` — *"ordered by when they happened"*,
  `assert ['change', 'recommendation'] == ['recommendation', 'change']`

**One root cause, and it is not TASK-005's alone.** Every chronological read in the store is
`order by <timestamp>, id`. `datetime.now(UTC).isoformat()` resolves to about 15.6 ms on this
platform — **1,999 of 2,000 consecutive calls returned an identical string** — and the tiebreak
`id` is a random UUID hex. Two rows written inside one tick come back in coin-flip order. That
is TASK-005's board (`reported_at`) and TASK-004's `decision_records` (`occurred_at`), whose
`read_all` docstring says *"the order **is** the history, not a view of it."* It is not, and it
has not been since migration 006 shipped. `latest_recommendation` picks with
`order by occurred_at desc limit 1` and can therefore return the wrong row outright.

| Check | Result |
|---|---|
| **The figure the log carries is an aggregate *for that neighbourhood*** (done criterion 5) | **Failed — the assertion cannot fail.** Two mutations of `open_reports_in_area`, each left green by all 249 tests: counting **every** open report in the storm (coarser than a neighbourhood), and counting reports **per asset** (finer than one — the thing REQ-NF-007 exists to forbid). Cause: every UTEST-012 case files into exactly one neighbourhood with no asset, so the right figure and both wrong ones are the same number. `AGENT.md`'s first lessons row in a new coat — a fixture where correct and incorrect agree. |
| **The board's performance claims can be made red** | **Held**, with one dead sub-assertion. A query per job turns the statement-count test red; dropping `damage_reports_scenario_status_job` turns the query-plan test red with `SCAN damage_reports`. But the `repair_jobs` half of that same assertion **cannot** fail: dropping `repair_jobs_scenario_status` leaves `sqlite_autoindex_repair_jobs_2`, created by `unique (scenario_id, location_key)`, serving the query, so the plan still reads `SEARCH … USING INDEX`. Also `statements_during` compares two counts with no positive guard — `0 == 0` would pass — though it captures 8 statements today, so it is real for now. |
| **A rule enforced in service code that the store could refuse** | **Failed, and this is the Block.** `api/dispatch.py`'s `find_asset` lookup is the *only* thing stopping a damage report in storm A from naming storm B's asset. Disabling it leaves 248 tests green and nothing red. Issued directly against the database, the store accepts both a cross-storm `asset_id` and a cross-storm `repair_job_id`; only a non-existent `scenario_id` is refused. `assets.id` is the whole foreign key, so membership of the storm is never checked. The store could refuse it — a unique index on `assets (scenario_id, id)` and a composite foreign key — and this is the failure the log predicted in advance and pre-committed to blocking on. **In fairness to the author:** migration 005 gave `risk_scores.asset_id` the same shape, so the pattern is repo-wide; TASK-005 is only where it first becomes reachable from **caller-supplied input**, which is what makes it live. |
| **A described state with nowhere in the schema to live** | **Failed.** Dismiss a job's only report — TASK-008's state, whose columns migration 007 already carries, and which the schema permits today — and the board returns that job as `location: {"neighbourhood": null}`, `report_count: 0`: a repair job on a shared dispatcher's board with no location and nothing behind it. The only stored form is `repair_jobs.location_key`, casefolded to `saltmarsh`, and CHG-017 explicitly **declined** a display column on the ground that *"the board derives a job's neighbourhood from its first report"*. That derivation has a hole, and the mutation shows exactly how far the tests reach: forcing every job's location to `null` turns ITEST-003's two-locations test red, so the **happy** path is asserted and the dismissed one is not. |

**Two smaller observations, neither a finding.** `DispatchBoard` has no Playwright spec — done
criterion 7 ("two reports render under one job; the empty state reads *no damage reported*")
is satisfied by reading the source and by nothing executable; the two e2e files cover
ATEST-004 and E2E-002 only. And `damage_reports.status` permits `'duplicate'`, which nothing
writes and the board's `status <> 'dismissed'` filter lets straight through.

**What held.** The rest of the task's own claims survived re-checking: both halves of AC-007,
the `unique (scenario_id, location_key)` refusal issued directly against the database, the
seven refused location shapes, the endpoint's `extra="forbid"`, and the rewritten
`no_endpoint_returns_reasons_on_their_own` — which is now genuinely red under the mutation that
first exposed it. `ruff`, `ci/fitness.py` (6 of 7), `ci/evals.py`, `tsc`, `lint`, `build` and
all 9 Playwright specs pass.

### Author and reviewer are the same process, for the sixth time — and a second agent is not a second person

**Q-026, and it has to be said plainly here because this row is the one most likely to be read
as independent review.** This review was run by a later agent invocation that did not write
TASK-005 and had not seen its code — which is why three checks failed where the author's five
held. That is worth something. It is **not** independence: it is the same model, under the same
account, following instructions from the same person, with no human between the work and its
acceptance. No real people exist for this prototype; one person holds every decision-owner
role, recorded as a deferral rather than resolved with invented names. **A different invocation
of the same process is not a second pair of eyes, and this signature must not be read as one.**

What it does demonstrate, and the reason to keep doing it: **a reviewer who did not write the
code found three failures in output that had already been mutation-checked 26 times by its
author.** The author's checks were good and none of them were wrong — they were chosen by
somebody who already knew where the code was careful.

### TASK-005's checks — the fifth review, and the first to find a test that proved nothing

Every test written for this task was mutation-checked: 26 mutations, each breaking one claim and
running only the tests that assert it.

| Check | Result |
|---|---|
| Both halves of AC-007 hold, and pull against each other | Held. *One job* is the de-duplication; *both visible* is the refusal to lose the second radio call. Mutation: making the second report at a location return the first — a plausible "de-duplicate" implementation — keeps the job count at one and turns two tests red. |
| The rule survives a service that forgets to look first | Held, **by the schema**. `unique (scenario_id, location_key)` on `repair_jobs`; the second job inserted **directly against the database** is refused. Mutation: removing the constraint leaves every functional test green and fails that one, which is the whole argument for ADR-002. |
| The grouping rule can be **absent** | Held. TASK-002's technique reused: a constant location key (one job for the whole storm) satisfies every "two reports, one job" assertion and fails *two locations produce two jobs*; a unique key per report fails the other three. Neither state is reachable now. |
| A household-level location can neither get in nor out | Held, three ways. The endpoint refuses an unknown field rather than dropping it; the store refuses seven location shapes including `{}` and a coordinate pair; the board carries `asset_id` and no coordinate, though the asset row stores one. Mutations on each turn the matching test red. |
| The board query is indexed, and constant in the report count | Held. Mutation: fetching reports per job passes every functional test and fails the statement-count assertion at 200 reports; removing the index fails the query-plan assertion. |
| **The "no reasons-only endpoint" check is real** | **It was not.** It walked `application.routes` for a path containing "reason" — and this FastAPI wraps `include_router` in a route whose own `path` is `None`, so the walk saw four documentation routes and **none of the ten endpoints**. It passed on its first run and stayed green when the mutation added a `/reasons` endpoint. Rewritten against the published OpenAPI paths, with a positive assertion beside it so a blind enumeration fails instead of passing. Now red under the same mutation. |

**That finding is the fourth instance of a gate that cannot fail** — after FF-002 (CHG-010),
FF-003 (CHG-013) and TASK-002's two defect checks — and the first found in an ordinary test
rather than in a fitness function. It has a row in `AGENT.md` now, stated generally: **an
assertion that nothing matches is worth nothing without an assertion, over the same
enumeration, that something known does.** It cost one mutation to find and would have survived
every review that reads code rather than breaking it.

**Both change entries are `proposed`, and that is the finding under *change scope*.** Every
previous entry in the log was raised and accepted in the same breath by the same person. These
two are decisions about the specification — where damage reports come from, and how precisely a
damage location may be recorded — and the second one narrows what the product may ever store.
The build could not proceed without deciding both; accepting them was not the agent's to do.

### TASK-004's checks, and the criterion that was corrected rather than coded around

| Check | Result |
|---|---|
| The 409 is decided **before** the write, not after | Held. `integration-tests.md` names the exact bug — *a handler that returns 409 after updating the row satisfies the status code and breaks the rule*. Mutation: removing the pre-write conflict lookup fails ITEST-002 on both the status and the byte-identical comparison. |
| A decision can never be actorless | Held, **by the schema**. `check (kind = 'recommendation' or actor_user_id is not null)` — issued directly against the database, an actorless `accept` is refused. Only the system's own recommendation may have no actor. |
| Both triggers refuse a real statement | Held. FF-004 issues an `UPDATE` and a `DELETE` and requires both to abort. Mutation: renaming one trigger drives `trigger decision_records_no_update is absent`. Checking the schema for two names would not have caught a trigger that was present and wrong. |
| Every delivered ranking is recorded | Held. FF-005 mutation: skipping the append drives `0 recommendation rows for one delivered ranking`. |

**AC-009 cannot be satisfied as written, and this is the finding.** STEST-005 expects a
non-admin's refused upload to append a row to `decision_records`. That table's `scenario_id` is
`not null references scenarios(id)` — and a *refused* upload has no scenario, by definition,
because refusing it is what stopped one being created. The refusal is currently recorded in the
security log with actor, reason and outcome, which satisfies "recorded" in the ordinary sense
but not STEST-005's wording.

Three ways out were put to the developer and **the third was chosen** (CHG-015): the refusal
goes to the **security log** with actor, time, filename and reason, and AC-009's wording is
corrected to say so. The reasoning is worth keeping: *the decision record holds decisions about
recommendations, and a refused upload is an access-control event, not a decision.* Nullable
`scenario_id` was declined because that constraint is part of what makes the audit table
trustworthy; a one-event table was declined as not worth its own schema. **STEST-005's
assertion is now real rather than skipped** — the suite has no skipped tests left.

### Author and reviewer are the same person, for the fourth time

Q-026. The note from TASK-003's row stands and gets stronger with repetition: **the pattern of
these reviews passing is not evidence they are sufficient.** Four tasks have now been signed by
the person who wrote them.

### TASK-003's review — the eval harness paid for itself immediately

| Check | Result |
|---|---|
| Reasons come from the same computation as the score | Held. Mutation: authoring the strength as a constant drives `contributed 3% and claims Strong, not Slight` in both the suite and FF-007. |
| The weights and design references drive the arithmetic | Held. Both asserted with **non-default** values — inverted weights reorder the list, weaker line ratings reorder it again. |
| An unscorable asset is never scored low | Held. Mutation: scoring it 0 instead of UNSCORED fails two tests. This is the most dangerous failure in the product and the cheapest to introduce. |
| A recalibration cannot rewrite history | Held, **after being written for this review**. Mutation: deriving `weight_set_version` at read time from live configuration passes every other test and silently relabels every historical ranking the day anyone calibrates. |

**And the finding the checks did not produce.** `EVAL-001`'s `stale_inputs_disclosed` failed at
demo scale: **138 of 185**. Cause was a filter dropping any reason whose factor contributed
zero — so an asset rated 5/5 *six years ago* produced no condition reason and its rank said
nothing about resting on a six-year-old inspection. 189 tests passed while that was true,
because the eight-asset fixture had no such asset. Fixed: every computed factor now carries a
reason, including one that scored zero, since *why* it scored zero is often the most useful
sentence on the panel.

That is the strongest argument available for keeping the eval harness separate from the suite.
It scores a distribution against a threshold; the suite checks examples. Only the first could
see 47 silent ranks in a population of 185.

### Author and reviewer are the same person, for the third time

Q-026. As before, **this acceptance is worth less than one by somebody who did not write the
code.** Two of the four TASK-002 checks changed the code; one of the four here did, and the
eval harness changed it again. The pattern holding is not evidence the reviews are sufficient —
it is evidence the code has never been read by anyone else.

### TASK-002's four directed checks — two found real defects

Run **before** the signature, and each one mutation-checked. The most valuable was the first,
and it is the one worth reusing: **remove each defect from the fixture in turn and require the
matching finding to disappear.**

| Check | Result |
|---|---|
| Each of the seven defect rules fires by its **own** check | **Two were fake.** Defect 3 returned a finding whenever `weather.csv` carried any asset-linked row — it detected the file's existence, not absent gusts. Defect 6 matched "routine" and "scheduled", so `Routine inspection - no action` tripped a *repair-record* check. Both fired on every dataset, so **FF-006 was counting to 7 with 5 real checks behind it.** Both narrowed; all seven now stop firing when their defect is removed, with no collateral. |
| The scenario write is atomic | Held. Asserted by failing between the scenario insert and the asset insert — the only window a half-loaded storm could exist in. FTEST-001's other cases all fail during *parsing*, before a row is written, so none of them would have noticed. Mutation: removing the rollback fails it. |
| Two scenarios never blend | Held. Every read scoped by `scenario_id`; ITEST-005 formalises it under TASK-009, the scoping exists now. |
| BR-003 is enforced by the store, not the loader | Held. Removing the loader's guard leaves UTEST-003's assertions passing, because they issue their `insert` against the database. That is the property, demonstrated rather than asserted. |

**Nothing was wrong with the data handling in either defect case** — wind still came from the
grid, failures still came from `outages.csv`. What was wrong was the *reporting*, and the gate
built on it. A check that cannot be absent is not detecting anything, which is the same family
as CHG-010's gate that could not fail — third instance of that shape, now with a named
technique for finding it.

### Author and reviewer are the same person again, for the same reason

Q-026: no other person exists for this prototype. As with TASK-001, **this acceptance is worth
less than one by somebody who did not write the code**, and it is the strongest available. What
partially compensates is that the checks were chosen and run before the account of them was
written, and two of the four changed the code.

### Author and reviewer are the same person, and this row says so

**Q-026 is why.** No real people exist for this prototype; one person holds every decision-owner
role, and that was recorded as a deferral rather than resolved with invented names. So the
separation this log is built on — the agent reports, a human judges — is unavailable here, and
the honest response is to name the gap in the row rather than let the signature imply a second
pair of eyes. **This acceptance is worth less than a review by somebody who did not write the
code, and it is the strongest one available until Q-026 is answered.**

What compensates, partially: the reviewer directed four checks *before* seeing the account of
them, and two of the four found the suite was not yet proving what it claimed.

| Check | Result |
|---|---|
| The deny path works | STEST-001 refuses all ten unbuilt data routes **and** an unknown path — the guard runs before routing, so a route added by TASK-002 is refused by default. Confirmed against a running server. |
| A session survives a restart | **Was not tested.** Every existing test used one application instance, so an in-memory session would have passed all of them. Now asserted by `test_ADR-002_session_survives_restart.py`, both halves — a live session outlives the process, and a signed-out one is not resurrected by it. |
| The timeout comes from configuration | **Was not tested.** Every test used ADR-006's shipped 240 minutes, so a hard-coded 240 would have passed the lot. Now asserted with a configured 30 minutes and a configured 2-hour cap. |
| No raw token in the table or the logs | Confirmed three ways: no column in any table, no occurrence in the raw database file **or its WAL** at byte level, and no log line. The password likewise. Only a SHA-256 digest and a bcrypt hash are stored. |

**Both new tests were mutation-checked**, because a test written after the code and passing on
its first run has proved nothing. Hard-coding the two limits made the configuration tests fail;
pointing the restarted application at a different database made the durability test fail. Each
was reverted and the suite is green: **70 tests, lint clean**.

**None of the three predicted failures appeared** (see *What to expect from the first reviews*
below) — but only the third was reachable in this task. TASK-001 builds no ranking, so nothing
could drop an unscorable asset, and it builds no per-action allow-list, so no deny path could be
missed. The third was reachable and was avoided deliberately: the role constraint is a `check`
in the schema and the acceptance test issues its `insert` against the database, not through
`create_user`.

**A fourth failure mode appeared that `AGENT.md` did not predict, and it is worth a row there:**
*a test suite that pins every value to the shipped default cannot tell configuration from a
constant.* Two of the four review checks were the same mistake in different clothes. It is not
a bug — the code was right both times — but the suite would not have noticed had it been wrong,
which is the same thing as not testing it.

This table is not the same as `01-docs/09-change-control/spec-change-log.md`, and the difference
is worth stating before the first entry blurs it. That log records **decisions about the
specification** — five were made during the interview itself. This one records **judgements
about output**: what an agent produced, and whether it was accepted. A specification change that
arrives *because* of a review gets a row in both, and the review row is the one that says why.

---

## Entry template

```
Date:
Item reviewed:        [task output, PR, generated tests, spec draft]
Requirement / Task:   REQ-### / TASK-###
Reviewer:

Layers checked:
[ ] Requirement fit   [ ] Architecture fit   [ ] Security & validation
[ ] Performance       [ ] Test evidence      [ ] Change scope
[ ] Maintainability

Findings:
1. [severity] [layer] — [finding] → [action]

Accepted because / Rejected because:

Decision:             Accept / Accept with follow-up / Revise / Reject / Block
Follow-up tasks:      TASK-###
Spec updates needed:  Yes / No → CHG-###
```

---

## Team review layers (Ch. 29 §29.4)

| Review layer | Main question | Evidence needed | Who helps | Decision |
|---|---|---|---|---|
| Requirement fit | Does this solve the user need? | Requirement ID and acceptance criteria. | Product manager, developer. | Accept / revise. |
| Architecture fit | Does this follow the agreed design? | Technical spec, ADRs, module boundaries. | Developer, architect. | Accept / refactor. |
| Security and privacy | Does this expose data or weaken controls? | Security checklist, permission tests. | Developer, reviewer. | **Block if unsafe.** |
| Test evidence | Do tests prove expected behavior and failure paths? | Unit, integration, UI, edge-case tests. | Developer, QA. | Accept / add tests. |
| Maintainability | Can the next developer understand this? | Clear naming, useful comments, updated specs. | Team reviewer. | Accept / simplify. |

> Review should not ask only "does this look good?" It asks whether the output satisfies
> requirements, respects architecture, passes tests, protects users, and keeps future
> maintenance clear.

**Two of these five have a standing *block* condition on this project**, decided in advance so
the judgement is not made under pressure at review time:

| Condition | Layer | Why it blocks rather than revises |
|---|---|---|
| An asset that could not be scored is absent from a ranking, or carries a default score | Security and privacy | The screen reads as safety, and the consequence is a crew not sent. It is a safety failure wearing a formatting bug's clothes. |
| A rule enforced in the service layer that the store could refuse | Architecture fit | It works, it passes, and the first refactor silently removes it. BR-002, BR-003 and BR-004 are enforced by the store on purpose. |

---

## What to expect from the first reviews

Written before the first review rather than after, so it can be checked against what actually
happens. `AGENT.md` predicts three failures on this project. If the first three reviews find
none of them, that is worth noticing as much as if they find all three.

| Predicted finding | Layer it appears in | Test that should have caught it |
|---|---|---|
| An unscorable asset dropped from the ranking | Requirement fit | FTEST-004 |
| A permission's allow path built, deny path absent | Security | The deny test for that row in `security-tests.md` |
| A store constraint implemented in a service instead | Architecture fit | UTEST-009 asserts the **store** refuses, not the caller |

---

> Blueprint: blueprints/05-review/01-logs/review-log.md
