# SGW Resilience Platform — specification workspace

> **What this folder is:** the specification for this software. It is meant to be read,
> edited, and committed alongside the code — not archived and forgotten.
> **Who it is for:** anyone about to build, review, or change this software, including an
> AI coding agent.

**In one sentence, this software:** brings SGW's scattered storm information into one place so
the operations manager and the dispatcher decide from current, shared facts rather than
recollection — with people making every decision. The exact version-one capability set is not
yet decided; see Q-001 in [`01-docs/01-intent/open-questions.md`](01-docs/01-intent/open-questions.md).

**The problem it exists to solve:** SGW's storm decisions rest on facts that sit in four
systems which do not share data, so the crew plan is rebuilt by hand whenever the forecast
shifts, the damage picture is assembled from radio calls and a whiteboard, and no numbers are
ready when a regulator calls — costing longer outages, penalty fees, premium-priced emergency
crews and rising insurance. Storm decisions should be made from one current, shared set of
facts.

> **The one rule to remember:**
> Before code, write the spec. Before accepting code, run the tests. Before release,
> review the risks. After release, update the spec when reality changes.

---

## Start here

| If you are… | Read |
|---|---|
| New to this project | [`01-docs/01-intent/intent.md`](01-docs/01-intent/intent.md) — the problem, users, goals, scope |
| About to build something | [`01-docs/02-requirements/requirements.md`](01-docs/02-requirements/requirements.md), then the task file for your piece |
| Reviewing a change | [`05-review/02-checklists/code-review-checklist.md`](05-review/02-checklists/code-review-checklist.md) |
| An AI coding agent | [`06-agent/01-instructions/AGENT.md`](06-agent/01-instructions/AGENT.md) — rules and boundaries first |
| Looking for what changed | [`01-docs/09-change-control/spec-change-log.md`](01-docs/09-change-control/spec-change-log.md) |

**Not every file below exists yet.** This workspace holds what the interview reached.
Anything deliberately left out is recorded as a dated row in the change log, with its
reason — so an absence is always either a decision or a gap, never a mystery.

---

## What each folder holds

| Folder | Purpose |
|---|---|
| `01-docs/` | Project direction and specifications. **The memory of the project.** |
| `02-tasks/` | Small, controlled work items for a person or an agent. |
| `03-tests/` | Test plans, expected checks, and test cases. |
| `04-src/` | The application code. |
| `05-review/` | Review notes and decision records. |
| `06-agent/` | AI assistant instructions and context summaries. |
| `07-ops/` | Deployment and maintenance notes. |

### Inside `01-docs/`

| Sub-folder | Holds |
|---|---|
| `01-intent/` | Why this exists: the brief, the intent document, constraints and non-goals, open questions, and which parts of the system are worth the effort |
| `02-requirements/` | What it must do, and the three qualities that shape how it is built |
| `03-product-spec/` | How it should work for users |
| `04-technical-spec/` | How it is built: architecture, interface, runtime, and the checks that keep those true |
| `05-architecture/` | Decisions, each with its context and consequences |
| `06-api-and-data-design/` | Entities, endpoints, contracts, external services |
| `07-security-and-reliability/` | Who can do what, and what happens when something fails |
| `08-traceability/` | Requirement → test → code, in both directions |
| `09-change-control/` | Versions, stage acceptance, and every deliberate skip |
| `10-reference/` | Glossary, tools, and the process itself |

---

## Where does this information belong?

The question that keeps a specification usable is not **"is this written down?"** but
**"would the next person look for it here?"**

| If you are writing about… | Put it in |
|---|---|
| The problem, users, non-goals | `01-docs/01-intent/` |
| A behaviour the system must have | `01-docs/02-requirements/requirements.md` (REQ-…) |
| User journeys, personas, priorities | `01-docs/03-product-spec/product-spec.md` (US-…) |
| Architecture, modules, data flow | `01-docs/04-technical-spec/technical-spec.md` |
| A design choice and its trade-offs | `01-docs/05-architecture/architecture-decisions/` |
| Endpoints, contracts, status codes | `01-docs/06-api-and-data-design/api-specification.md` |
| Entities, fields, indexes, retention | `01-docs/06-api-and-data-design/database-design.md` |
| Who can do what | `01-docs/07-security-and-reliability/security-specification.md` |
| What happens when something fails | `01-docs/07-security-and-reliability/reliability-specification.md` |
| The next unit of work for an agent | `02-tasks/02-task-files/TASK-###.md` |
| How a requirement will be proven | `03-tests/01-plan/test-specification.md` |
| Whether generated code is acceptable | `05-review/02-checklists/code-review-checklist.md` |
| How the release ships and rolls back | `07-ops/01-deployment/` |
| Rules the AI agent must always follow | `06-agent/01-instructions/AGENT.md` |
| The context an agent gets for one task | `06-agent/02-context/context-pack.md` |

---

## Reading order

Each document is an input to the next. Read down the chain; write down it too.

```
01-docs/01-intent/          why this exists
        ↓
01-docs/02-requirements/    what it must do
        ↓
01-docs/03-product-spec/    how it works for users
        ↓
01-docs/04-technical-spec/  how it is built
   ├─ 05-architecture/         and why, decision by decision
   ├─ 06-api-and-data-design/  contracts and entities
   └─ 07-security-and-reliability/
        ↓
01-docs/08-traceability/    kept current from here on
        ↓
03-tests/                   how it is proven
        ↓
02-tasks/                   what gets built next
        ↓
04-src/                     the code
        ↓
05-review/  →  07-ops/      review, ship, operate
        ↓
back to 01-docs             when reality changes the spec
```

---

## Stage gates — do not pass until true

| Gate | Condition |
|---|---|
| Intent → Requirements | Problem, users, goals, constraints and non-goals are written. |
| Requirements → Product spec | Every requirement is testable and has acceptance criteria. |
| Product spec → Technical spec | Main user flows and first-version scope are clear. |
| Technical spec → Tasks | Architecture, data, APIs, security and errors are defined. |
| Tasks → Tests | Each task is small, bounded, and has done criteria. |
| Tests → Code | You can answer: *"How will I know this works without trusting the agent blindly?"* |
| Code → Review | Only approved files changed; tests added or updated. |
| Review → Deploy | Requirements met, tests pass, rollback written. |
| Deploy → Maintain | Monitoring is live and the specs match deployed behaviour. |

---

## Rules that apply at every stage

- **Do not ask an AI agent to build a feature** until you can explain the requirement,
  acceptance criteria, expected tests, failure states, and review standard.
- **Do not ask an agent to "build the whole app."** One bounded task at a time.
- **Exploration is not implementation.** Brainstorm freely, then write the requirement
  before asking for code.
- **The ambiguity test:** could two competent developers build two different things from
  this instruction? If yes, add detail.
- **The one-outcome rule:** if a task has more than one major outcome, split it.
- **Testability is the first quality filter.** If you cannot test a requirement, rewrite it.
- **Refactor only after tests exist.** Behaviour change is not refactoring.
- **A fix is incomplete** until code, tests, and specification agree.
- **When behaviour changes, update the spec** — in the same change, not later.

### The central question

> Can this feature be traced from requirement → specification → task → test → code →
> review → deployment?
>
> If yes, the specification is doing its job. If no, there is a gap to find.

---

> Blueprint: blueprints/README.md
