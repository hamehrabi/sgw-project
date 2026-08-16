# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# SGW Resilience Platform

An internal dashboard that loads a prepared storm scenario, ranks assets by risk with a
plain-words reason beside each rank, and records every recommendation and decision.
**It recommends; people decide.**

## The specification is in this repository

It lives at `spec/`, and every task is driven from it. **Nothing under `spec/01-docs/` is ever
an output of a task** - it is an input to all of them, and a change there is a change-log
decision first (`spec/01-docs/09-change-control/spec-change-log.md`).

`proj-knowledge/` holds the client briefing documents the specification was derived from. They
are history, not requirements: where the two disagree, `spec/` is the decision and the briefing
is what was thought before it.

| Before any task, read | Path |
|---|---|
| **Rules for an AI agent** | `spec/06-agent/01-instructions/AGENT.md` |
| The workspace entry point | `spec/CLAUDE.md` |
| The next unit of work | `spec/02-tasks/01-planning/task-index.md` |
| The context slice for that task | `spec/06-agent/02-context/context-pack.md` |

If `spec/` is absent, **stop and ask** — do not infer the specification from the code.

**Work one task at a time, in three stages — prepare, implement, report — never skipping one**
(`AGENT.md`). Prepare means restating the task, listing the files you will touch, and naming
your assumptions *before* editing. Report means naming the requirement covered, the tests that
should pass, and any file you changed that the task plan did not list.

**When two documents disagree, the change log is newer.** Five accepted documents were corrected
in place during the interview (CHG-001…005) and each left an older sentence somewhere a careless
reader can still find. Two live examples are in *Known spec drift* below.

## Where things stand

**TASK-001 is Done** — accepted at review, with the author-is-reviewer conflict recorded in
`review-log.md` rather than hidden (Q-026).

**TASK-005 is back In review, for the third time.** Five of ten tasks are built — sign-in,
upload/parse/joined view, the ranked risk list, the append-only decision record, and the
dispatch board — but the fifth was **blocked at a second review and blocked again at a third**,
and each round's findings were fixed on 2026-08-16 (`TASK-005.md`, *What the third review
found*). It is not Done until somebody who did not fix it says so. **TASK-006 (re-rank on a
forecast change) is next, and must not be started on the assumption that TASK-005 is accepted.**

**Three reviews of one task have each found something the previous one did not, and every one
of them was found by a directed mutation rather than by the gate.** 264 tests, six fitness
functions, ten evals and fourteen browser cases were all green while a second crew could be sent
to one neighbourhood. Treat a green gate as the start of a review, not the end of one.

**The gate is five commands, and the test suite is only one of them:**
`pytest` (294) · `ruff` · `ci/fitness.py` (6 of 7 wired) · `ci/evals.py` (the quality floor) ·
`playwright` (14, real Chromium against both processes).

**Run the suite more than once before calling the gate green.** Five of fifteen clean runs were
red before migration 008, from one root cause, and a suite run once looks green half the time.
**A total order needs a key that is total:** `datetime.now(UTC).isoformat()` resolves to about
15.6 ms here and a random UUID is not a tiebreak, so `repair_jobs`, `damage_reports` and
`decision_records` each carry a monotonic `unique` `seq` and every chronological read orders by
it (CHG-018). `decision_records` could not be backfilled — the `BEFORE UPDATE` trigger refuses
the statement, which is BR-004 working.

**The scenario is the scoping root, and a foreign key must carry it.** `references assets (id)`
proves an asset exists; it never proved the asset is in *this* storm. `damage_reports` now uses
composite keys `(asset_id, scenario_id) → assets (id, scenario_id)` (CHG-019). One instance of
the same shape is knowingly unfixed and named in that entry: `risk_scores.asset_id`.

**A damage location is a neighbourhood and can be nothing else.** CON-003 forbids any
premise-level record, so `damage_reports.location` is constrained by the schema to exactly
`{"neighbourhood": …}` — an address, a meter id or a coordinate is refused by the database
(CHG-017). Two consequences: "the same location" in AC-007 *means* the same neighbourhood, and
REQ-NF-007's "aggregated in every log and export" holds by construction, because nothing finer
is stored to leak. **Two reports at one location are one repair job**, enforced by
`unique (scenario_id, location_key)` on `repair_jobs`, not by the code that looks first.

