# TASK-002: Upload and parse a prepared storm into the joined asset view

> Written from the template in `TASK-001.md` when the task was picked up, as
> `task-index.md` requires. One task = one outcome.

---

**Task ID:** TASK-002
**Task title:** Upload and parse a prepared storm into the joined asset view
**Priority:** P0
**Status:** Done — accepted 2026-08-15, `review-log.md`
**Assigned to:** AI agent

> **Where this stands.** Upload, parse, join, both read endpoints and the views are built and
> green: **153 tests, ruff clean, eslint clean, tsc clean, `next build` clean, fitness gate
> passing 3 of 7 wired**, plus a real-server smoke of upload → read → file-loss → re-read.
>
> **`SCENARIO_STALE_AFTER_HOURS = 6`** (CHG-013), from the National Hurricane Center's
> 6-hourly full advisories — a property of the forecast source rather than an inference about
> operators. P1: 3 hours during an active storm. Revisit if the forecast source changes.
>
> **E2E-002 is done.** Playwright drives real Chromium against both processes — five browser
> tests, no mocks. The harness (`ci/e2e_backend.py`, `frontend/playwright.config.ts`) is
> reusable by every later task, which is why it was built now rather than retrofitted.
>
> **Two assertions are skipped by name** so a run reports them rather than passing quietly:
> STEST-005's refusal-record half (TASK-004 owns `decision_records`) and ITEST-001's ranking
> half (TASK-003 owns the scorer). E2E-002's "reach a *rankable* scenario" is asserted as far
> as the boundary allows — the storm loads and its assets are readable.
>
> **The review changed the code.** Two of the seven defect checks were firing for the wrong
> reason and FF-006 was counting 7 with 5 real checks behind it. See `review-log.md`.

---

## Source requirement or spec section

REQ-F-001 · REQ-F-010 · REQ-NF-003 · SEC-Z-002 · AC-001, AC-002, AC-009, AC-010 ·
BR-003 · ADR-001 · ADR-002 · ADR-008 · CHG-001 · CHG-011

## Business reason

This is the task that gives the product something to be about. Every later slice reads assets;
none of them can be built, or reviewed by using them, until a storm can be loaded. It is also
the only place untrusted input enters the system, which is why its refusals matter as much as
its successes.

## Goal

An admin drags in a prepared storm; it is validated, parsed in the background, joined into one
record per asset, and readable in the asset view — each value carrying its source and its age.
A load that fails, fails whole and names the file.

## Inputs

- `01-docs/06-api-and-data-design/data-and-integration-spec.md` §1 (the format, as amended by
  CHG-011), §3 (the endpoint), §4 (**the seven defect rules**), §5 (failure behaviour)
- `01-docs/06-api-and-data-design/database-design.md` §1, §3 — `scenarios` and `assets`
- `01-docs/07-security-and-reliability/security-specification.md` §7 — the filled block for
  *Upload a prepared storm scenario*
- `01-docs/07-security-and-reliability/reliability-specification.md` — the staleness behaviour
- `01-docs/04-technical-spec/technical-spec.md` §9.5 — the background job's states
- `01-docs/04-technical-spec/frontend-component-spec.md` — `ScenarioUploadPanel`, `AssetTable`,
  `ScenarioSwitcher`, `StalenessBanner`
- `spec/.env.example` — `SCENARIO_UPLOAD_DIR`, the two size limits, the parse timeout

## Expected files or components

**Backend:** `loader/` filled — manifest validation, the four CSV parsers, the seven defect
rules, asset matching. `store/` gains migration 002 (`scenarios`, `assets`) and its queries.
`api/` gains `POST /api/v1/scenarios`, `GET /api/v1/scenarios/{id}`,
`GET /api/v1/scenarios/{id}/assets`, and the background parse job.
**Frontend:** `views/` gains `ScenarioUploadPanel`, `AssetTable`, `StalenessBanner`, and
`ScenarioSwitcher` beyond the empty state TASK-001 left.
**Fixture:** a prepared scenario carrying **all seven defects on purpose**.

## Expected output

