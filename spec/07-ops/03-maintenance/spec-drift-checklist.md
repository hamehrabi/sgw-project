# Maintenance and Spec Drift Checklist

> Source: Appendix Q + Ch. 24 §24.8–24.9.
> **Spec drift** happens when production behavior changes but the specification does not.
> It is dangerous because your next change, your next prompt, and your next AI-assisted
> task will be based on outdated truth.

---

## After every release (Appendix Q)

- [ ] Update requirements to reflect accepted changes.
- [ ] Update API, database, and technical specs if contracts changed.
- [ ] Update the traceability matrix with released test evidence.
- [ ] Record architecture decisions that changed the design direction.
- [ ] Add monitoring observations or known limits to the maintenance notes.

## Monthly maintenance review (Appendix Q)

- [ ] Compare top user feedback with current requirements.
- [ ] Review frequent errors and decide whether specs or code need updates.
- [ ] Review performance trends and capacity assumptions.
- [ ] Remove obsolete tasks and mark superseded decisions.
- [ ] **Refresh the project context pack before giving it to an AI agent.**

The last box carries more weight here than in most projects. An agent builds every task
(CON-008), and it reads `06-agent/02-context/context-pack.md` — so a context pack that still
describes the world before the last three changes is not a stale document, it is **wrong
instructions being followed literally**.

## Maintenance checklist (Ch. 24 §24.9)

| Maintenance check | Done? |
|---|---|
| Key workflows have monitoring requirements. | Yes — `monitoring-plan.md` |
| Errors are grouped and reviewed by severity. | Yes — in plan; no errors yet |
| Logs include request IDs and useful context. | Yes — specified |
| Performance targets exist for important workflows. | **No** — the targets exist as words; the numbers are unset (Q-012) |
| User feedback is mapped to requirements or decisions. | Yes — `feedback-register.md`, empty |
| Specs are updated after production behavior changes. | Not applicable yet |
| New or changed behavior has matching tests. | Yes — 47 ids, written before any code |
| AI agent instructions use the current spec, not outdated context. | Yes — today. This is the one that degrades fastest |
| Spec drift review is completed before major changes. | Not applicable yet |

---

## Drift signals (Ch. 24 §24.8)

| Drift signal | What it may mean | What you should do |
|---|---|---|
| Code behavior does not match acceptance criteria. | The code changed without a spec update, or the requirement was wrong. | Compare production behavior with the requirement and choose the correct source of truth. |
| Tests pass but users complain. | The tests may not cover the real user expectation. | Update acceptance criteria and add tests for the missing behavior. |
| AI agent suggests changes outside scope. | The context or task instruction may be too broad. | Narrow the task and restate the boundaries. |
| A bug fix creates new workflow behavior. | The fix changed product behavior, not just code. | Update the product spec, technical spec, and tests. |

### A fifth signal, specific to this project

| Drift signal | What it may mean | What you should do |
|---|---|---|
| **The scoring weights have changed and the ranking still looks reasonable.** | The rule was tuned toward what somebody expected to see. Q-025 makes weight changes the expected activity, and a rule tuned to look right is indistinguishable on screen from one that is right. | Re-run the full eval set (`ai-evals.md` §4 requires it on any weight change) and check `failure_recall_at_decile` against the *previous* run, not against intuition. Record the change; a weight edit is a product decision. |

**This is the drift this product is most exposed to**, and it is the only kind that improves the
appearance of the system while degrading it. Nothing breaks, no test fails, and the reasons on
screen update to match the new weights — confidently, and wrongly in the same way.

---

## Drift audit

| # | Behavior in production | What the spec says | Which is correct? | Action | Owner | Status |
|---|---|---|---|---|---|---|

**Empty — nothing is in production.** The first audit runs after the first release, and there is
already one row to expect: `scoring_rule_version` on every `RANKING_DELIVERED` event exists
precisely so that this table can be filled from evidence rather than from memory.

### The drift that has already happened, in the specification itself

Five decisions changed during the interview because later answers made earlier ones
unsatisfiable — CHG-001 to CHG-005. That is not drift; it is change control working. It is
recorded here because a reader encountering, say, the two-database-credentials design in an old
note would be reading a sentence that was corrected. **When a document and the change log
disagree, the change log is newer.**

---

## Maintenance areas to watch (Ch. 27 §27.10)

| Area | What to watch | Action | Spec update required? |
|---|---|---|---|
| Correctness | Impossible values, mismatch with source data. | Investigate ingestion and calculation rules. | Yes, if meaning changes. |
| Performance | Slow endpoints. | Review queries, indexes, cache rules, ranges. | Yes, if limits or targets change. |
| Error tracking | API failures, failed jobs, permission errors. | Classify cause and create fix tasks. | Yes, if new error states appear. |
| User feedback | Confusing UI, missing filters, new requests. | Convert repeated feedback into requirements. | Yes, when accepted into the roadmap. |
| **Spec drift** | Code behavior no longer matches requirements. | Update specs or refactor code to match approved behavior. | **Always.** |

The first row has a permanent home here: the seven measured data defects are *expected*, not
exceptional. A rise in `ASSET_MATCH_NEEDS_REVIEW` or `ASSET_SCORING_FAILED` between two loads of
the same storm means the input data changed shape — which is a correctness signal about the
world, not about the code.

---

## The production rule (Ch. 24 §24.1)

> Every meaningful production lesson should answer one question:
> **does the spec still describe the system you need to maintain?**

A code fix without a spec update solves today's bug and creates tomorrow's confusion.

**On this project it creates something worse than confusion.** An agent reads the specification
as its instructions. A fix that is not written back does not merely confuse the next reader — it
guarantees the next task is built against a description of a system that no longer exists.

---

> Blueprint: blueprints/07-ops/03-maintenance/spec-drift-checklist.md