**And which two spellings are one location is also the schema's, not the code's** (CHG-023,
migration 009). A `unique` over a derived key only enforces identity across the spellings that
key can hold, so `repair_jobs` refuses a `location_key` that is not already lower-cased,
trimmed and singly-spaced — `Northgate` and `north  gate` bounce at the database, not at
`store/dispatch.py`. **One length bound**, 120, lives in both schema checks and in
`dispatch.NEIGHBOURHOOD_MAX`, and UTEST-012 reads it out of `sqlite_master` so the copies cannot
drift; when they do, the specified `400 validation_error` silently becomes a `500`.

**Nine change entries are `proposed` and await a human decision** — the first that were not
self-accepted: **CHG-016** (no endpoint created a damage report, so AC-007 could not occur),
**CHG-017** (`repair_jobs.location_key`, and the resolution of `damage_reports.location`),
**CHG-018** (a monotonic `seq` — a timestamp is not a total order), **CHG-019** (composite
foreign keys, so a report cannot name another storm's asset), **CHG-020** (a job's neighbourhood
survives the dismissal of the report it came from), **CHG-021** (`damage_reports.status =
'duplicate'` given a reader), **CHG-022** (a damage report belonging to no repair job is on the
board and in the area figure), **CHG-023** (normalisation and the single bound, above) and
**CHG-024** (a report whose asset is deleted — the cascade kept, the alternatives recorded).
All are built except CHG-024, which is a record rather than a change; none is accepted.

Seven change entries have been raised from implementation, all accepted: **CHG-008** (a
`sessions` table), **CHG-009** (`GET /api/v1/auth/session`), **CHG-010** (FF-002 was a gate
that could not fail under ADR-008, restated), **CHG-011** (three columns added to the prepared
format, because defects 4 and 5 could not otherwise be represented — this one knowingly breaks
Q-017's "nothing invented"), **CHG-012** (a `scenario_uploads` table), **CHG-013** ("last good
picture" meant two things and one of them could not happen — split into data-age and
file-integrity; FF-003 was vacuously true and is restated), **CHG-014** (two of ADR-007's
four factors compare against reference values that exist in no document — now per-type
constants with public sources, uncalibrated on the same footing as the weights).

**Staleness is the age of the data, never the presence of a file.** Reads are served from
stored rows (`technical-spec.md` §6), so a lost source file leaves the picture *correct* — it
is reported to an admin as breaking replay and recovery, and the screen is not degraded.
`SCENARIO_STALE_AFTER_HOURS = 6`, from the National Hurricane Center's 6-hourly advisories.

**No assertion is skipped any more.** AC-009 was corrected by **CHG-015**: a refused upload is
recorded in the **security log** with actor, time, filename and reason — not in
`decision_records`, which holds decisions about recommendations. A refused upload is an
access-control event, and writing it to the audit table would have meant making `scenario_id`
nullable, trading the constraint that makes that table trustworthy for one event type.

**Mutation-check anything that guards something** before recording it as working — every new
fitness function before its register row changes, and any test written after the code it
covers. Two TASK-001 tests and one TASK-002 test would have passed against a wrong
implementation; all three were found this way, not by review.

Nothing blocks building. **Q-029** (LLM cost guards) and **Q-030** (which pinned model) block
the ADR-009 phrasing path *only* — the ranking is required to render without it. What is still
open elsewhere (Q-018, Q-026, Q-028) blocks *claiming* things, not *building* them.

## Architecture

**Two processes** (ADR-008), holding **five named modules** with a one-directional import rule
(ADR-001). The process line is what makes the boundary structural rather than conventional:

```
frontend/  Next.js / TypeScript       backend/  FastAPI / Python           SQLite
  views/            ──── HTTP ────►     app/api/     ──►  app/scoring/     one file,
  screens, the      (same-origin,       routes, identity,  THE CORE        single
  five states        via a Next          role checks       SUBDOMAIN       writer
  lib/api.ts         rewrite —                             app/loader/     (ADR-002)
  the only way       no CORS)                              parse, 7 defect
  to reach data                                            rules, matching
                                                           app/store/
                                                           schema, migrations,
                                                           triggers
```

