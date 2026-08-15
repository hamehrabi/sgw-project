# The Repeatable Spec-Driven AI Engineering System

> Source: Ch. 30 — "Building a Repeatable Spec-Driven AI Engineering System".
> A single successful AI-assisted project is useful. A **repeatable system** is much more
> valuable. This file holds the system-level guidance that governs how the rest of this
> template is used and improved.

> **Final chapter principle (Ch. 30):** the goal is not to use AI more. The goal is to
> build better software with clearer intent, stronger tests, safer review, and a process
> you can repeat on any project.

---

## 1. The reusable engineering process (Ch. 30 §30.1)

A reusable process is a defined path from first idea to production learning. It does not
remove judgment — it gives your judgment a structure.

> The process should be simple enough for a small feature and strong enough for a full
> production application. If it is **too heavy, people avoid it**. If it is **too weak, the
> AI agent fills gaps with assumptions**. The best process is lightweight, visible, and
> strict at the points where failure is expensive.

| Stage | Main artifact | Quality gate | Result |
|---|---|---|---|
| Idea intake | Engineering intent document | Problem, users, constraints, and non-goals are clear. | The team knows **why** the work exists. |
| Requirements | PRD and acceptance criteria | Each requirement can be tested or rejected. | The team knows what **success** means. |
| Design | Technical spec and ADRs | Architecture choices are explicit and justified. | The team knows **how** the system should be built. |
| Tasking | Agent task plan | Each task is small, bounded, and reviewable. | The agent receives **controlled work**. |
| Testing | Test specification | Expected behavior, failures, and edge cases are covered. | Implementation has a **target**. |
| Implementation | Code and test changes | Code matches specs and does not change unrelated behavior. | The feature becomes real software. |
| Review | Review checklist and traceability evidence | Output is checked against requirements, architecture, security, and tests. | The team decides what can move forward. |
| Release and learning | Deployment notes, monitoring, updated specs | Production feedback becomes a spec update. | The process **improves over time**. |

### Where this project stands on that path

| Stage | Artifact produced | Quality gate | Status |
|---|---|---|---|
| Idea intake | `intent.md`, `project-brief.md` | Problem, users, constraints, non-goals clear | ✅ Round 1–2 |
| Requirements | 10 functional, 7 non-functional, 3 role, 5 business rules, 10 acceptance criteria | Each testable or rejectable | ⚠ REQ-NF-006 is not testable — Q-013 |
| Design | Technical spec + ADR-001…005 | Architecture explicit and justified | ✅ Round 4–5, plus CHG-005 |
| Tasking | 10 tasks, 15 agent items, dependency map | Each small, bounded, reviewable | ⚠ TASK-002 blocked — Q-017 |
| Testing | 47 test ids across 8 levels | Behaviour, failures, edge cases covered | ⚠ 2 blocked — Q-012, Q-017 |
| Implementation | — | — | Not started |
| Review | — | — | Not started |
| Release and learning | — | — | Not started |

**The path stops at Tasking, and it stops for one reason.** Q-017 — what a prepared scenario
consists of — blocks the task that eight other tasks depend on. Everything upstream of that line
is complete; nothing downstream can start.

> **Reusable process rule:** do not design the process around one tool. Design it around
> **artifacts, decisions, tests, and review evidence**. Tools can change; the engineering
> system should remain useful.

---

## 2. Documentation organization and update triggers (Ch. 30 §30.2)

Documentation should be organized so a human **or an AI agent** can quickly find the
current source of truth. The structure does not need to be complicated — it needs to be
**consistent**. Every project should have the same broad sections, even if some are short.

| Section (this template) | Purpose | Typical contents | **Update trigger** |
|---|---|---|---|
| `01-docs/01-intent/` | Captures why the project exists. | Brief, goals, users, constraints, non-goals. | A new product idea, feature, or change request arrives. |
| `01-docs/02-…09-` | Defines what and how to build. | PRD, technical spec, API spec, database spec, ADRs. | Requirements or design decisions change. |
| `02-tasks/` | Turns specs into work. | Task list, agent briefs, status notes, handoff records. | A feature is broken into implementable steps. |
| `03-tests/` | Defines proof of correctness. | Test plan, test cases, edge cases, security tests, regression tests. | A requirement, API, or failure path changes. |
| `05-review/` | Stores human review evidence. | Code review checklist, security review, QA notes, traceability checks. | AI output is ready for acceptance. |
| `07-ops/` | Captures deployment and production learning. | Deployment plan, rollback plan, monitoring notes, maintenance checklist. | A release is prepared or production feedback arrives. |

---

## 3. The template library (Ch. 30 §30.4)

A template does not replace thinking. It makes sure important thinking is **not skipped**.

| Template | Used when | Minimum sections | Improvement signal | File |
|---|---|---|---|---|
| Engineering intent | A new idea or project begins. | Problem, users, value, constraints, non-goals, success. | People ask fewer basic scope questions. | [`../01-intent/intent.md`](../01-intent/intent.md) |
| PRD | Product behavior must be defined. | Requirements, acceptance criteria, priorities, risks. | Tests map clearly to requirements. | [`../03-product-spec/product-spec.md`](../03-product-spec/product-spec.md) |
| Technical spec | Implementation needs design. | Architecture, data, APIs, integrations, errors, security. | AI output respects boundaries. | [`../04-technical-spec/technical-spec.md`](../04-technical-spec/technical-spec.md) |
| Agent task brief | AI receives implementation work. | Task, context, constraints, files, tests, expected output. | Agent changes fewer unrelated files. | [`../../02-tasks/02-task-files/TASK-001.md`](../../02-tasks/02-task-files/TASK-001.md) |
| Test specification | Work is ready for implementation. | Unit, integration, end-to-end, failure, security, performance. | Bugs are caught before release. | [`../../03-tests/01-plan/test-specification.md`](../../03-tests/01-plan/test-specification.md) |
| Review checklist | Output is ready for acceptance. | Requirements, design, security, tests, maintainability. | Review is evidence-based. | [`../../05-review/02-checklists/code-review-checklist.md`](../../05-review/02-checklists/code-review-checklist.md) |
| Release checklist | Work is ready for production. | Config, migration, rollback, monitoring, owner. | Deployment is calmer and recoverable. | [`../../07-ops/01-deployment/deployment-checklist.md`](../../07-ops/01-deployment/deployment-checklist.md) |