- An admin uploads; the panel shows *uploading → parsing → ready* or *failed*, with the reason.
- A non-admin is refused `403`, no file is written, and the refusal is recorded (AC-009).
- Each asset appears **once**; records that cannot be matched load flagged `needs_review` and
  are surfaced, never merged on a guess and never dropped.
- Every value in the asset view shows its source and its age, and an estimated value is
  visually distinct from a measured one (BR-003).
- A parse that fails partway creates **no scenario**, and every already-loaded scenario still
  works.
- **FF-001 and FF-006 are wired into a runnable gate** (CHG-010).

## Step-by-step instructions

1. Migration 002: `scenarios` and `assets` exactly as `database-design.md` §3 specifies,
   including the `match_status` check and the BR-003 condition/source/age check.
2. The loader, as pure functions over parsed rows — no request, no HTTP, no store writes.
3. One check per defect rule in §4, each independently testable (UTEST-002…008).
4. Asset matching across differing codes. Anything below the bar is `needs_review`.
5. The upload endpoint: admin only, size before type, type by **content inspection** not
   extension, stored under a generated identifier.
6. The parse job. No automatic retry — a malformed file is a fact about the file.
7. The read endpoints, then the views.
8. Wire FF-001 (no import cycle) and FF-006 (7 of 7 defects caught) as a gate script.

## Dependencies

TASK-001 (done). ADR-005's scorer is **not** a dependency and must not be anticipated.

## Constraints / Boundaries

- Do not change unrelated files.
- **Do not build the ranking.** TASK-003 owns it, behind ADR-005's boundary.
- **Do not call OpenAI.** ADR-009's phrasing layer belongs to the scoring work.
- **Do not create `decision_records`** — TASK-004 owns it and its two triggers. The AC-009
  refusal record therefore has nowhere to go yet; see *Stop condition*.
- Do not resolve an unmatched asset by guessing, and never drop it.
- Do not compute a percentage from a stored total without an independent population figure.
- Do not derive the failure history from repair or maintenance records.

## Do not change

`decision_records` and its triggers — still not created. The scoring module — still empty, and
nothing here may anticipate it. Anything under `01-docs/` except through a change entry.

## Acceptance check / Done criteria

1. A fixture carrying all seven defects loads, and each defect is caught by its own check.
2. Each asset appears once; unmatched records are `needs_review` and visible.
3. Every displayed value carries source and age; estimated is distinct from measured.
4. A non-admin upload returns 403 and writes no file.
5. A file whose extension is allowed but whose content is not returns 415; an oversize file 413.
6. A partial parse creates no scenario and leaves loaded scenarios ranking.
7. A missing file after load shows the last good picture, stale, dated, and names the file.
8. FF-001 and FF-006 run and can fail.

## Tests to run or create

| Test ID | Defined in |
|---|---|
| UTEST-002 … UTEST-008 | `03-tests/02-functional/unit-tests.md` |
| ITEST-001 | `03-tests/02-functional/integration-tests.md` |
| ATEST-001, ATEST-002, ATEST-009, ATEST-010 | `03-tests/02-functional/acceptance-tests.md` |
| FTEST-001, FTEST-002, FTEST-003 | `03-tests/04-failure/failure-tests.md` |
| STEST-005, STEST-006, STEST-007 | `03-tests/03-non-functional/security-tests.md` |
| E2E-002 | `03-tests/02-functional/end-to-end-tests.md` |

## Out of scope

- Any score, rank, band or reason (TASK-003)
- The dispatch board (TASK-005) and switching between storms (TASK-009)
- `decision_records` and any audit write (TASK-004)

## Stop condition

**Stop and ask** rather than proceeding if:

- **AC-009's refusal record has nowhere to go.** `decision_records` does not exist until
  TASK-004, and STEST-005 expects a refusal appended to it. Either the table arrives early or
  the assertion defers — that is a scope decision, not a coding one.
- ITEST-001's "and rank it" half is reached. It belongs to TASK-003; building a placeholder
  scorer to satisfy it would be anticipating the module this task must not touch.
- A defect rule appears to need a column the format does not carry. That was CHG-011 once
  already; a second one is a decision, not a guess.

---

> Written from: blueprints/02-tasks/02-task-files/TASK-001.md
