# Architecture Decision Records

> Source: Ch. 8 §8.8, Appendix K.
> An ADR is a short document explaining an important architecture decision: the context,
> the options considered, the decision made, and the consequences.

**Why ADRs matter with AI agents:** they become *durable instructions*. Instead of
explaining the same decision repeatedly in every prompt, include the ADR in the project
context and tell the assistant to follow it.

## Index

| ID | Title | Status | Date | Supersedes |
|---|---|---|---|---|
| [ADR-000](ADR-000-template.md) | Template — copy me | — | — | — |
| [ADR-001](ADR-001-modular-monolith.md) | Use a modular monolith | Accepted | 2026-08-15 | — |
| [ADR-002](ADR-002-embedded-relational-store.md) | Use an embedded relational database | Accepted | 2026-08-15 | — |
| [ADR-003](ADR-003-email-password-sessions.md) | Email and password with server-side sessions | Accepted | 2026-08-15 | — |
| [ADR-004](ADR-004-append-only-by-trigger.md) | Enforce the append-only decision record with database triggers | Accepted | 2026-08-15 | — |
| [ADR-005](ADR-005-deterministic-scoring-behind-a-model-boundary.md) | A deterministic scoring rule for version one, behind a model-shaped boundary | Accepted | 2026-08-15 | — |
| [ADR-006](ADR-006-session-lifetime.md) | Session lifetime of 240 minutes idle, 12 hours absolute | Accepted | 2026-08-15 | — |
| [ADR-007](ADR-007-scoring-factors-and-weights.md) | The scoring factors, their weights, and keeping criticality out of risk | Accepted | 2026-08-15 | — |
| [ADR-008](ADR-008-python-fastapi-backend.md) | A Python/FastAPI backend, with Next.js as a separate frontend | Accepted | 2026-08-15 | amends ADR-001, ADR-002 |
| [ADR-009](ADR-009-llm-phrases-computed-reasons.md) | A hosted language model phrases computed reasons, and may invent nothing | Accepted | 2026-08-15 | reverses CON-006 |

ADR-006 and ADR-007 fill numbers that ADR-003 and ADR-005 deliberately left open (Q-021, Q-025).
Neither supersedes its parent: an ADR that defers a value and an ADR that supplies it are two
decisions, and separating them keeps the reasoning for each readable on its own.

ADR-005 was written during Round 7 rather than Round 5, because the question surfaced when the
task plan showed TASK-003 blocked with nothing to unblock it (CHG-005). It rejects deep learning
for this scorer permanently, on explainability, and defers the decision-tree family until there
is data to train on.

ADR-004 exists because of ADR-002. Choosing an embedded store removed the role system that
BR-004's original enforcement relied on, and a consequence that reaches a driving characteristic
is a decision in its own right rather than a footnote on the one that caused it.

## Conventions

- File name: `ADR-###-short-kebab-title.md`
- Numbers are sequential and never reused.
- An accepted ADR is **immutable**. To change direction, write a new ADR and mark the old
  one `Superseded`.
- Every ADR lists at least one **rule the AI assistant must follow during implementation** —
  that rule belongs in `06-agent/AGENT.md` too.

The four rules imposed so far are stated in each ADR's *Consequences*, and Round 8 collects them
into `AGENT.md`. They are not restated here: an index that also carried the rules would be a
second copy of four sentences that must not be allowed to disagree.

## Status values

| Status | Meaning |
|---|---|
| Proposed | Written, not yet agreed. |
| Accepted | Agreed; binding on implementation. |
| Rejected | Considered and declined; kept for the record. |
| Replaced / Superseded | A later ADR governs instead. |

---

> Blueprint: blueprints/01-docs/05-architecture/architecture-decisions/adr-index.md