Tests live in `spec/03-tests/05-executable/`, not beside the code — `pytest.ini` at the repo
root is what joins the two.

- **A view never imports `scoring/`** (FF-002). Across a process line this is now impossible
  rather than merely checked — do not reintroduce it by reimplementing scoring in the frontend
  "for display".
- **A route handler never contains a scoring rule or a matching rule** (FF-001).
- **The frontend never touches the store.** It calls the API.

**Data flow:** admin uploads → loader validates and parses in a **background job** → store holds
one joined record per asset → scoring produces ranks and reasons per forecast revision → API
authenticates and authorises → views render. Every read is served from **stored** results; a
re-rank is a write that produces a new revision. Every ranking served and every decision taken
appends a row to `decision_records`.

**The scenario is the scoping root.** Every other record belongs to exactly one, every read
carries it, and a missing scope is a correctness bug — two storms blended into one ranking would
look entirely plausible.

### Scoring (the part the product competes on)

Deterministic and hand-checkable (ADR-005, ADR-007): four weighted factors — forecast gust vs
design threshold 0.40, flood zone 0.25, age vs service life 0.20, condition decayed by inspection
staleness 0.15. Score = 100 × weighted sum; bands High ≥ 60, Medium 30–59, Low < 30.

- **Weights, band boundaries and reason-strength thresholds are configuration, never constants
  in code.** They are an unvalidated assumption awaiting calibration with SGW's engineers.
- **Reasons come out of the same computation as the score**, never a separate step. Strength is
  a factor's share of the total: ≥ 25% *Strong*, 10–25% *Moderate*, < 10% *Slight*.
- **Criticality is not risk.** A `critical_facility` asset is never scored higher — risk orders
  the planning list, criticality badges the dispatch queue.

### The one external service

A hosted OpenAI model **phrases reasons the scorer already computed** (ADR-009). Four rules, all
load-bearing: computed reasons stay the record of truth; **only factor names and contributions
enter a prompt** — never an asset name, identifier, coordinate, or note; every output is
validated against its input factor set before display and discarded on mismatch (FF-007); and
the model is **optional at runtime** — if it is slow, down, or over budget, the ranking renders
templated computed text and the product keeps working. A test must prove that last one.

### The store

One SQLite file, in-process, single writer (ADR-002). **Every constraint lives in the schema,
not in application code** — a rule that lives only in code is removed by the first refactor with
every test still green. `users.role` carries `check role in ('admin','user')`; a rank cannot be
written without at least one reason (BR-002); a condition never exists without its source and
age (BR-003).

`decision_records` is append-only, enforced by a `BEFORE UPDATE` and a `BEFORE DELETE` trigger
(ADR-004). **Those two triggers are BR-004's only enforcement.** Migrations are raw SQL and
re-assert both; a migration that drops one removes the guarantee and no functional test notices.

## Commands

Run everything from the repo root. The virtualenv is `.venv/`.

```bash
# setup, once
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt   # + httpx2
cd frontend && npm install

# the gate — the suite is NOT the gate on its own
.venv/Scripts/python.exe -m pytest                       # 294 tests, 1 skipped
.venv/Scripts/python.exe -m ruff check backend spec/03-tests/05-executable ci
.venv/Scripts/python.exe ci/fitness.py                   # FF-001, FF-002, FF-006
cd frontend && npx tsc --noEmit && npm run lint && npm run build
cd frontend && npm run e2e     # Playwright starts BOTH processes; no mocks

# running it — two processes
.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --port 8000
cd frontend && npm run dev                               # proxies /api to :8000

# accounts exist only here — no endpoint creates one, and none ever will
.venv/Scripts/python.exe -m app.cli create-user --name "Ops Manager" \
    --email ops@sgw.example --role admin
```

`PYTHONPATH=backend` is needed for `uvicorn` and `app.cli`; `pytest.ini` sets it for tests.
Configuration comes from the environment with **no defaults** — a missing value fails at
startup, named (ADR-006).

Running one test — files are named for their test ID, so the ID is the selector:

