# SGW Resilience Platform — specification workspace

An internal dashboard that loads a prepared storm scenario, ranks assets by risk with a
plain-words reason beside each rank, and records every recommendation and decision.
**It recommends; people decide.** All ten tasks are Done as of 2026-08-16; the code is in
`backend/` and `frontend/` at the repository root, not under `spec/`.

## Start here

| What you need | File |
|---|---|
| Why this exists, and for whom | `01-docs/01-intent/intent.md` |
| What is in and out of version one | `01-docs/01-intent/constraints-and-non-goals.md` |
| Which part the product competes on | `01-docs/01-intent/subdomain-map.md` |
| Every open question, with its owner | `01-docs/01-intent/open-questions.md` |
| What the system must do | `01-docs/02-requirements/requirements.md` |
| How it works for users | `01-docs/03-product-spec/product-spec.md` |
| How it is built | `01-docs/04-technical-spec/technical-spec.md` |
| The three drivers and their guards | `01-docs/02-requirements/driving-characteristics.md` · `01-docs/04-technical-spec/fitness-functions.md` |
| Why it is built that way | `01-docs/05-architecture/architecture-decisions/adr-index.md` |
| Endpoints, schema, the data boundary | `01-docs/06-api-and-data-design/` |
| Who may do what, and what happens when it breaks | `01-docs/07-security-and-reliability/` |
| The scoring boundary and its guardrails | `01-docs/07-security-and-reliability/ai-boundary-spec.md` |
| Requirement → task → test | `01-docs/08-traceability/traceability.md` |
| What changed, and why | `01-docs/09-change-control/spec-change-log.md` |
| The next unit of work | `02-tasks/01-planning/task-index.md` |
| How anything is proven | `03-tests/01-plan/test-plan.md` |
| **Rules for an AI agent — read before any task** | **`06-agent/01-instructions/AGENT.md`** |
| Context to hand an agent for one task | `06-agent/02-context/context-pack.md` |
| Whether generated code is acceptable | `05-review/02-checklists/code-review-checklist.md` |
| Deploy, roll back, recover, monitor | `07-ops/` |

## Working a task

1. Read `06-agent/01-instructions/AGENT.md`. Its rules are not summarised here.
2. Take **one** task from `02-tasks/01-planning/task-index.md`.
3. Build its context slice from `06-agent/02-context/context-pack.md`.
4. Prepare → implement → report. Never skip a stage.
5. Review against `05-review/02-checklists/code-review-checklist.md`, changed-file list first.
6. Record the outcome in `05-review/01-logs/review-log.md`.

## Never

- **Never edit anything under `01-docs/`.** The specification is an input to every task,
  never an output. A change there is a change-log decision first.
- **Never let the system act.** It ranks and records. No crew is moved, no command is sent
  to any system controlling the grid or water — no such path exists, at any version.
- **Never store a rank without its reasons**, or render an unscorable asset as absent or
  low-risk. An empty screen must never read as safety.
- **Never let the model score, rank, or band anything** (ADR-009). It phrases reasons the
  scorer computed. Only factor names and contributions enter a prompt — never an asset name,
  identifier, coordinate or note. Output naming a factor absent from its input is discarded.
- **Never write `UPDATE` or `DELETE` against `decision_records`**, and never drop its two
  triggers inside an unrelated migration.
- **Never answer an open question by guessing.** Stop and ask.

## Commands

**Two processes** (ADR-008): Next.js/TypeScript frontend → FastAPI/Python backend → SQLite.
One external service (ADR-009): a hosted OpenAI model that **phrases computed reasons and
invents nothing**. It is off the critical path — the ranking renders without it.

```
frontend   npm ci · npm run lint · npx playwright test · npm run dev
backend    pip install -r requirements.txt · ruff check · pytest
migrate    raw SQL — and every migration re-asserts both decision_records triggers
gate       bash ci/gate.sh — nine stages. The suite PLUS FF-001..FF-007 PLUS the
           trigger check PLUS the eval floor. Never the suite alone; the script
           exists so nobody has to recite the list. 07-ops/01-deployment/cicd-pipeline.md
```

## Where things stand

- **Stage:** specification complete and **all ten tasks Done** (2026-08-16). 634 tests, none
  skipped; seven fitness functions; ten evals; 36 browser cases; `bash ci/gate.sh` exits 0.
- **Done is not the same as decided.** Twenty-four change entries are `proposed` and **none is
  accepted**. Two contradict each other (CHG-034, CHG-035), and one live defect is knowingly
  unfixed — see the root `CLAUDE.md`, *Known open defects*.
- **The last review round is the weakest in the log and says so.** TASK-005 to TASK-009 were
  closed in one run; two of the five had a defect found and fixed by the run that then accepted
  them (Q-026, `05-review/01-logs/review-log.md`).
- **Blocking the LLM path only:** **Q-029** (cost guards — max calls per ranking, monthly
  ceiling, timeout) and **Q-030** (which pinned model). ADR-009 makes all four mandatory and
  sets none; a ranking phrases up to 220 reasons, so unbounded is an unbounded invoice.
- **Still open, and none of it blocks code:** **Q-018** — the "faster than today" baseline
  cannot be measured, because the client is fictional. **Q-028** — no restore rehearsed.
  **Q-026** — no real people exist; one person holds every role. **Q-019** reopened: recurring
  cost is no longer zero. **Q-006**, **Q-008** remain as recorded.
- **Calibration owed:** ADR-007's scoring weights are an assumption. The operator sessions
  exist to challenge them, and SGW's engineers have not seen them.
- **Generated by:** spec-driven-devkit v0.1.0

> Generated by: instructions/entrypoint.md — no blueprint produces this file, and the manifest
> contains no entry-point blueprint. `spec/README.md` is the file that comes from
> `blueprints/README.md`; attributing this one to it would be a back-link nobody could audit.
