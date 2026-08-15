# driving-characteristics.md — Pick Three

> **Purpose:** choose the small set of quality attributes that will shape the structure.
> **When you use it:** after requirements, before the technical spec.
> **Source:** Richards & Ford, *Fundamentals of Software Architecture*, Ch. 4–6.

> **Pick three. More than three and you have prioritised nothing.**
> Every characteristic you support adds effort, complexity, and interaction effects.

---

## Step 1 — Translate business concerns into candidates

| Business concern (their words) | Candidate characteristics |
|---|---|
| Time to market | Agility, testability, deployability |
| User satisfaction | Performance, availability, fault tolerance |
| Competitive advantage | Agility, scalability, availability |
| Mergers / acquisitions | Interoperability, extensibility, adaptability |
| Tight time / budget | **Simplicity, feasibility** |

A concern is an **architecture characteristic** only if all three hold:
it is **non-domain**, it **influences structure**, and it is **critical to success**.

Decompose composites: *agility* = deployability + modularity + testability.

## Step 2 — Candidates considered

Keep roughly seven. Preserve the rejected ones — that list is why the decision was sound.

| Candidate | Kept? | Reason |
|---|---|---|
| Simplicity / feasibility | ✅ | About one week to build version one (CON-002). Feasibility is the binding constraint here, not a preference. |
| Reliability / graceful failure | ✅ | The platform is used during the event it describes. REQ-NF-003 already fixes the behaviour: the last good picture, marked stale, with the failing file named. |
| Auditability | ✅ | The decision record exists to be produced to a regulator (REQ-F-009, BR-004). *"Why is it like this?"* is the question this product is bought to answer. |
| Performance | ❌ | Offered in Round 4 and not chosen. Latency remains a **requirement** (REQ-NF-001) with a real limit still to set (Q-012) — governed as a requirement rather than allowed to shape the structure. |
| Security and access control | ❌ | Already a constraint and a set of denials — CON-007, REQ-R-002, REQ-R-003, BR-004, BR-005. A driver slot spent here would buy nothing that is not enforced already, and the slot is better spent on something that could degrade silently. |
| Scalability | ❌ | Under 50 users in the first six months. Scaling and caching work is left out deliberately. **Revisit trigger:** 1,000 users, or the first live connection to a source system. |
| Accessibility | ❌ | Not rejected on merit — undecided. Q-013 is open, and a control room under storm conditions is exactly where contrast, keyboard reach and text size stop being optional. If Q-013 answers yes, it **displaces** one of the three rather than joining them. |

## Step 3 — The three drivers (unordered)

| # | Characteristic | Precise definition | Observable measure | Fitness function |
|---|---|---|---|---|
| 1 | **Simplicity / feasibility** | One person or agent can add a capability end to end inside a day, and the scoring logic can change without touching either view. | Zero import cycles between the scoring module, the API layer and the data layer; zero direct imports of scoring from a view. | FF-001, FF-002 → [`../04-technical-spec/fitness-functions.md`](../04-technical-spec/fitness-functions.md) |
| 2 | **Reliability / graceful failure** | Every screen keeps working when the prepared data behind it is missing, malformed or stale — showing the last good picture, marked stale and dated, and naming the file that failed. | Remove or corrupt each prepared file in turn: zero empty screens, zero error pages, and every stale render states its age. | FF-003 |
| 3 | **Auditability** | Every recommendation shown and every human decision taken can be reconstructed afterwards, and nothing in that record can be altered by anyone, including an admin. | Zero `UPDATE`/`DELETE` grants on `decision_records` for the application role; zero delivered rankings without a matching recommendation row. | FF-004, FF-005 |

> If you cannot state a **measure**, the definition is too vague. Rewrite it before
> moving to the technical spec.

## Step 4 — Explicitly NOT driving

| Characteristic | Why it is not a driver here |
|---|---|
| Performance | Offered and not chosen. It stays a requirement with a number (REQ-NF-001, Q-012) — a thing to pass, not a thing to shape the architecture around. |
| Security and access control | Already enforced as constraints and denials. Spending a driver slot on a quality that is already a hard boundary buys nothing. |
| Scalability | Under 50 users. Revisit at 1,000 users or at the first live source-system connection — that is an ADR trigger, not a version-one driver. |
| Accessibility | Undecided rather than rejected. Q-013 is open; answering it yes displaces one of the three above. |

---

> Blueprint source: this file is new to the template — added from the architecture review.

---

> Blueprint: blueprints/01-docs/02-requirements/driving-characteristics.md