> **Template library rule (Ch. 30 §30.4):** after every project, ask one question —
> **which template should be improved so the same confusion does not happen again?**

### Improvement log

| Date | Project / feature | Recurring problem | Template or rule improved | Change made |
|---|---|---|---|---|

Empty, because no project has completed. The first entry is owed the day TASK-001 is reviewed —
and the question to ask is the one above, not *what went wrong*.

---

## 4. Where each system component lives

| Ch. 30 component | This template |
|---|---|
| §30.1 Reusable process | This file, §1 |
| §30.2 Documentation organization | This file, §2 + the folder structure itself |
| §30.3 Versioning requirements and specs | [`../09-change-control/spec-change-log.md`](../09-change-control/spec-change-log.md) |
| §30.4 Template library | This file, §3 |
| §30.5 Agent rules and coding standards | [`../../06-agent/01-instructions/agent-rules-and-coding-standards.md`](../../06-agent/01-instructions/agent-rules-and-coding-standards.md) |
| §30.6 Connecting specs to tasks, tests, code | [`../08-traceability/traceability.md`](../08-traceability/traceability.md) |
| §30.7 Measuring engineering quality | [`../../07-ops/04-release/engineering-quality-review.md`](../../07-ops/04-release/engineering-quality-review.md) |
| §30.8 Individual use → team adoption | Root `README.md` |
| §30.9 The future | This file, §5 |
| §30.10 Final guidance | This file, §6 |

---

## 5. The future of spec-driven AI engineering (Ch. 30 §30.9)

> The more powerful the agent becomes, the **more important the specification becomes**.
> Strong teams will not be the teams that simply use the newest AI tool. They will be the
> teams that can express product intent clearly, convert it into reliable engineering
> artifacts, supervise AI-generated work, and keep production systems aligned with
> changing reality.

| Likely direction | What it means for you | Skill to build now |
|---|---|---|
| More autonomous agents | Agents will handle larger workflows with less manual prompting. | Write stronger boundaries, rules, and review gates. |
| Spec-aware development tools | Tools will read requirements, tests, and architecture together. | Keep artifacts structured and current. |
| Continuous production feedback | Monitoring and user feedback will update plans faster. | Treat production learning as part of the spec lifecycle. |
| Human review becomes higher level | Humans will spend more time judging intent, risk, and trade-offs. | Improve product thinking, systems thinking, and review discipline. |

---

## 6. Final guidance (Ch. 30 §30.10)

**Do not ask AI to replace engineering discipline. Use AI inside engineering discipline.**

1. Begin every project with **engineering intent** before asking for code.
2. Turn intent into requirements that can be **tested**.
3. Write technical specifications **before** implementation decisions become scattered.
4. Give AI agents **bounded tasks** with context, constraints, and expected outputs.
5. **Plan tests before generation** so the agent builds toward clear proof.
6. Review generated code against requirements, architecture, security, and maintainability.
7. Deploy with **rollback, monitoring, and maintenance** in mind.
8. Treat production feedback as part of the **specification lifecycle**.
9. Keep improving templates, rules, and checklists after each project.

> Start with small projects. Build your template library. Improve your agent rules. Keep
> requirements connected to tests. Review generated work with evidence. Update
> specifications after release. **When a mistake repeats, improve the system instead of
> only fixing the immediate bug.**

> **Final guidance (Ch. 30):** your advantage is not that you can ask an AI agent to write
> code. Your advantage is that you can guide AI with clear specifications, verify its
> output with tests, and build a repeatable system that keeps improving.

---

## 7. Repeatable system checklist (Ch. 30)

| Area | Question to ask | Ready? |
|---|---|---|
| Process | Can you explain the path from idea to production review? | **Yes** — §1, and where it currently stops |
| Documentation | Can a new human or AI agent find the current source of truth? | **Yes** — the source-of-truth order is in `AGENT.md` |
| Versioning | Are requirement and spec changes named, dated, and explained? | **Yes** — CHG-001 to CHG-005, all raised during the interview |
| Templates | Do projects reuse proven briefs, specs, test plans, and review checklists? | **Yes** — every file here came from a blueprint, named in its back-link |
| Agent rules | Do agents receive clear constraints, coding standards, and completion rules? | **Yes** — `AGENT.md`, plus a rule from each of ADR-001 to ADR-005 |
| Traceability | Can each feature be traced from requirement to task, test, code, review, and release? | **No** — traced to task and test; no code exists, and REQ-NF-006 has no design link at all |
| Quality metrics | Do you measure defects, rework, review findings, drift, and production stability? | **No** — nothing to measure until something ships |
| Adoption | Does the workflow help the team work with less confusion and better evidence? | **Not yet answerable** — one interview is not evidence of adoption |

**Three honest No's.** Two of them are unreachable rather than unmet: you cannot measure quality
or adoption before anything is built. The third is real — the traceability matrix has a
requirement with no design link, and that is a gap somebody has to close rather than wait out.

---

> Blueprint: blueprints/01-docs/10-reference/repeatable-system.md
