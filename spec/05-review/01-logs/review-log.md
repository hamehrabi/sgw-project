# Review Log

> Source: Ch. 4 §4.3 — `/review` folder: "Stores review notes and decision records."
> A running record of what was **accepted, rejected, or changed**, and why.

---

| Date | Item reviewed | Task / Req | Reviewer | Layers checked | Findings | Decision | Follow-up |
|---|---|---|---|---|---|---|---|

**Decision values:** Accept · Accept with follow-up · Revise · Reject · Block

**No review has happened**, because nothing has been built. The first entry is owed when
TASK-001's output arrives.

This table is not the same as `01-docs/09-change-control/spec-change-log.md`, and the difference
is worth stating before the first entry blurs it. That log records **decisions about the
specification** — five were made during the interview itself. This one records **judgements
about output**: what an agent produced, and whether it was accepted. A specification change that
arrives *because* of a review gets a row in both, and the review row is the one that says why.

---

## Entry template

```
Date:
Item reviewed:        [task output, PR, generated tests, spec draft]
Requirement / Task:   REQ-### / TASK-###
Reviewer:

Layers checked:
[ ] Requirement fit   [ ] Architecture fit   [ ] Security & validation
[ ] Performance       [ ] Test evidence      [ ] Change scope
[ ] Maintainability

Findings:
1. [severity] [layer] — [finding] → [action]

Accepted because / Rejected because:

Decision:             Accept / Accept with follow-up / Revise / Reject / Block
Follow-up tasks:      TASK-###
Spec updates needed:  Yes / No → CHG-###
```

---

## Team review layers (Ch. 29 §29.4)

| Review layer | Main question | Evidence needed | Who helps | Decision |
|---|---|---|---|---|
| Requirement fit | Does this solve the user need? | Requirement ID and acceptance criteria. | Product manager, developer. | Accept / revise. |
| Architecture fit | Does this follow the agreed design? | Technical spec, ADRs, module boundaries. | Developer, architect. | Accept / refactor. |
| Security and privacy | Does this expose data or weaken controls? | Security checklist, permission tests. | Developer, reviewer. | **Block if unsafe.** |
| Test evidence | Do tests prove expected behavior and failure paths? | Unit, integration, UI, edge-case tests. | Developer, QA. | Accept / add tests. |
| Maintainability | Can the next developer understand this? | Clear naming, useful comments, updated specs. | Team reviewer. | Accept / simplify. |

> Review should not ask only "does this look good?" It asks whether the output satisfies
> requirements, respects architecture, passes tests, protects users, and keeps future
> maintenance clear.

**Two of these five have a standing *block* condition on this project**, decided in advance so
the judgement is not made under pressure at review time:

| Condition | Layer | Why it blocks rather than revises |
|---|---|---|
| An asset that could not be scored is absent from a ranking, or carries a default score | Security and privacy | The screen reads as safety, and the consequence is a crew not sent. It is a safety failure wearing a formatting bug's clothes. |
| A rule enforced in the service layer that the store could refuse | Architecture fit | It works, it passes, and the first refactor silently removes it. BR-002, BR-003 and BR-004 are enforced by the store on purpose. |

---

## What to expect from the first reviews

Written before the first review rather than after, so it can be checked against what actually
happens. `AGENT.md` predicts three failures on this project. If the first three reviews find
none of them, that is worth noticing as much as if they find all three.

| Predicted finding | Layer it appears in | Test that should have caught it |
|---|---|---|
| An unscorable asset dropped from the ranking | Requirement fit | FTEST-004 |
| A permission's allow path built, deny path absent | Security | The deny test for that row in `security-tests.md` |
| A store constraint implemented in a service instead | Architecture fit | UTEST-009 asserts the **store** refuses, not the caller |

---

> Blueprint: blueprints/05-review/01-logs/review-log.md
