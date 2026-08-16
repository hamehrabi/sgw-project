# TASK-007: Record a crew placement against the ranking

> Written from the template in `TASK-001.md` when the task was picked up.

---

**Task ID:** TASK-007
**Task title:** Record a crew placement against the ranking
**Priority:** P1
**Status:** **Done** — accepted 2026-08-16 at its first review, by a run that did not write it
(`review-log.md`). **Read the Q-026 note in that row before reading this line:** the review found
a live defect and **the same run fixed it and then signed the task off**, which is the weakest
separation this log has recorded. Suite **634 + 0 skipped**, `ruff`, `ci/fitness.py` (**7 of 7
wired**), `ci/evals.py`, `ci/triggers.py`, `tsc`, `lint`, `build`, all **36** Playwright specs
and `ci/gate.sh`.

**What the review found.** A crew label of one **U+200B** or one **U+FEFF** was answered `201`
and written into `decision_records` — a placement under a person's name naming a crew nobody can
see, in the one table BR-004 forbids correcting. No mutation was needed; the request was enough.
`'   '`, U+00A0, U+2003 and U+3000 were all refused, so the rule looked present and was three
characters short of the alphabet CHG-037 had already decided one module over — and
`PlacementForm` used `String.prototype.trim()`, which removes U+FEFF, so the hole was invisible
from the screen. Raised as **CHG-039** and fixed: `store/blanks.py`, migration **016**,
`frontend/lib/blank.ts`, 33 new cases, **60 red with 016 removed**. The second check — done
criterion 2, *the revision the operator was looking at, not the storm's pointer* — **held** at
two red.

Two change entries raised and left **proposed**: **CHG-029** (`decision_records.kind` permitted
`'placement'` and nothing decided what a placement *is*, so the payload had no shape and the
store could not refuse a placement it cannot trace) and **CHG-039**. **Done is not the same as
decided**, and neither is accepted.
**Assigned to:** AI agent

---

## Source requirement or spec section

