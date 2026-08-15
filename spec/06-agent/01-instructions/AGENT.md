# AGENT INSTRUCTIONS

> Source: Ch. 4 §4.7 (`AGENT.md` starter) + Ch. 11 §11.8 (agent instruction file) +
> Appendix H.
> Keep this **short enough to reuse often**. If it becomes too long, the assistant may
> ignore parts of it. Version it: `AGENT v1.0`.

**Version:** AGENT v1.0

---

## Role

You are assisting with a **spec-driven software project**. Do not invent features. Follow
the approved requirements, specifications, tasks, and tests.

## Project goal

The SGW Resilience Platform, version one. An internal dashboard that loads a prepared storm
scenario from files an admin uploads, joins them into one record per asset, ranks those assets
by risk with a plain-words reason beside each rank, and records every recommendation it makes
and every decision a person takes. Two roles: admin and user. It **recommends and never acts** —
no crew is moved, no valve closed, no command sent to any system that controls the grid or the
water network. It exists to test three unproven guesses as cheaply as possible, in about a week.

## Current stage

**Task planning complete; implementation not started.** TASK-001 is ready to pick up. TASK-002
is blocked on Q-017, and eight tasks sit downstream of it.

---

## Source-of-truth order

When information conflicts, the higher item wins.

1. `01-docs/01-intent/intent.md`
2. `01-docs/03-product-spec/product-spec.md`
3. `01-docs/04-technical-spec/technical-spec.md` (+ `01-docs/05-architecture/architecture-decisions/`)
4. `01-docs/06-api-and-data-design/` — API specification and database design
5. `01-docs/07-security-and-reliability/` — security and reliability specifications
6. Current task file in `02-tasks/02-task-files/`
7. Existing code and tests

## Use these folders

| Folder | Contains |
|---|---|
| `01-docs/01-intent/` | Why the project exists: intent, constraints, non-goals, open questions |
| `01-docs/02-requirements/` … `09-change-control/` | Requirements, product spec, design, API, data, security, reliability, traceability |
| `02-tasks/` | Bounded work items and the task register |
| `03-tests/01-plan/` … `04-failure/` | Test plans and specifications |
| `03-tests/05-executable/` | Executable tests |
| `04-src/` | Application code |
| `05-review/` | Review checklists and evidence |
| `06-agent/` | Agent rules, context packs, prompts, handoffs |
| `07-ops/` | Deployment, monitoring, maintenance, runbook |

---

## Rules

1. **Follow the current task only.**
2. **Do not add unrequested features.**
3. **Do not change unrelated files.**
4. **Ask before making assumptions** that affect scope, security, data, or architecture.
5. **Explain important changes in simple language.**
6. **Connect every implementation change to a requirement and a test check.**
7. Do not remove or weaken tests to make code pass.
8. Do not introduce new dependencies without approval.
9. Do not expose secrets, tokens, or private data — in code, logs, examples, or output.
10. Do not rename public interfaces unless the task explicitly requires it.
11. If a request has no matching spec entry, **pause and ask** instead of implementing it.

**Rule 12, specific to this project: nothing under `01-docs/` is an output of any task.** The
specification is an input. Editing a requirement so your code passes inverts the whole method,
and the change belongs in `01-docs/09-change-control/spec-change-log.md` as a decision before it
belongs in code.

## Workflow rule

Before making changes: **restate the task, list the files you plan to inspect, and identify
assumptions.** Wait for approval if the task is unclear.

Work in three stages, never skipping one:

| Stage | You must |
|---|---|
| Prepare | Restate the task, list relevant files, identify assumptions. |
| Implement | Change only approved files; keep the solution small. |
| Report | Summarize changes, tests, risks, and unresolved questions. |

## Change rule

Change only files needed for the approved task. Do not refactor unrelated code.

## Testing rule

For behavior changes, add or update tests. Tests come from **acceptance criteria**, not
from the code you just wrote. If tests cannot be run, explain what should be tested
manually.

---

## Output format

Every completion must include:

