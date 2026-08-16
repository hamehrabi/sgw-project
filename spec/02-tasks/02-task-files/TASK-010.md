# TASK-010: Wire the remaining fitness function into the build gate

> Written from the template in `TASK-001.md` when the task was picked up.

---

**Task ID:** TASK-010
**Task title:** Wire the **remaining** fitness function into the build gate — FF-003
**Priority:** P1
**Status:** Done — built 2026-08-16, `review-log.md`. The register's `Runs` cell moved only after
every clause had been seen to fail; the decisions that moving it required are **CHG-038**, proposed.
**Assigned to:** AI agent

---

## Source requirement or spec section

FF-003 · REQ-NF-003 · AC-002 · AC-010 · CHG-013 · CHG-010 · ADR-008 · ADR-002 ·
`technical-spec.md` §6 · `07-ops/01-deployment/cicd-pipeline.md` stage 4

## Business reason

**A fitness function written down but not in a gate governs nothing**, and `fitness-functions.md`
exists to catch exactly that decay. Six of its seven rows have run since TASK-004. The seventh has
said `Not wired yet` for nine tasks, with a reason that was true when it was written and had to be
re-examined once there were screens: *nothing on a render path opens a file, so remove a file and
open every screen cannot fail.*

The task the brief set was therefore not *write a check* but **decide honestly whether one can
fail** — and to leave it unwired, with the reason, if it cannot. Two of this project's most
expensive lessons are the same shape: FF-002 was a dead gate for a whole task under ADR-008
(CHG-010), and FF-003's own clause (a) was vacuously true before the views existed (CHG-013).
Wiring a third dead gate would be the decay committed by the file that warns about it.

## What was undecided, and how it was decided

The register defines *what* FF-003 checks. Three things it does not define had to be settled
before a line of the check could be written, and all three are in **CHG-038** with the
alternatives that were declined.

**(a) What *open every screen* is, under ADR-008.** All sixteen views are `'use client'` and reach
data only through `lib/api.ts`, so a screen's content is entirely the responses behind it. The
check drives **every GET the application serves**, discovered from the routing table rather than
listed — a screen a later task adds is covered without anyone remembering to add it. Driving
Playwright from inside `ci/fitness.py` was declined in writing: five files × two states × a
browser is the cost that gets a fitness function folded back into the test stage, which is the
decay stage 4 exists to prevent.

**(b) What *reads a source file* means — and left undecided, the register contradicts itself.**
`views.integrity()` calls `is_file()` on all five source files on the render path of
`GET /scenarios/{id}`. Under the most literal reading of clause (c) those five calls are the
violation — and then (c) forbids what (b) requires, because *the loss is named to an admin* cannot
be answered without looking. **(c) forbids a source file's contents reaching a response** — an
`open`, by any of Python's three doors — and asking whether a file exists is what (b) *is*.

**(c) How clause (a) is measured.** Its original sense still cannot happen and CHG-013 is right
about that. What is checked is the claim CHG-013 actually made: with a file lost, the picture does
**not** move.

## Goal

`ci/fitness.py` runs all seven fitness functions, blocks the merge when any fails, and says
nothing about FF-003 that has not been watched to fail first.

## Expected files or components

**Gate:** `ci/fitness.py` — `ff_003_a_lost_source_file_never_reaches_a_screen()` and
`ff_003_no_view_reaches_for_a_file()`, the `OpenProbe` recorder, the route walk, and the two
vacuity guards. `_loaded_and_ranked` now returns its client so the screen reads go through the
same signed-in session.
**Specification:** `fitness-functions.md` — FF-003's `Runs` and `On failure` cells, recorded as
**CHG-038** in `spec-change-log.md`, because nothing under `01-docs/` is an output of a task.
**Ops:** `cicd-pipeline.md` stage 4, which named TASK-010 as the task that changes it.

**No application file changes.** This task inspects the product; it does not alter it. Every
change to `backend/` and `frontend/` in this task was a mutation, applied and reverted.

## Step-by-step instructions

1. Load one storm into a live application and deliver its ranking (the FF-004/FF-005 helper).
2. Discover every GET from the routing table. **Prove the walk** against five named endpoints
   before reporting any absence over it.
3. Require the storm's five source files to be **on disk**. Without that, no clause can fail.
4. Install a recorder over `builtins.open`, `io.open` and `os.open`; drive every GET; then show
   the recorder a real source file through all three doors and require it to have seen them.
5. Baseline: every GET answers 200, every `data_age_hours` is stated, and the integrity block
   carries exactly `intact`, `missing_files`, `affects`.
6. For each of the five files: remove it → the notice names **exactly** that file with its
   consequence, nothing is opened, and every screen answers the same thing it answered before.
   Restore, corrupt it, and require the same again with the notice reporting the file present.
7. Scan `frontend/app`, `frontend/views` and `frontend/lib` for a reach into Node's filesystem —
   the half of (c) that runs outside a browser. Prove the scan found a named file first.
8. **Mutation-check every clause before the register's `Runs` cell moves**, and record what the
   rest of the gate said under each mutation.

## Constraints / Boundaries

- **Never edit `01-docs/` except through a change entry.** FF-003's row moved; CHG-038 is why,
  and it is **proposed** — nobody here is entitled to accept it.
- **Do not change application code to make a check pass.** Nothing in `backend/` or `frontend/`
  is modified by this task.
