# TASK-006: Re-rank on a forecast change, keeping the previous order

> Written from the template in `TASK-001.md` when the task was picked up.

---

**Task ID:** TASK-006
**Task title:** Re-rank on a forecast change, keeping the previous order
**Priority:** P1
**Status:** In review — built 2026-08-16, **blocked at review the same day**, and all three
findings plus all three observations fixed on 2026-08-16 (*What the review found, and what was
done about it*, below). Four change entries raised and left **proposed**: **CHG-025** (a
scenario's forecast series had nowhere to live, and nothing decided what "the next forecast
change" is), **CHG-026** (`risk_scores` had no enforcement of *never rewrites n*), **CHG-027**
(a forecast the file carries is not a revision that can be read back, and the screen offered
both as one list) and **CHG-028** (three invariants on `risk_scores` the store could hold and
did not). **It is not Done until somebody who did not fix it says so.**
**Assigned to:** AI agent

---

## Source requirement or spec section

REQ-F-004 · AC-005 · US-006 · ADR-002 · ADR-005 · ADR-007 · `technical-spec.md` §6 (every read
is served from stored results; a re-rank is a **write** that produces a new revision) ·
`technical-spec.md` §7.2 (allowed to both roles) · `technical-spec.md` §7.3 (`forecast_revision`
is validated and **never** silently falls back) · `api-specification.md` — endpoint index row
`POST /api/v1/scenarios/{scenario_id}/forecast-revisions`, and the `GET /risks` block's
`forecast_revision` query parameter ("an earlier value returns that earlier ranking unchanged
(AC-005)") · `database-design.md` §3 — `scenarios.forecast_revision` and
`risk_scores.unique (scenario_id, asset_id, forecast_revision)` ·
`frontend-component-spec.md` — `ForecastRevisionControl` · `reliability-specification.md` §
duplicate protection ("a re-run cannot produce two rankings for one revision") and § recovery
("a revision is one transaction").

## Business reason

**The forecast moving is the event this product exists for.** `intent.md`'s current pain point
is that *"the forecast changes and hours of manual collection start again from zero"*, and the
desired outcome is *"the plan adjusts when the forecast changes instead of restarting"*. US-006
says the same from the manager's chair. A re-rank that started the plan over would deliver the
requirement's letter and none of its point.

**The second half of AC-005 is the harder half and it is a safety property, not a convenience.**
*"The previous order remains retrievable for comparison"* is what makes a re-rank safe to press
during a storm. A crew was placed against revision 0 and a decision was recorded against it
(TASK-004, TASK-007); if applying revision 1 rewrote revision 0, that decision would afterwards
be attached to a ranking that no longer exists in the form it was made against — the audit trail
would be intact and its subject would have changed underneath it. `acceptance-tests.md` lists the
risk for ATEST-005 in one line: *"a re-rank destroying the order a decision was made against."*

## What "the scenario's next forecast change" is, and why it needed deciding

**`weather.csv` carries `valid_time` and nothing said what to do with it** — this is **CHG-025**,
raised rather than guessed, and left `proposed`.

- `data-and-integration-spec.md` §1 gives `weather.csv` the columns
  `grid_cell_id, asset_id, valid_time, wind_gust_mph, rainfall_in`, and `technical-spec.md`
  sizes the fixture at *"220 assets, ~5,000 forecast rows"* — far more rows than one forecast
  needs. So the change REQ-F-004 applies is **already inside the prepared scenario**, which is
  what the requirement says: *"a changed forecast **inside** the prepared scenario"*.
- The loader took **one** gust per grid cell and discarded every other row, and `assets` holds
  **one** `wind_gust_mph`. The later forecasts had nowhere to live — `AGENT.md`'s third lessons
  row for the sixth time, and the reason it is checked at *Prepare*.

Decided, in CHG-025: **a forecast revision is one distinct `valid_time`** in the cell-level rows
of `weather.csv`, revisions numbered from 0 in chronological order, and **each revision is a
complete grid** — a cell with no row at that time keeps the value it had at the last time it did
(carry-forward, at load, once). Stored in two new tables so the store owns the rules. Revision 0
is unchanged from what TASK-002 already loads.

## Goal

A signed-in user applies the scenario's next forecast change. The whole list is scored again
against that forecast and written as revision **n+1**. Revision **n** is not touched — not by
this write, and **not by any statement the database will accept**. Both orders stay readable
afterwards, each one labelled with the forecast that produced it.

## Expected files or components

**Backend:** migration **010** — `scenario_forecast_revisions` and `scenario_forecast_cells`,
plus `risk_scores`' `BEFORE UPDATE` trigger; both `decision_records` triggers re-asserted.
Migration **011**, added at the remediation — `risk_scores` rebuilt with the composite asset key,
a conditional `BEFORE DELETE` guard and a `BEFORE INSERT` guard that a ranking names one of its
storm's own forecasts (**CHG-028**); both `decision_records` triggers re-asserted again.
`store/forecasts.py` — the series, the next revision, one revision's cells.
`store/scenarios.py` — the series written inside the load transaction; the asset read carries
revision 0's `valid_time`. `store/rankings.py` — `save_revision` (the ranking **and** the
scenario pointer, or neither), and the ranking read joined to its own revision's forecast.
`api/rerank.py` — one scoring pass over stored rows at one revision, shared with the load path.
`api/scenarios.py` — `POST /api/v1/scenarios/{scenario_id}/forecast-revisions`, and the revision
list on `GET /api/v1/scenarios/{scenario_id}`. `loader/load.py`, `loader/records.py` — the series
comes out of the parse. `api/views.py` — the gust value carries the `valid_time` it came from.
**Frontend:** `views/ForecastRevisionControl.tsx`, wired into `ScenarioView`; `lib/api.ts`.
**Fixtures:** `03-tests/05-executable/fixtures/storm-with-a-forecast-change/` — three forecasts,
two assets identical in every factor but their grid cell, so a swap between them has exactly one
possible cause. A new fixture rather than an edit to `storm-with-seven-defects`, which eleven
other tests and FF-006 are written against. `ci/synthetic.py` — its filler forecast rows are
dated **after** the issue time, so the demo-scale storm carries later forecasts rather than
earlier ones.
**Gate:** no new fitness function. FF-005 already covers the new revision's delivered ranking.

## Step-by-step instructions

1. Write `TASK-006.md` (this file) and read the requirement, AC and component rows it cites.
2. Write **ATEST-005** and **ITEST-004** first, against a fixture carrying a forecast change.
   Run them; confirm each fails because the feature is missing.
3. Migration **010**. Both new tables, the composite foreign key that carries the scenario scope
   (CHG-019's lesson applied before it is needed), `unique (scenario_id, valid_time)` so two
   revisions cannot claim one forecast time, the backfill of revision 0 from `assets`, and the
   `risk_scores` `BEFORE UPDATE` trigger (**CHG-026**). Re-assert both `decision_records`
   triggers. Ship an up and a down.
   **The task brief reserved 008 and 008 was already taken** — TASK-005's second remediation used
   it and its third used 009. 010 is the next free number; nothing else about the instruction
   changes.
4. The loader returns the whole series; the store writes it in the same transaction as the
   scenario and its assets, so a scenario never exists without its forecasts.
5. The endpoint: 404 for an unknown storm, **409** when the storm carries no forecast after the
   current revision, otherwise 201 with the new revision. The write is one transaction — the
   ranking **and** the pointer, or neither.
6. `GET /risks?forecast_revision=n` keeps working unchanged and now shows each revision's own
   gust, so the number a rank rests on cannot disagree with the number on screen (BR-003).
7. `ForecastRevisionControl`: apply, and switch between revisions to compare. Disabled while
   applying and when no forecast remains.
8. Mutation-check every test written. Run the whole gate.

## Constraints / Boundaries

- **A revision is a write; a read never writes one.** `GET /risks` must never compute, and must
  never fall back to the current revision when the requested one is absent (§7.3).
- **Never rewrite an earlier revision.** Not by `UPDATE`, not by delete-and-reinsert, and not by
  moving the pointer without writing the rows.
- **The model scores nothing** (ADR-009). This task adds no prompt and no phrasing path.
- **The response is a ranking, never an action** (BR-001, BR-005). Applying a forecast change
  moves no crew and sends nothing outside the platform.
- **Applying a revision is not a `decision_records` row.** `kind` is
  `in ('recommendation','accept','change','reject','dismiss','placement')` and none of them is
  this; the *ranking* the revision produces gets its `recommendation` row when it is delivered,
  which is FF-005 unchanged. Adding a seventh kind would be a schema decision this task does not
  own — the same reasoning CHG-021 used for `duplicate`. The application is recorded in the
  event log instead (CHG-015's reasoning, reused).
- Nothing under `01-docs/` is edited. CHG-025 and CHG-026 are entries in the change log.
- Do not build crew placement (TASK-007), dismissal (TASK-008) or storm switching (TASK-009).

## Acceptance check / Done criteria

1. Applying the forecast change writes revision **n+1** for every asset in the storm and
   advances `scenarios.forecast_revision` to it, in **one transaction**.
2. The order at revision n+1 differs from revision n when the forecast moved, and the difference
   is the forecast — two assets identical in every other factor swap places.
3. Revision n's `risk_scores` rows are **byte-identical** afterwards.
4. An `UPDATE` against `risk_scores` issued **directly against the database** is refused by the
   store, not by the service layer (CHG-026).
5. A second ranking for one revision, inserted **directly against the database**, is refused by
   `unique (scenario_id, asset_id, forecast_revision)`.
6. `GET /risks?forecast_revision=0` after revision 1 exists returns the revision-0 order
   unchanged, **writes nothing at all**, and leaves revision 1 current (ITEST-004).
7. An unknown revision is a 404 and never a silent fallback; applying when no forecast remains
   is a **409** that names the current revision and writes nothing.
8. Each revision's ranking shows the forecast it was computed from — the gust on the row, and
   the `valid_time` beside it (BR-003).
9. Every delivered revision has its own `recommendation` row, so what was shown at each revision
   can be reconstructed (REQ-F-009, FF-005).
10. An unscorable asset stays present and unranked at every revision, never scored low.
11. The revision pointer and the forecast series **survive a restart**, and the next apply
    continues from the stored pointer (ADR-002; `AGENT.md`'s standing rule that the restart test
    belongs to the task that introduces the durable state).
12. `ForecastRevisionControl` applies the change and lets the previous order be read back.
13. Migration 010 has an up **and** a down, both were run, and its backfill was run **against a
    database that already held a storm** — the branch every other test misses, because every
    other test migrates an empty file. Neither `decision_records` trigger is missing at any
    point of the round trip.

## Tests to run or create

| Test ID | Defined in |
|---|---|
| ATEST-005 | `03-tests/02-functional/acceptance-tests.md` |
| ITEST-004 | `03-tests/02-functional/integration-tests.md` |
| TASK-006 done criterion 13 (`test_TASK-006-AC13_migration_010_up_and_down.py`) | this file — the same way TASK-001 and TASK-003 wrote a test for a criterion no plan row owned |
| TASK-006 done criterion 2, the chronology half (`test_TASK-006-AC2_revisions_are_numbered_chronologically.py`) | this file — written at the remediation, because *the next forecast change* has no meaning without it |
| TASK-006 done criterion 12 (`frontend/e2e/ATEST-005.spec.ts`) | this file — the browser case the criterion named and nothing executable covered |
| PTEST-001 (re-run — **and extended to the endpoint**, which is the operation REQ-NF-001 names; the in-process cases measured a proxy for it) | `03-tests/03-non-functional/performance-tests.md` |
| STEST-001 (already lists this endpoint; it now exists to refuse) | `03-tests/03-non-functional/security-tests.md` |

## What the mutation check found

**All 29 cases were mutation-checked, and one of them was wrong.** Each mutation below breaks
one claim, was run, and was reverted; `git status --short` showed no unexpected file after each.

| Mutation | What turned red |
|---|---|
| The `risk_scores` `before update` trigger guards a different table — *present and wrong*, not absent | 1 — **and on the first attempt, nothing did.** See below. |
| The re-rank deletes revision n before writing n+1 | 9, including both halves of AC-005 and the restart |
| Every revision is scored against revision 0's forecast | 6, including the ALPHA/BRAVO swap |
| The ranking read always joins revision 0's forecast | 2 — the rank moves, the number beside it does not |
| No carry-forward: a revision holds only the cells that got a new row | 2 — CHARLIE goes unscorable at revision 2 |
| No further forecast answers 201 instead of 409 | 1 |
| The scenario pointer never moves | 13 |
| The applied revision is counted in process memory, keyed by connection | 5, including the restart |
| The forecast **series** is held in process memory | 1 — **only** the restart case, which is the case that claims it |
| Every ranking read appends a `recommendation` row | 3, including ITEST-004's *writes nothing* |
| An unknown revision falls back to the current one | 1 |
| `unique (scenario_id, asset_id, forecast_revision)` removed from migration 005 | 1 |
| The scenario response hides its revisions | 1 |
| ITEST-004's dump looks at one table nothing writes | 2 — the positive guard **and** the negative test it props up |
| Applying appends a `decision_records` row | 2 |
| Applying becomes admin-only | 2 |
| The unknown-storm check is removed | 1 |
| Unscorable assets are dropped from the re-rank | 1 |
| `forecast_revision` stops being an integer parameter | 1 |
| The forecast series is never stored | 23 of 25 |
| A carried-forward value claims the revision's own time | 1 |
| Migration 010's backfill selects nothing | 2 |
| The backfill takes the wrong gust / the wrong date | 1 each |
| The down migration drops a `decision_records` trigger | 1 |
| The down migration leaves the tables / the trigger behind | 3 / 2 |

**The one that was wrong.** `test_the_database_refuses_an_update_to_a_stored_ranking` set
`score = 0.0` across a whole revision — which includes the UNSCORED row, and BR-002's
`json_array_length(reasons) >= 1 or score is null` refuses that whether CHG-026's trigger
exists or not. Same exception type, same result: with the trigger removed the test **still
passed**. It now names a scored row and requires the refusal to be *this* rule by reading it
out of the message, and it carries a positive guard that the same connection can still write.
That is the fifth *assertion that could not fail for the reason it claimed* in this repository,
and the second found in an ordinary test rather than a fitness function.

**Two mutations were themselves wrong before they were right**, which is worth recording
because both failures were silent: renaming a trigger does not disable it, and a counter held
in a module-level dict does not reset between two `create_app()` calls in one pytest process —
`test_ADR-002_sequence_survives_restart.py` already keys its equivalent by `id(connection)` for
exactly that reason. A mutation that does not actually mutate reports a clean bill.

## What the review found, and what was done about it

**Three findings and three observations, all closed. Each fix names the mutation that now makes
it red, because that is the part a later reader can check.** Every mutation below was applied,
the relevant gate stage run, and reverted; `git status --short` showed no unexpected file after
each one.

| Finding | Fix | Mutation that is now red |
|---|---|---|
| **Chronological numbering (CHG-025, criterion 2) was asserted by nothing.** The only fixture listed its three forecast times already in chronological file order, so `enumerate(observed)` — dictionary insertion order, which is file order — passed all 323 tests. Handed a file that is not pre-sorted, that mutation numbers revision 0 as the 06:00 forecast and walks the storm backwards through its own weather. | `weather.csv` in `storm-with-a-forecast-change` now lists its three time blocks **06:00, 12:00, 00:00** — the file order, the text order and the chronological order are three different answers, and `test_TASK-006-AC2_revisions_are_numbered_chronologically.py` names all three. It asserts the fixture's disorder first (the haystack: if anyone tidies the file, the discrimination goes with it), then the numbering, then that each revision carries **its own** cells, then a fully reversed file producing an identical series, then two forecasts in different UTC offsets whose text order and true order disagree, then an unparseable `valid_time` (the `_chronological` branch nothing had reached), then the same property at demo scale, where the generator emits ~5,000 rows at randomly chosen times. | `enumerate(observed)` fails **17**, seven of them ATEST-005's. `sorted(observed)` — the plain text sort — fails the offsets case, which is the one that separates a parse from a string compare. |
| **Criterion 11 was half-proven: the restart test asserted nothing about the forecast VALUES.** It crossed a restart and then compared the two earlier **orders**, served from stored `risk_scores.rank` that no restart could lose, and that the next apply answered 201. Cells held in a per-connection temp table passed all 25 cases, and a second application over the same file re-ranked the whole storm to `ranked: 0, unscored: 5`. | The restart case now compares the **whole ranking**, values and all: the gust and its `valid_time` come from `scenario_forecast_cells` by a left join, so a lost series makes every one of them null while the order is untouched. It asserts the gusts are non-null **before** the restart (the haystack), the full `items` of revisions 0 and 1 after it, `ranked: 4, unscored: 1` on the next apply, and revision 2's own numbers including a carried-forward cell. A second case, `test_the_forecast_series_is_in_the_database_and_not_in_the_process`, reads all 15 cells back through the restarted application's own connection. | The review's own mutation — `save_series` writing the cells to a `temp table` that shadows the real one — fails **both** restart cases and leaves the other 24 green, which is the point it was making. |
| **Criterion 12 (`ForecastRevisionControl`) was covered by nothing executable, and the control had a reachable defect.** `GET /scenarios/{id}` lists the forecasts the **file** carries, so a freshly loaded storm reports `[0, 1, 2]` while only revision 0 is ranked; the control drew a selectable button per entry, pressing *Revision 2* got the 404 §7.3 requires, and `ScenarioView`'s single `catch` put the whole screen into an error state it never left — with accept / change / reject still offered beside a ranking that was not there. | **CHG-027.** Each entry carries **`ranked`**, read out of `risk_scores` rather than inferred from the pointer; the control renders an unapplied revision **disabled** and says *not applied yet, so there is no order to compare*; `ScenarioView`'s three reads settle independently, a ranking that could not be read is cleared rather than left standing, and `RecommendationDecision` is not rendered without it. **`e2e/ATEST-005.spec.ts`** is the browser case the criterion never had — three ordered tests over the real fixture in real Chromium. | Deleting the whole `<ul className="revisions__list">` block fails **3** browser cases (it used to leave all 14 green). Removing `disabled={!entry.ranked}` fails 2. Reporting every forecast as `ranked` from the backend fails the same 2 in the browser and 2 in `pytest`. |

| Observation | What was done |
|---|---|
| **Two invariants the store could hold and does not** — a direct `delete`-and-reinsert of revision 0 was accepted, and `risk_scores` carried no key on `(scenario_id, forecast_revision)`. | **CHG-028**, migration **011**. A `before delete` guard whose `when` clause fires only when both parents are still present — true of a direct delete, false inside either cascade, and both cascades asserted rather than reasoned about. A `before insert` guard that a ranking names one of its storm's own forecasts. And the composite `(asset_id, scenario_id)` foreign key, which closes the instance CHG-019 recorded as knowingly unfixed. The **foreign key** version of the revision rule was written, run and **withdrawn**, with the evidence in the entry: it makes 010's rollback destroy every stored ranking. Mutations: the delete guard absent, present-and-wrong, and unconditional; the insert guard absent; the asset key back to `references assets (id)` — five mutations, five different tests red. |
| **PTEST-001 measured a proxy for the operation this task created** — `load_scenario` plus `rank_assets` in process, touching neither the endpoint, nor `score_revision`'s join, nor `save_revision`'s 220-row write and pointer move. | Two cases added that drive `POST /forecast-revisions` at demo scale through the API, and one that asserts the **shape**: everything the re-rank does apart from writing one row per asset is constant between 110 and 220 assets. The in-process cases stay — they are what makes a regression name itself. Mutation: one lookup per asset inside `score_revision` — 122 statements at 110 assets against 232 at 220, red. |
| **Migration 010's backfill dates revision 0 from a different source than the loader does**, and the fixture could not tell them apart. | The fixture's manifest now says the advisory was issued at **21:00 on the 14th** while its earliest forecast is valid from **00:00 on the 15th** — two different strings. `test_the_backfill_dates_revision_zero_from_the_manifest_and_the_loader_does_not` names both, asserts which one survives a rollback round trip, and follows it to the value BR-003 puts an age beside. The backfill genuinely has no better source — `assets` carries the gust and never the time it was issued for — so the fix is to make the re-dating **loud** rather than to pretend it does not happen. |

**Two things this remediation did not do, named rather than left out.** The foreign key the
review named on `(scenario_id, forecast_revision)` is declined in writing in CHG-028, with the
rollback evidence. And `scenarios.forecast_revision` can still be moved directly to a revision
nothing has ranked; the pointer cannot carry a foreign key without a circular reference between
`scenarios` and `scenario_forecast_revisions`, and CHG-027's `ranked` flag is what stops the
screen believing it.

## Out of scope

Crew placement (TASK-007) · dismissing a false alarm (TASK-008) · switching between storms
(TASK-009) · **the joined asset view is not re-dated**: `GET /assets` is REQ-F-001's picture of
the storm **as loaded**, it carries revision 0's forecast and says so with the `valid_time`
beside the gust, and rewriting it in place is the one thing AC-005 forbids · no phrasing model
(Q-029, Q-030) · no new fitness function.

## Stop condition

**Stop and ask** if applying a revision appears to require rewriting or deleting an earlier
one, if a migration appears to need either `decision_records` trigger dropped, if the forecast
change would have to come from outside the prepared scenario (caller-supplied gusts are
untrusted input to a ranking, which is a different product), or if anything suggests the
platform should act on a re-rank rather than record it.

---

> Written from: blueprints/02-tasks/02-task-files/TASK-001.md
