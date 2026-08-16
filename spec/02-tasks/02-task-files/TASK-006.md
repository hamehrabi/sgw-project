# TASK-006: Re-rank on a forecast change, keeping the previous order

> Written from the template in `TASK-001.md` when the task was picked up.

---

**Task ID:** TASK-006
**Task title:** Re-rank on a forecast change, keeping the previous order
**Priority:** P1
**Status:** In review — built 2026-08-16. Two change entries raised and left **proposed**: **CHG-025** (a scenario's forecast series had nowhere to live, and nothing decided what "the next forecast change" is) and **CHG-026** (`risk_scores` had no enforcement of *never rewrites n*).
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
| PTEST-001 (re-run — the re-rank limit it measures is this task's operation) | `03-tests/03-non-functional/performance-tests.md` |
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
