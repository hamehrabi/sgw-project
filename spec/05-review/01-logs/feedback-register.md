# Feedback Register

> Source: Ch. 29 §29.5 + Ch. 24 §24.6.
> Feedback becomes useful when it is **specific, traceable, and assigned**. "Make this
> better" gives the team and the agent nothing to act on.

Good feedback identifies the affected requirement, explains the gap, proposes a decision,
and states who owns the next action.

---

## Register

| ID | Date | Source | Type | Summary | Affected artifact | Owner | Status | Spec update? | Test update? |
|---|---|---|---|---|---|---|---|---|---|

**Status:** New · Under review · Accepted · Rejected · Deferred
**Types:** Clarification · Bug · Design concern · Scope request · Operational concern · Performance

**Empty, because nothing has been shipped to anyone.** The first entries will come from the
scenario tests in Phase 1 — real operators using the ranking — and that is exactly where the two
guesses this product exists to test get answered.

---

## Entry template (Ch. 29 §29.5)

```
Feedback ID:
Date:
Source:                     [user / support / stakeholder / monitoring / QA]
Affected requirement or artifact:
Feedback summary:
Evidence or example:
Decision needed:
Owner:
Status:                     New / Under review / Accepted / Rejected / Deferred
Spec update required:       Yes / No
Test update required:       Yes / No
Next action:
```

---

## Feedback → action mapping (Ch. 29 §29.5)

| Type | Example | Where to record it | Owner | Next action |
|---|---|---|---|---|
| Clarification | "The task status labels are unclear." | Feedback register + product spec. | Product manager. | Define label meanings; update acceptance criteria. |
| Bug | "A viewer can access an edit-only screen." | Issue list, test plan, security checklist. | Developer. | Fix permission logic; add regression test. |
| Design concern | "The AI answer appears too confident." | AI behavior spec and prompt rules. | Product + developer. | Add unsupported-answer rule and test. |
| Scope request | "Stakeholders want team notifications." | Scope change log. | Product manager. | Decide now, later, or reject. |
| Operational concern | "Errors are hard to diagnose in production." | Reliability spec and monitoring plan. | Engineering. | Add structured logs and error tracking. |

---

## Turning user feedback into engineering input (Ch. 24 §24.6)

Monitoring tells you what the system **is doing**. Feedback tells you how the system
**feels** and where it fails real expectations. You need both — a system can have no
errors and still be confusing.

| Feedback type | Example | Spec action |
|---|---|---|
| Confusion | "I do not know which button saves my changes." | Update user flow and UI requirement. |
| Missing behavior | "I need to export only completed tasks." | Add or **explicitly reject** a new requirement. |
| Wrong expectation | "I expected project members to see shared reports." | Clarify role permissions and access rules. |
| Performance complaint | "The dashboard is slow every morning." | Add a performance requirement and monitoring signal. |

> Treat feedback as **engineering input, not casual opinion**. Map every report to a
> requirement, user flow, design decision, or missing acceptance criterion.

---

## The feedback this product is actually built to collect

Version one is a probe. Most feedback registers exist to catch what a shipped product got wrong;
this one exists to answer two questions the whole project rests on, and the answers will arrive
as ordinary-sounding remarks rather than as bug reports.

| What somebody says | What it is really evidence of | Where it goes |
|---|---|---|
| *"I'd have sent them there anyway."* | **Assumption A2 failing.** The combined ranked view did not change the crew decision. Not a complaint, not a defect, and the most important sentence anyone can say about this product. | Success metric 1, and a decision about whether to scale or redesign |
| *"I just take the top of the list."* | **Assumption A3 failing in the dangerous direction** — over-trust, the source PRD's danger (c). Acting on the ranking without reading why is what BR-002 exists to prevent, and success metric 3 counts it. | Success metric 3 |
| *"I didn't bother opening the reasons."* | The same thing, said honestly. | Success metric 3 |
| *"It said nothing was at risk."* | Possibly a **ranking that could not be computed**, rendering as safety. Treat as a Bug and check FTEST-004 before treating it as a Clarification. | Issue list, `failure-tests.md` |
| *"The condition data is nonsense."* | Not a defect — the seven known data problems working as specified. Whether the **display** of source and age is doing its job is a Clarification. | Product spec, BR-003 |

**The first two rows are why this register matters more than usual here.** A team watching for
bugs will record neither, because neither is a bug. Both are the product failing at the only
thing it was built to find out.

---

> Blueprint: blueprints/05-review/01-logs/feedback-register.md
