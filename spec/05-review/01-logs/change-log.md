# Change Log

> Source: Ch. 4 §4.8–4.9 (Step 7) — "Use `change-log.md` to record important changes and
> decisions."
>
> This works **even if you do not use Git**. The core idea: every important change should
> leave a record. When a requirement changes, record it. When an agent completes a task,
> record it. When you accept or reject a change, record why.

---

## Entries

| Date | Type | Change | Requirement / Task | Reason | Decision | Recorded by |
|---|---|---|---|---|---|---|
| 2026-08-15 | Intent | Specification workspace created from the spec-driven devkit; eight rounds completed. | — | Project start | Accepted | Developer |
| 2026-08-15 | Spec | ADR-001 modular monolith · ADR-002 embedded relational store · ADR-003 email-and-password sessions · ADR-004 append-only by trigger · ADR-005 deterministic scoring behind a model boundary. | — | Round 5, plus ADR-005 during Round 7 | Accepted | Developer |
| 2026-08-15 | Spec | CHG-001 to CHG-005 — five accepted decisions changed during the interview because later answers made earlier ones unsatisfiable. | REQ-F-010, BR-004, REQ-NF-002, REQ-F-002 | Recorded in `01-docs/09-change-control/spec-change-log.md` | Accepted | Developer |
| 2026-08-15 | Task | 10 tasks, 15 agent work items, dependency map. | TASK-001…010 | Round 7 | Accepted | Developer |
| 2026-08-15 | Test | 47 test ids across 8 levels, written from acceptance criteria before any code exists. | All | Round 7 | Accepted | Developer |

**Types:** Intent · Spec · Task · Test · Code · Review · Release · Fix · Scope

No **Code**, **Review**, **Release** or **Fix** entry exists, because nothing has been built.
Those four are what this log is really for; the five rows above are the record of getting to the
point where they can begin.

---

## Entry template

```
Date:
Type:
What changed:
Why it changed:
Requirement / Task:
Files or documents affected:
Accepted / Rejected — and why:
Follow-up needed:
```

---

## What is worth recording (Ch. 4 §4.8)

| Change type | Example entry |
|---|---|
| New intent document | Add engineering intent for the task manager project. |
| Updated requirements | Refine task creation requirements and acceptance criteria. |
| New task file | Add TASK-001 for task creation API. |
| Test plan added | Add acceptance and failure tests for task creation. |
| Implementation completed | Implement TASK-001 task creation workflow. |
| Review notes added | Record review results for TASK-001. |
| Change rejected | Reject auto-assign suggestion — outside approved scope. |

**The last row is the one people stop writing first, and the one worth most later.** A log that
records only what was accepted cannot answer *why doesn't it do X?* six months on. Four
rejections are already predictable on this project, and each will look like a helpful
improvement when it is proposed: a threshold that marks assets "high risk", an edit path on the
decision record "for corrections", auto-assignment of crews to top-ranked jobs, and an email of
any kind. Each is refused by a decision already recorded; when one is proposed and declined,
**record the rejection here** rather than relying on the refusal being findable.

---

## Related logs

| Log | Purpose |
|---|---|
| [`review-log.md`](review-log.md) | Review findings and accept/reject decisions. |
| [`feedback-register.md`](feedback-register.md) | Feedback from users and stakeholders. |
| [`../docs/spec-change-log.md`](../../01-docs/09-change-control/spec-change-log.md) | Versioned specification changes. |
| [`../tasks/scope-change-log.md`](../../02-tasks/03-control/scope-change-log.md) | Scope additions/removals and their decision trail. |
| [`../ops/release-notes.md`](../../07-ops/04-release/release-notes.md) | What shipped, when. |

**Five logs is a lot, and the split is deliberate rather than bureaucratic.** This one is the
running narrative — what happened, in order. The other four each answer one specific question:
*was this output accepted* (review), *what did a user tell us* (feedback), *what version is the
spec at and why* (spec change), *did the scope grow* (scope change). When in doubt, record it
here and cross-reference; a fact in the wrong log is recoverable, a fact in no log is not.

---

> Blueprint: blueprints/05-review/01-logs/change-log.md
