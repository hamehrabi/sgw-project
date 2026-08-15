# Constraints and Non-Goals

> Source: Ch. 30 §30.2, Ch. 5 §5.6, Ch. 6 §6.5.
> Out-of-scope decisions are as important as in-scope decisions — they protect focus and
> stop the agent from adding features you never approved.

## Constraints

A constraint is a fixed condition that limits the solution. State real-world limits before
implementation, because AI agents invent ideal solutions.

| ID | Type | Constraint |
|---|---|---|
| CON-001 | Technology | No technology is mandated. "A specific technology is mandated" was offered in Round 2 and not selected, so the stack is an open decision taken in Round 5 rather than a limit imposed here. |
| CON-002 | Time | Version one must be small enough to build in about one week. |
| CON-003 | Data | **Never stored, never logged, never on screen:** customer names, addresses, account numbers, meter IDs, phone numbers, or any premise-level record; individual household outage status; crew personal data beyond a display name and role; credentials, session values and reset links. **Permitted:** aggregate outage counts by feeder or neighbourhood, and a `critical_facility` boolean on an asset. This is the source PRD §8 privacy line — *neighbourhood totals rather than single homes* — as a schema rule (Q-007). |
| CON-004 | Environment | No environment ceiling is imposed. "Must run on a single small server" was offered in Round 2 and not selected; the deployment target is decided in Round 8. |
| CON-005 | Integration | Version one runs on prepared data files. Live connections to the four source systems — GIS, maintenance, weather feeds, field-ops tools — are out of scope, so no integration contract binds version one. |
| CON-006 | Budget | **Amended by ADR-009.** One paid third-party service: a hosted OpenAI model that phrases computed reasons. Nothing else. The original constraint — *no paid third-party services in version one* — held from Round 2 until ADR-009 and is quoted here because a reversed constraint should keep its own words. **A second paid service is a new decision, not an extension of this one.** |
| CON-007 | Compliance / privacy | The platform may only read from the systems that physically control the grid and the water network, and can never send them commands. Screens show neighbourhood-level totals rather than single households wherever possible. Both are carried from the source PRD (§8) rather than stated in the interview. |
| CON-008 | Team skill | An AI coding agent builds it, one task at a time, from the task files in `02-tasks/`. That makes the do-not-change list and the stop condition on each task load-bearing rather than advisory, and it makes `06-agent/` the centre of this workspace rather than a formality. |

**Examples (Ch. 5 §5.6)**

| Type | Example |
|---|---|
| Technology | The frontend must be built with plain HTML, CSS, and JavaScript for v1. |
| Time | The first working version must be small enough to build in one week. |
| Data | The system must not store payment card details. |
| Environment | The application must run on a low-cost cloud instance. |
| Integration | The system must export task data as CSV. |

> **Warning:** do not let a constraint become an excuse for poor design. A constraint
> guides the solution; it does not lower the quality standard.

---

## Non-goals / out of scope

State whether each item is excluded **permanently**, **deferred**, or **waiting for
information**.

| Item | Reason it is excluded now | Future status |
|---|---|---|
| Live connections to the four source systems (GIS, maintenance, weather feeds, field-ops tools) | Version one runs on prepared data files. Connecting the systems is the largest cost in the plan and it tests none of the three guesses that could end the project. | Deferred — P1 in the source PRD, unlocked once operators change decisions and act on the rankings. |
| Water early-warning on sensor readings | It serves the dispatcher's during-storm decision rather than the ranked-risk guess version one exists to test. | Deferred — P1. |
| Automatic summary writer for leadership | A language model plus a human approval step is a body of work with its own failure mode, and it tests no dangerous guess. | Deferred — P1. |
| Offline crew app, field photo capture, and route planning | The source PRD sequences all three after operators trust the ranking, and none of them can be trusted before that. | Deferred — P2. |

**Example (Ch. 6 §6.5)**

| Out-of-scope item | Reason | Future status |
|---|---|---|
| Real-time chat | v1 focuses on task tracking, not conversation. | Possible later version. |
| Mobile app | v1 will be web-only to reduce complexity. | After web workflow is stable. |
| Advanced reporting | Basic task status is enough for v1. | After users request specific reports. |
| Multiple assignees per task | Single ownership is simpler for v1. | Revisit after testing real team workflows. |

---

## Scope control habit (Ch. 6 §6.4)

For every feature you include, write one sentence explaining why it belongs in **this**
version. If you cannot explain the value, move it to the table above.

**Prioritization test (Ch. 6 §6.8):** if this feature is missing, can you still test the
main product idea? If yes, it is probably not a must-have for v1.

---

> Blueprint: blueprints/01-docs/01-intent/constraints-and-non-goals.md