- **The check must fail the build**, not print a warning (`fitness-functions.md`, Rules).
- **A separate stage, never folded into `pytest`.** Folding them in is how FF-002 decays while
  every feature test stays green (`cicd-pipeline.md`, stage 4).
- Do not restate what FF-003 checks anywhere but the register — the id plus the characteristic
  is the whole of a citation.

## Acceptance check / Done criteria

1. `ci/fitness.py` exits 0 and prints `7 of 7 wired`; no line of it says `NOT WIRED`.
2. **Clause (c), the browser half:** a filesystem reach in a render-path module fails the gate,
   and was seen to.
3. **Clause (c), the backend half:** a screen read that opens a source file fails the gate, and
   was seen to — with the whole test suite green under the same mutation.
4. **Clause (b):** a loss the notice does not name fails the gate, per file.
5. **Clause (a):** a screen that degrades because a file is missing fails the gate — including at
   an endpoint no test covers for this, with all 534 tests green.
6. **The check cannot pass for want of anything to test:** with no source files on disk it reports
   the vacuity; with one door of the recorder unwatched it reports the canary; with a flat route
   walk it reports the four documentation routes.
7. `fitness-functions.md` says all seven run, and says how clause (a) is now measured.
8. The whole gate is green — suite, `ruff`, `ci/fitness.py`, `ci/evals.py`, `tsc`, `lint`,
   `build`, Playwright.

## Tests to run or create

| Test ID | Defined in |
|---|---|
| — | **The register is the assertion** (`task-index.md`). FF-003 is a gate stage, not a test: putting it in `pytest` is the one thing `cicd-pipeline.md` stage 4 forbids by name |
| FTEST-002, FTEST-003, ATEST-010 (re-run, not changed) | `03-tests/04-failure/failure-tests.md`, `03-tests/02-functional/acceptance-tests.md` — CHG-013's own tests, and the reason clause (b) had coverage before this task and clause (a) did not |

## What the mutation check found

**Every mutation was applied, the named stage of the gate run, and reverted, and
`git status --short` was checked after each one.** The middle column is what `ci/fitness.py` said;
the right-hand column is what the *rest* of the gate said, which is the number that matters.

| Mutation | FF-003 | The rest of the gate |
|---|---|---|
| `fs.readFileSync` of a scenario file in `app/page.tsx`, a server component | **red**, twice: the import and the call | `tsc`, `lint`, `build` all **green** |
| `views.integrity()` reads `manifest.json` to report its size | **red**, 10 lines — one per pass in which the file was there | **534 passed**, 1 skipped |
| The missing-file list emptied — the loss is no longer named | **red**, 10 lines, 2 per file | 3 FTEST-002 cases red |
| `GET /assets` returns nothing when a file is missing | **red**, 5 lines | 1 FTEST-002 case red |
| `GET /risks` returns nothing when a file is missing | **red**, 5 lines | **534 passed**, 1 skipped |
| The upload keeps no files on disk | **red** — *the storm's source files are not on disk … no clause of this check could fail* | not run; the guard is the point |
| The recorder leaves `io.open` unwatched | **red** — *saw 2 of its own 3 canary reads* | not run |
| The route walk is flat, as it was first written | **red** — *did not find `/api/v1/scenarios`; it found `['/docs', '/docs/oauth2-redirect', '/openapi.json', '/redoc']`* | not run |

**Two of these deserve to be read together, because they are the answer to the question this task
was set.** A view reading a scenario file at render time is invisible to `tsc`, `lint`, `build` and
all 36 browser cases in the frontend, and invisible to all 534 tests in the backend. That is what
*a check that could really fail* means here: not that the failure is likely, but that when it
happens nothing else in this repository will say so.

**And the flat route walk is `AGENT.md`'s 2026-08-16 lesson catching this task while it was being
written.** The first version of the walk read `application.routes` and found four documentation
routes and **none** of the seventeen endpoints — this FastAPI wraps `include_router` in a
`_IncludedRouter` whose own `path` is `None`. Without the five named routes asserted present, the
check would have reported *no file reads across zero screens* and passed on the first run, which is
precisely how TASK-005's `no endpoint returns reasons on their own` came to be worthless. It was
not caught by being careful; it was caught by the positive assertion being written first.

## The two things this task added that are not clauses

**A canary, because a recorder that records nothing is indistinguishable from a system that opens
nothing.** After the screen reads, the probe opens a real source file through all three doors and
requires to have seen all three. *Prove the haystack is a haystack before reporting no needle.*

**A vacuity guard, because the storm's files being on disk is a precondition of the whole check.**
Delete them after upload and the product still works — the loader parses from bytes in memory —
and every clause of FF-003 would pass for free. It now reports that state as a failure instead.

## Out of scope

Any change to `backend/` or `frontend/` · accepting CHG-038 or any of the other 22 proposed change
entries · moving the integrity check off the render path (declined in writing in CHG-038) ·
re-running the browser suite inside the fitness stage · the `npm`/`vitest`/`drizzle-kit` drift in
`cicd-pipeline.md`, which belongs to a different decision (CHG-024's rule about not smuggling a
change inside a remediation for something else)

## Stop condition

**Stop and ask** if wiring a clause would require changing application code to make it pass, if a
clause turns out to be unfailable and its row would therefore be claiming enforcement nobody
earned, or if the honest reading of a clause contradicts another clause of the same row — the last
of these happened, and it became CHG-038(b) rather than a guess.

---

> Written from: blueprints/02-tasks/02-task-files/TASK-001.md
