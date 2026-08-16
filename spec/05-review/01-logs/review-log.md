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

**Decision values:** Accept · Accept with follow-up · Revise · Reject · Block

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
