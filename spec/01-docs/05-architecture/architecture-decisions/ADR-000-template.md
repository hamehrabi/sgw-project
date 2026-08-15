# ADR-000: [Decision Title]

> Source: Ch. 8 §8.8 + Appendix K.
> Copy this file to `ADR-001-short-title.md` and fill it in. Never edit an accepted ADR —
> supersede it with a new one.

**ADR ID:** ADR-000
**Status:** Proposed | Accepted | Rejected | Replaced | Superseded
**Date:**
**Decision owner:**
**Review date:**

---

## Context

*Explain the problem, project constraints, and why a decision is needed. A future reviewer
must be able to judge the decision knowing what you knew.*

## Options considered

> **Design it twice** (Ousterhout Ch. 11). You must compare **at least two genuinely
> different** options — not one option and two strawmen. Make them radically different;
> that is where the learning is. The winner is often a third design you only found by
> seeing what was wrong with the first two.

1. **[Option A]** — benefit / cost
2. **[Option B]** — benefit / cost
3. **[Option C]** — benefit / cost

*Compared on:* which interface is simpler · which is more general · which forces callers
to do work that should be inside · which is cheaper to reverse.

## Decision

*State the selected option clearly.*

## Reason

*Explain why this option fits the current project.*

## Consequences

- **Positive:**
- **Trade-off or limitation:**
- **Rule the AI assistant must follow during implementation:**

> **If no trade-off is visible, keep looking.** A choice with no downside was never a
> choice — you are comparing in the abstract instead of weighted for this context.

## Compliance

*How is this decision enforced? Name the fitness function, or say "manual review" and
say who does it. A decision with no compliance mechanism decays from the day it is written.*

| Enforced by | Where |
|---|---|
| FF-### / manual review by [role] | [`../../04-technical-spec/fitness-functions.md`](../../04-technical-spec/fitness-functions.md) |

## Revisit when

*What observable change would make this decision wrong? This is how you avoid
re-litigating it from scratch later.*

## Impact

| Dimension | Impact |
|---|---|
| Security | |
| Reliability | |
| Performance | |
| Cost | |
| Maintainability | |

## Related

- Related requirements: REQ-###
- Related technical spec sections:
- Supersedes / superseded by:

---

## Why each field matters (Appendix K)

| Field | Why it matters |
|---|---|
| Context | Prevents future reviewers from judging the decision without knowing the problem. |
| Decision | States the actual choice clearly. |
| Alternatives | Shows that the team considered other options. |
| Consequences | Makes trade-offs visible. |
| Related requirements | Keeps architecture tied to product value. |

---

> Blueprint: blueprints/01-docs/05-architecture/architecture-decisions/ADR-000-template.md