REQ-F-005 · BR-001 · US-007 · REQ-R-001 · REQ-NF-004 · CON-003 · ADR-002 · ADR-004 ·
`product-spec.md` §10 — the *Place crews against the ranking* flow, which is the only place
this feature is written out: *"Input: the placement — which crews wait where — against **named
assets**. System response: records the placement and writes one row to the decision record.
Success path: the placement is saved, visible, and **traceable to the ranking and forecast
revision it was made against**."* ·
`api-specification.md` — endpoint index row `POST /api/v1/scenarios/{scenario_id}/placements`,
*Signed in* ·
`database-design.md` §3 — `decision_records`, whose `kind` check already permits `'placement'`,
and its two append-only triggers ·
`frontend-component-spec.md` — `PlacementForm` ("Keeps every typed value on error. A placement
lost mid-storm is worse than an error message.") ·
`technical-spec.md` §7.2 and `security-specification.md` — *Record a crew placement: Admin yes,
User yes*, enforced by SEC-Z-001 ·
`end-to-end-tests.md` — **E2E-001**, written out in full, including its failure path.

## Business reason

**Without this the ranking is a report.** `product-spec.md` §7 says so in one line about the
planning view: *"It is where the ranking becomes a decision. Without it the ranking is a
report."* Success metric 1 is the operations manager reaching a crew placement from a loaded
scenario faster than the same decision takes today, and there is nothing to measure until a
placement can be reached at all.

**BR-001 is the rule this task is most able to break.** A "placement" is the closest thing in
the product to an instruction to move people, and it is the first feature whose *name* sounds
like an action. It is not one. Nothing is dispatched, nobody is notified, no crew is assigned
and no request leaves the platform — a placement is a row in the append-only record saying what
a person decided while looking at a particular ranking. Build it as an action and the product
changes category.

## What a "placement" is, and why it needed deciding

**`decision_records.kind` has permitted `'placement'` since migration 006 and nothing writes
one, nothing reads one, and no document says what the row contains.** That is exactly the shape
CHG-021 named one task earlier — *an enumerated value with no writer and no reader* — and it is
**CHG-029**, raised rather than guessed and left `proposed`.

Decided there, and the reasoning is in the entry:

- **A placement is one `decision_records` row of kind `placement`**, and not a table of its own.
  §3 already permits the kind; a new table would be a second home for the same fact, and the
  audit trail is where §10 says the placement goes (*"writes one row to the decision record"*).
- **Its subject is the ranking**: `subject_type = 'ranking'` and
  `subject_id = '<scenario_id>:<forecast_revision>'` — byte-identical to the `subject_id` the
  `recommendation` row for that ranking already carries, so the existing
  `decision_records_by_subject` index answers *"what was recommended here, and what did people
  decide about it"* in one lookup.
- **Its payload carries `crew`, `asset_ids`, `forecast_revision`, `recommendation_id` and
  `note`.** The "where" is a list of **asset ids and nothing else** — `product-spec.md` §10 says
  *against named assets*, and CON-003 forbids any premise-level record, so there is no address
  field, no coordinate field and no free-text location to leak. The "who" is a **crew display
  label**, which is the one piece of crew data CON-003 permits (*"crew personal data beyond a
  display name and role"* is what is forbidden).
- **The store refuses a placement it cannot trace** (migration 012). Every asset id must be on
  the ranking at the revision the placement names — which is `product-spec.md` §10's
  *traceable to the ranking and forecast revision it was made against*, expressed as something
  the database will not accept rather than as something the endpoint remembers to check.

## Goal

A signed-in operator, looking at a ranking, records which crew waits at which assets. One row
is appended to `decision_records`. It names the forecast revision the operator was **looking
at**, not the storm's current pointer. Nothing moves, and the confirmation says so.

## Expected files or components

**Backend:** migration **012** — `decision_records_placement_shape`, a `BEFORE INSERT` trigger
that fires only for `kind = 'placement'`; both `decision_records` triggers re-asserted, neither
dropped. `store/decisions.py` — `append_placement`, `placements_for`, `CREW_LABEL_MAX`.
`store/rankings.py` — `assets_in_ranking`, the membership read the endpoint's legible 400 sits
on. `api/placements.py` — `POST /api/v1/scenarios/{scenario_id}/placements`. `api/views.py` —
`placement_item`. `app/main.py` — the router.
**Frontend:** `views/PlacementForm.tsx`, wired into `ScenarioView`; `lib/api.ts`.
**Fixtures:** `03-tests/05-executable/fixtures/storm-for-the-planning-flow/` — E2E-001's
preconditions as written: all seven data defects **and** a forecast change, which no existing
fixture carries together. A new fixture rather than an edit to either existing one:
`storm-with-seven-defects` is what eleven tests and FF-006 are written against, and
`storm-with-a-forecast-change` is the one `e2e/ATEST-005.spec.ts` advances the pointer of, in a
browser run where `fullyParallel: false` and one database serves every spec.
**Gate:** no new fitness function. FF-004 already proves the append-only triggers survive
migration 012; FF-005 is untouched, because a placement is not a delivered ranking.

## Step-by-step instructions

1. Write `TASK-007.md` (this file), having read REQ-F-005, BR-001, `product-spec.md` §10,
   `frontend-component-spec.md`'s `PlacementForm` row, and E2E-001 as written out.
2. Write **E2E-001** first — the API half in
   `03-tests/05-executable/integration/test_E2E-001_place_crews_against_ranking.py` and the
   browser half in `frontend/e2e/E2E-001.spec.ts`. Run them; confirm each fails because the
   feature is missing rather than because of a typo. Add the store-level and migration cases the
   done criteria name, and the placement half of **FTEST-005**, which that row has always
   covered (*"a decision **or a placement**"*) and which only ever tested the decision.
3. Migration **012**. The `BEFORE INSERT` trigger, and both `decision_records` triggers
   re-asserted at the end. Ship an up and a down.
   **The task brief reserved 009 and 009 was already taken** — TASK-005's third remediation used
   it, and TASK-006 used 010 and 011. 012 is the next free number; nothing else about the
   instruction changes. This is the same drift TASK-006 recorded when 008 was reserved for it.
4. `store/decisions.py` appends the row through the same `_append` every other kind uses, so
   `seq` and the actor rule are not re-implemented beside it.
5. The endpoint: 404 for an unknown storm and for a revision with no ranking; 400 for a missing
   or over-long crew label, an empty or duplicated asset list, an unknown field, or an asset
   that is not on that ranking; otherwise 201 with the row as stored.
6. `PlacementForm`: keeps every typed value on error, confirms in words that nothing was
   dispatched, and is not rendered without a ranking on screen — the same rule
   `RecommendationDecision` follows (BR-001: a person decides while looking at a list).
7. Mutation-check every test written. Run the whole gate.

## Constraints / Boundaries

- **The response is a record, never an action** (BR-001, BR-005, REQ-R-003). No crew is moved,
  no job is created on the dispatch board, nothing is assigned, and no request from this module
  reaches anything outside the platform, at any version.
- **A placement is never a `repair_job` and never touches the board.** REQ-F-007's board is the
  during-storm list; folding a placement into it would make a computed ranking start ordering
  crews, which is the one thing `api/dispatch.py` already says it must not do.
- **Never write `UPDATE` or `DELETE` against `decision_records`.** A correction is a new
  placement row, exactly as a corrected decision is a new decision row.
- **Migration 012 does not drop, disable or recreate either append-only trigger.** It adds a
  third trigger beside them and re-asserts both, the way 008, 010 and 011 do. `decision_records`
  is **not rebuilt**: a check constraint would need the table recreated, which means dropping
  both triggers, which is the one thing ADR-004 forbids — 008 avoided the same rebuild for the
  same reason and used `alter table … add column`. The rule therefore goes in a trigger, which
  is CHG-026 and CHG-028(b)'s argument reused: *a rule the schema cannot express without
  destroying something else is a trigger, and it says the true and narrower thing — what may be
  written.*
- **No premise-level data enters the payload** (CON-003, REQ-NF-007). The API refuses an unknown
  field rather than dropping it, so an `address`, a `meter_id`, a `phone` or a `lat`/`lon` is a
  400 that names the field; and there is no column, key or field of any kind for one to be
  stored in. The crew is a display label; nothing about a person is stored or logged.
- **The model scores, ranks and bands nothing** (ADR-009). This task adds no prompt.
- Nothing under `01-docs/` is edited. CHG-029 is an entry in the change log, **proposed**.
- Do not build dismissal (TASK-008) or storm switching (TASK-009).

## Acceptance check / Done criteria

1. A placement appends exactly one `decision_records` row of kind `placement`, carrying the
   acting user, the crew label, the assets and the forecast revision.
2. **It records the revision the operator was looking at, not the storm's pointer.** Placing
   against revision 0 while the storm is current at revision 1 stores 0, and the row read back
   says 0.
3. The row names the ranking it was made against: `subject_id` is the same value the
   `recommendation` row for that ranking carries, and the payload names that
   `recommendation_id`.
4. **The store refuses a placement it cannot trace** — issued **directly against the database**,
   not through the endpoint: an asset that is not on that ranking, an asset from another storm,
   an empty asset list, a duplicated asset, a crew label that is blank, whitespace-only, over the
   bound or carries a control character, and a `subject_id` that disagrees with the payload's
   revision. Each refusal is read out of the message so it cannot pass for another rule's reason.
5. One length bound governs the crew label: the trigger's and `decisions.CREW_LABEL_MAX` are the
   same number, and a test fails when they disagree — otherwise the specified `400
   validation_error` silently becomes a `500` (CHG-023's lesson, applied before it bites).
6. A crew may be placed at an **UNSCORED** asset. It is in the ranking, not ranked, and refusing
   to let anyone plan around it would be the same failure as omitting it from the list.
7. A failed write shows no success, writes **no row**, keeps the typed placement on screen, and
   logs `DB_WRITE_FAILED` **without the crew label or the note** (FTEST-005, E2E-001's failure
   path).
8. Both roles may record a placement, and a signed-out caller may not (SEC-Z-001, STEST-001,
   which has listed this endpoint since TASK-001 and until now had nothing to refuse).
9. **No placement path issues any outbound action** (BR-001): no repair job, no damage report,
   no assignment, no message. Asserted as the whole database, not as a promise.
10. Migration 012 has an up **and** a down, both were run, and **both `decision_records`
    triggers are present and still refusing at every point of the round trip** — asserted by
    issuing a real `UPDATE`, not by reading two names out of `sqlite_master`.
11. `PlacementForm` records a placement from the planning screen in a real browser, shows which
    revision it was made against, says nothing was dispatched, and keeps every typed value when
    the write fails (`frontend-component-spec.md`; E2E-001's *THE TYPED PLACEMENT IS STILL ON
    SCREEN*).

## Tests to run or create

| Test ID | Defined in |
|---|---|
| E2E-001 — the API half (`integration/test_E2E-001_place_crews_against_ranking.py`) | `03-tests/02-functional/end-to-end-tests.md` |
| E2E-001 — the browser half (`frontend/e2e/E2E-001.spec.ts`) | the same row. *"An operations manager can go from a loaded storm to a recorded crew placement"* is a claim about a person at a screen, and `AGENT.md`'s standing rule is that such a claim needs a browser case |
| FTEST-005 (extended — the row says *"a decision **or a placement**"* and only the decision was ever tested) | `03-tests/04-failure/failure-tests.md` |
| TASK-007 done criteria 4, 5 and 6 (`unit/test_TASK-007-AC4_store_refuses_an_untraceable_placement.py`) | this file — the same way TASK-006 wrote a file for a criterion no plan row owned |
| TASK-007 done criterion 10 (`integration/test_TASK-007-AC10_migration_012_up_and_down.py`) | this file |
| STEST-001 (already lists `POST /api/v1/scenarios/{id}/placements`; it now exists to refuse) | `03-tests/03-non-functional/security-tests.md` |

## What the mutation check found

**Every case written for this task was mutation-checked — 27 mutations.** Each breaks one claim,
was applied, was run against the part of the gate that claims to cover it, and was reverted;
`git status --short` showed no unexpected file after each one. The counts are what actually turned
red, not what was expected to.

| Mutation | What turned red |
|---|---|
| The endpoint records `scenario["forecast_revision"]` instead of the revision the caller named | **2** — criterion 2, and the contract case, because a revision the storm never ranked stops being refused once the parameter is ignored |
| `subject_id` is the recommendation id rather than `scenario:revision` | **8** — the store refuses the row outright, which is criterion 4's subject clause doing its job from the inside |
| The whole placement trigger deleted from migration 012 | **22**, including `test_one_bound_governs_the_crew_label`, which is the haystack assertion earning its place |
| The trigger neutered but still present (`when 0`) | **19** — the bound tie stays green, correctly: its subject is the number, not the guard |
| The trigger **present and wrong**, conditioned on `kind = 'dismiss'` | **20**, including `test_the_placement_rules_leave_every_other_kind_alone`. Renaming or misconditioning a trigger does not disable it — the trap TASK-006 recorded |
| Clause 1 removed — the crew label | **9**, one per whitespace and bound case |
| Clause 2 removed — at least one asset, at most 500 | **2**, both ends of the bound |
| Clause 3 removed — each asset once | **1** |
| Clause 4 removed — the forecast revision | **1** |
| Clause 5 removed — the subject agrees with the payload | **1** |
| Clause 6 removed — the note | **1** |
| Clause 7 removed — assets are on that ranking | **5**, including the cross-storm asset, the unranked revision, and both migration cases |
| The endpoint's membership check removed, the trigger kept | **1** — the specified `400` becomes a `500`, the CHG-023 shape one column over |
| `CREW_LABEL_MAX` raised to 5000 with the trigger left at 120 | **3**, one of them the `400` that had become a `500`, and one the label *at* the bound no longer being accepted |
| The request model drops unknown fields instead of refusing them (`extra="allow"`) | **1** — an `address`, a `meter_id`, a `lat` and a `household` reach the payload |
| The endpoint accepts a duplicated asset (the store still refuses) | **1** — again the `400` that becomes a `500` |
| An UNSCORED asset is treated as not on the ranking, in the store **and** in the endpoint | **2** — criterion 6, the review log's first pre-declared Block condition one step out |
| The failed write is logged with the crew label and the note | **2** |
| The failure path answers 201 with nothing written | **2** |
| Placing becomes admin-only | **9** |
| 012's down migration removes an append-only trigger and does not re-assert it | **4**, two of them TASK-006's own migration cases |
| 012's down migration leaves the placement trigger behind | **4** |
| The endpoint stops refusing a revision the storm never ranked | **1** |
| The endpoint stops refusing an unknown storm | **1** — and **0 before the test was fixed.** See below |
| `PlacementForm` clears the typed values on a failed write | **1** browser case |
| `PlacementForm` is rendered without a ranking on screen | **4** browser cases |
| The confirmation stops naming the revision it was made against | **2** browser cases |
| The form sends no revision, so the server records the storm's pointer | **1** browser case |
| The confirmation drops the *nothing was dispatched* sentence | **1** browser case |

**One test was wrong and the mutation is what said so.** `test_the_endpoint_refuses_what_the_contract_says_it_refuses`
asserted that an unknown storm answers `404` with `code == "not_found"`. Removing the scenario
lookup **entirely** left it green: the request fell through to the revision check three lines
later, found no ranking for a storm that does not exist, and was refused there — a different rule,
the same status, the same error code. `404`, `400` and `409` each have more than one cause in this
API. The test now reads the refusal out of the **message**, which is the discipline the
store-level file already followed for every one of its seven clauses, and there is a row in
`AGENT.md` saying it stops at the module boundary unless somebody carries it across.

**And two of the mutations were themselves wrong before they were right, which is worth recording
because both failures were silent.** Anchoring on `setState({ stage: 'error', message:` in
`PlacementForm.tsx` landed in the **validation** branch rather than the `catch` branch — three
lines earlier in the file and a different rule — so the "clears the typed values" mutation left
all four browser cases green while changing nothing that runs on a failed write. And adding
`drop trigger decision_records_no_update` to 012's down migration is a **no-op**, because the same
file re-asserts both triggers four lines later; the real mutation is to remove the re-assertion.
That is the third and fourth time this repository has recorded *a mutation that does not actually
mutate reports a clean bill*.

## Out of scope

Dismissing a false alarm (TASK-008) · switching between storms (TASK-009) · **a placement list
endpoint**: `GET /api/v1/scenarios/{id}/placements` is not in the index and is **declined in
writing** in CHG-029 — a placement is readable by an admin through
`GET /scenarios/{id}/decisions`, and `frontend-component-spec.md` gives `PlacementForm` the
states *idle, validating, saving, success, error, permission denied* and no list state, so
adding one would be inventing a screen · **assigning, scheduling, routing or notifying
anybody** (`agent-task-list.md` A-011 names all three as out of scope, and BR-001 is why) ·
**a crew roster**: crews are a typed display label, because a table of crews is crew data
CON-003 has an opinion about and no requirement asks for · no phrasing model (Q-029, Q-030) ·
no new fitness function.

## Stop condition

**Stop and ask** if recording a placement appears to require creating a repair job, assigning
anyone, or sending anything anywhere; if it appears to require storing a location finer than an
asset; if a migration appears to need either `decision_records` trigger dropped — including for
a table rebuild, which is why the rule in 012 is a trigger; or if anything suggests the platform
should act on a placement rather than record it.

---

> Written from: blueprints/02-tasks/02-task-files/TASK-001.md