- **Summary of changes**
- **Files affected** (and why each one)
- **Requirement covered** (REQ-### / TASK-###)
- **Tests added or updated, and which should pass**
- **Risks or assumptions**
- **Questions that need a human decision**
- **Any file changed that was not listed in the task plan**

---

## Not allowed (Appendix H)

- Do not invent requirements.
- Do not remove tests to make code pass.
- Do not introduce new dependencies without approval.
- Do not expose secrets, tokens, or private data.
- Do not expand scope without approval.

---

## Project-specific rules from ADRs

| ADR ID | Rule the agent must follow | Fitness function ID |
|---|---|---|
| ADR-001 | Every piece of logic lives inside a named module. A view never imports the scoring module. A route handler never contains a scoring rule or a matching rule. | FF-001, FF-002 |
| ADR-002 | Write every constraint into the schema, not into application code. Never implement a check in the service layer that the store could refuse. Never commit the database file. | — |
| ADR-003 | Never store or log a password, a hash, or a session identifier. Never check a session only in the browser. Never add a sign-in path, an account-creation path, or a third role. | — |
| ADR-004 | Never write an `UPDATE` or `DELETE` against `decision_records`. Never drop, disable, or recreate either trigger inside an unrelated migration. A correction is a new row. | FF-004 |
| ADR-005 | Never introduce a training step, a model file, or a learned parameter. The scorer is a pure function of the loaded scenario, and **the reasons must be produced by the same computation that produces the score** — never generated separately. | FF-005 |

> **Cite the ADR; do not restate the decision.** Every accepted ADR that constrains
> implementation gets a row here, and the right-hand cell is **the one imperative it puts on
> the agent** — "route handlers must not contain business rules" — not the decision, the options
> weighed, or the rationale. Those live in the ADR
> ([`../../01-docs/05-architecture/architecture-decisions/`](../../01-docs/05-architecture/architecture-decisions/)),
> which is the only place they are defined.
>
> This table used to arrive pre-numbered `ADR-001`, so it minted identifiers `adr-index.md`
> already owned and a run filled both — one decision with two homes, free to disagree the day
> either is edited. The ID column is blank now because it is a citation.

## Stop and ask — the five open questions

Reaching any of these means **stop**, not choose. Each has an answer an agent could plausibly
invent, and each invented answer would be indistinguishable from a decision.

| Question | What it governs |
|---|---|
| **Q-017** | Prepared scenario formats, file count, and sizes. Blocks TASK-002. |
| **Q-021** | Session idle timeout. Build the expiry check; do not pick a duration. |
| **Q-022** | Whether a second authentication factor is in version one. |
| **Q-025** | Scoring factors and weights. ADR-005 fixes the *kind* of scorer, not its content. |
| **Q-007** | Which data must not be stored. Add no field beyond `database-design.md` §3. |

## Lessons from past mistakes

> **Keep this section current.** Add a line here whenever a bug reveals a repeatable AI
> mistake (see `05-review/debugging-specification.md`). It is a standing habit, not a gap to
> fill once — so it stays in the delivered file rather than being replaced by an answer.

| Date | Mistake | Rule added |
|---|---|---|
| 2026-08-15 | **Every test pinned a configured value to its shipped default.** TASK-001's suite used ADR-006's 240 minutes and 12 hours everywhere, so a hard-coded 240 would have passed all of it. The code was right; the suite could not have told. Found by a directed check at review, not by the suite. | **When a value comes from configuration, at least one test must use a value that is not the default.** Otherwise the test proves the number, not that it was read. The same applies to every unset value in `.env.example`. |
| 2026-08-15 | **A durable-state property was asserted only within one process lifetime.** Every session test used a single application instance, so sessions held in memory would have passed — while ADR-002 promises "a restart is not an incident". | **Where a decision says state is durable, one test must cross a restart:** build a second application over the same database and assert the state is still there, and that ended state has not returned. |

| 2026-08-15 | **A specification described states with nowhere to keep them.** Three times: ADR-003 required a server-side session and §3 defined no `sessions` table (CHG-008); `frontend-component-spec.md` required `AppShell` to know the role and no endpoint returned it (CHG-009); §9.5 specified a parse job with four states while §9.1 forbade the scenario row existing until it succeeded, leaving the job's own state homeless (CHG-012). | **When a document defines states, a lifecycle, or a thing a screen must know, check the schema has a row that can hold it and an endpoint that can return it — before writing code against it.** A described state with no storage is not a design; it is a gap that looks like one, and it will be found at the worst moment by whoever builds against it. Check at the *Prepare* stage, where a change entry is cheap. |

The first two rows arrived together, at TASK-001's review, and they are the same mistake wearing
two coats: **a test that never varies the condition it claims to check.** Neither found a bug.
Both found an assertion nobody was making — which is what a review is for, and why the row is
worth more than the fix.

| 2026-08-15 | **Two of the seven defect checks fired for the wrong reason.** Defect 3 reported whenever `weather.csv` held any asset-linked row rather than when gusts were absent; defect 6 matched "routine", so an inspection note tripped a repair-record check. Both fired on every dataset, so FF-006 counted 7 of 7 with five real checks behind it. Neither affected the data handling — only the reporting, and the gate built on it. | **For any check that reports a condition, assert the silent case too: feed it data without the condition and require no finding.** A check that cannot be absent is not detecting anything. The general technique, and the one that found these: **remove each condition from the fixture in turn and require exactly the matching finding to disappear** — a suite that only ever sees the dirty fixture cannot tell one check from five. |

**The third row is a different kind and the most expensive one so far.** It cost three change
entries across two tasks, each found mid-build, and every one of them would have been visible in
five minutes of reading the schema against the document that described the behaviour. It is
cheap to check and it keeps being skipped, which is exactly what makes it worth a standing rule.

**Three failures are predicted rather than observed**, and are worth watching for from day one:
dropping an unscorable asset from a ranking because omitting the row is the tidiest code;
implementing a permission's allow path and not its deny path; and moving a store constraint into
the service layer because it is easier to write there.

---

## Agent rule checklist (Appendix H)

- [x] The agent is given the correct project context.
- [x] The task has a clear acceptance criterion.
- [x] The agent knows what it must not change.
- [x] The agent must explain assumptions before acting on them.
- [x] The agent must preserve tests and security rules.

---

> Blueprint: blueprints/06-agent/01-instructions/AGENT.md
