# Engineering Quality Review

> Source: Ch. 30 §30.7.
> Measure the quality of the **engineering system**, not the amount of AI usage. AI can
> generate many files quickly, but speed alone does not prove quality.

---

## Metrics (Ch. 30 §30.7)

| Metric | What it shows | How to measure simply | Healthy direction |
|---|---|---|---|
| Requirement clarity | Whether specs are usable before coding. | Count questions raised during task handoff. | Fewer basic clarifying questions over time. |
| Rework rate | How often generated work must be heavily corrected. | Track tasks reopened after review. | Lower reopen rate. |
| Test usefulness | Whether tests catch real problems. | Track bugs found by tests before release. | More meaningful failures before production. |
| Review findings | Where AI or humans commonly miss issues. | Tag review comments by category. | Repeated categories decrease. |
| Spec drift | Whether code and specs stay aligned. | Check if released behavior is reflected in docs. | Fewer undocumented behavior changes. |
| Production stability | Whether releases behave reliably. | Track errors, incidents, rollback events, response time. | Fewer incidents, faster recovery. |

**A seventh metric belongs on this project and is not in the list**, because it measures the
product rather than the engineering system — and it is the one that decides whether any of the
rest matters:

| Metric | What it shows | How to measure | Healthy direction |
|---|---|---|---|
| **Reasons-read rate** | Whether operators are still thinking, or deferring to the ranking | Ratio of decisions taken to `ReasonPanel` opens | Stable or rising. **A fall means over-trust — assumption A3 failing in the dangerous direction** |

---

## Monthly review template (Ch. 30 §30.7)

```
Period reviewed:
Projects or features shipped:
Requirements that changed:
Tasks completed with AI support:
Defects found before release:
Defects found after release:
Most common review issue:
Most common AI mistake:
Template that needs improvement:
Agent rule that needs improvement:
Spec drift found:
Action items for next month:
```

---

## Tracking table

| Period | Clarifying questions | Tasks reopened | Bugs caught pre-release | Bugs found post-release | Incidents | Rollbacks | Drift items |
|---|---|---|---|---|---|---|---|

**Empty, and it should stay empty until something is built.** Filling a metrics table before any
work has happened is exactly the "many files quickly" this file exists to argue against.

**The specification phase does have one number worth carrying forward**, recorded here rather
than in the table because it is not a period: **26 open questions were raised and 14 were
answered during the interview.** The twelve that remain are not a failure of the process — they
are the process working, and each is named with an owner instead of having been guessed. The
number to watch is not how many were raised; it is how many are still open when TASK-001 ships.

---

## Review-finding categories

Tag each review comment so patterns become visible.

| Category | Example |
|---|---|
| `requirement-gap` | Behavior implemented that no requirement asked for. |
| `architecture-drift` | Business logic placed in a route handler. |
| `missing-validation` | Input accepted without a boundary check. |
| `security` | Missing authorization check on a protected action. |
| `shallow-test` | Test asserts that something happened, not that it was correct. |
| `scope-creep` | Files changed outside the task boundary. |
| `unsafe-error` | Internal detail exposed in a user-facing message. |

Two more this project should expect to tag, because both are predicted in `AGENT.md`:

| Category | Example |
|---|---|
| `store-rule-moved` | A constraint the database could enforce, implemented in a service instead. |
| `absence-as-reassurance` | An empty or incomplete result rendered as though nothing were wrong. |

---

## Improvement loop (Ch. 30 §30.4)

After every project, answer one question:

> **Which template should be improved so the same confusion does not happen again?**

| Recurring problem | Template / rule to improve | Change made | Date |
|---|---|---|---|

Empty. The first row is owed after the first review, and the question above is the one to ask —
not *what went wrong*, which produces a fix for one bug rather than a change to the system that
produced it.

---

## Repeatable system checklist (Ch. 30)

| Area | Question | Ready? |
|---|---|---|
| Process | Can you explain the path from idea to production review? | **Yes** — and where it currently stops: Q-017 blocks TASK-002 |
| Documentation | Can a new human or AI agent find the current source of truth? | **Yes** — precedence order in `AGENT.md`; when a document and the change log disagree, the change log is newer |
| Versioning | Are requirement and spec changes named, dated, and explained? | **Yes** — CHG-001 to CHG-005, all raised during the interview |
| Templates | Do projects reuse proven briefs, specs, test plans, review checklists? | **Yes** — every file names its blueprint in a back-link |
| Agent rules | Do agents receive clear constraints, coding standards, completion rules? | **Yes** — `AGENT.md`, plus one rule from each of ADR-001 to ADR-005 |
| Traceability | Can each feature be traced requirement → task → test → code → review → release? | **No** — traced to task and test; no code exists, and REQ-NF-006 has no design link at all |
| Quality metrics | Do you measure defects, rework, review findings, drift, stability? | **No** — nothing to measure until something ships |
| Adoption | Does the workflow help the team work with less confusion and better evidence? | **Not yet answerable** — one interview is not evidence of adoption |

**Three honest No's, and only one is a real gap.** Quality metrics and adoption cannot be
answered before anything is built. Traceability can be improved today: a requirement with no
design link is a requirement nobody has decided how to satisfy, and it will not fix itself.

---

> Blueprint: blueprints/07-ops/04-release/engineering-quality-review.md
