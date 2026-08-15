# subdomain-map.md — Core / Generic / Supporting

> **Purpose:** decide where effort goes before you decide anything else.
> **When you use it:** right after `intent.md`, before requirements.
> **Source:** Khononov, *Learning Domain-Driven Design*, Ch. 1.

One table. It redirects budget, hiring, build-vs-buy, spec depth, and test rigour.
Skip it and you will over-engineer the login screen and under-model the thing you
actually compete on.

| Type | Recognise it by | What to do |
|---|---|---|
| **Core** | Differentiating, complex, **changes constantly** | Build in-house. Best people. Richest modelling. **Never duplicate it.** |
| **Generic** | Everyone needs it, nobody wins with it (auth, payments, email) | **Buy or adopt.** Building it is waste. |
| **Supporting** | Necessary, simple, rarely changes (CRUD, admin screens) | Build simply, or outsource. Cheapest pattern that works. |

---

## The map

| Area of the system | Type | Why | Build / Buy | Spec depth | Test depth |
|---|---|---|---|---|---|
| Ranked risk list with plain-words reasons | **Core** | Named in Round 2 as the one capability this product competes on. The score and the reason beside it are one thing — a rank nobody can explain fails the trust guess (A3), and a rank that changes no decision fails the value guess (A2). Both of the project's fatal risks live here. | Build | Full | Full |
| Joined asset view — one record per asset, each value carrying its source and its age | **Supporting** | Necessary, and nothing else works without it, but it is not differentiating: every utility integration does this, and on prepared data files the hard part (matching records that use different codes for the same asset) is already resolved. It becomes complex only when CON-005 is lifted and the live systems are connected. | Build simply | Light | Acceptance only |
| Planning view for the operations manager | **Supporting** | A screen over the ranked list. What is judged here is the ranking underneath it, not the view. | Build simply | Light | Acceptance only |
| Dispatch board for the dispatcher | **Supporting** | A live shared list of damage and repair jobs. Necessary and stable in shape; the differentiation is in what fills it. | Build simply | Light | Acceptance only |
| Authentication, sessions, and role separation | **Generic** | Every application needs it and none wins with it. The source PRD (§8) requires sign-in with a second factor and a per-role view, so it is real work — but it is work to keep cheap. CON-006 blocks buying an identity provider in version one, which is a reason to build it thin, not a reason to model it richly. | Build thin, in version one. Two roles only — admin and user (REQ-R-001) — because CON-006 blocks buying an identity provider and two roles is the smallest thing that separates loading a scenario from acting on one. Flagged to buy if this ever leaves the probe stage. | Light | Acceptance only |

**Test:** *could this be sold on its own? would someone pay for it?* → then it is **core**.

**Useful heuristic:** look for the worst-designed component — the one everyone hates and
the business refuses to rewrite because of the risk. That is very often a core subdomain.

---

## What each type changes downstream

| | Core | Generic | Supporting |
|---|---|---|---|
| Spec | Full chain, ADRs, deep modelling | Integration contract only | One page |
| Pattern | Domain model (rich objects, invariants) | Adapter around the bought thing | Transaction script / CRUD |
| Tests | Pyramid — mostly unit | Contract + failure tests | Reversed — mostly end-to-end |
| Review | Every change | Integration points only | Sampled |
| Who builds it | Your strongest people | Anyone | Training ground |

> **Never use "separate ways" for a core subdomain** — duplicating it defeats the whole
> strategy. Generic and supporting can be duplicated cheaply if it removes friction.

---

> Blueprint source: this file is new to the template — added from the architecture review.

---

> Blueprint: blueprints/01-docs/01-intent/subdomain-map.md