```bash
.venv/Scripts/python.exe -m pytest -k "STEST-002"
.venv/Scripts/python.exe -m pytest spec/03-tests/05-executable/unit
```

**The gate is the suite PLUS FF-001…FF-007 PLUS the trigger check** — never the suite alone
(`spec/07-ops/01-deployment/cicd-pipeline.md`). The fitness functions are a **separate stage**,
because folding them into the test run is exactly how FF-002 decays while every feature test
stays green. The trigger check runs *after* migrate and *before* deploy, and it is not a schema
inspection: attempt an `UPDATE` on `decision_records` and require the database to refuse it.

All seven fitness functions are currently marked **`Not wired yet`** in
`spec/01-docs/04-technical-spec/fitness-functions.md`, and TASK-010 is the task that wires them.
Do not edit that column to claim a gate nobody has built.

## Tests

Tests live in `spec/03-tests/05-executable/{unit,integration,end-to-end}/`, named
`test_<TEST-ID>_<slug>` so a CI failure points at a spec row rather than a line number. The
written plans they come from are in `spec/03-tests/01-plan/` … `04-failure/`; the mapping is in
`spec/03-tests/05-executable/executable-tests.md`.

**Tests come from acceptance criteria, not from the code you just wrote.** Three of them sit
deliberately below the application and must stay there — each is easy to "fix" into an
application-level check that passes and proves nothing:

| Test | Must assert against |
|---|---|
| STEST-008 | the database refuses the `UPDATE` — not a repository method |
| STEST-010 | the built artifact contains no outbound path — not an endpoint call |
| UTEST-009 | the store refuses a score written without reasons |

AI evals (`spec/03-tests/03-non-functional/ai-evals.md`) run in their own harness, not the test
folders — an eval scores a distribution against a threshold, and forcing it through the same
runner produces either a flaky suite or one that asserts nothing.

## Never

- **Never commit `.env` or any `*.db` file.** The database holds the append-only decision
  record and critical-infrastructure asset locations (ADR-002, ADR-004).
- **Never write `UPDATE` or `DELETE` against `decision_records`**, and never drop its two
  triggers inside an unrelated migration. A correction is a new row.
- **Never let the model score, rank, or band anything** (ADR-009). It phrases reasons the
  scorer computed, and only factor names and contributions enter a prompt.
- **Never let the system act.** It ranks and records. No crew is moved, no valve closed, no
  command sent to any system controlling the grid or water — no such path exists, at any version.
- **Never store a rank without its reasons**, and never render an unscorable asset as absent or
  low-risk. **An empty screen must never read as safety** — three of this product's screens look
  like good news when blank.
- **Never move a constraint the store could enforce into the service layer.**
- **Never answer an open question by guessing.** Stop and ask. The standing set is in `AGENT.md`;
  a task file's own stop condition narrows it.

Three failures are *predicted* rather than observed, and are worth watching for from day one:
dropping an unscorable asset because omitting the row is the tidiest code; implementing a
permission's allow path and not its deny path; and moving a store constraint into the service
layer because it is easier to write there. When a review finds a repeatable mistake, add a row to
the *Lessons from past mistakes* table in `AGENT.md` — the row is worth more than the fix.

## Known spec drift

Two documents predate ADR-008 and still describe the single-process Next.js stack. ADR-008 is
newer and governs:

- `spec/07-ops/01-deployment/cicd-pipeline.md` lists `npx vitest run` and `npx drizzle-kit
  migrate`. The backend is Python; migrations are raw SQL, precisely because `drizzle-kit`
  cannot generate the `decision_records` triggers.
- `Q-027` in `spec/01-docs/01-intent/open-questions.md` answers the stack as "Next.js with
  SQLite via `better-sqlite3`, one process". ADR-008 partially supersedes it — the frontend half
  stands, the server half does not.

## Where application code goes — settled during TASK-001

Root-level `backend/` and `frontend/`, so `spec/` stays a specification rather than becoming a
source tree. `spec/04-src/README.md` still describes the five modules and their rules and is
worth reading; treat its `04-src/…` paths as `backend/app/…` and `frontend/views/`. Tests were
never in doubt: `spec/03-tests/05-executable/`.
