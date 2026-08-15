# Decision Log

> Source: Ch. 4 §4.4 — `decisions.md`: "Records important design trade-offs. Whenever you
> choose one option over another."

This is the **lightweight** log. Use it for everyday choices that shape the work but do
not warrant a full record. When a decision affects architecture, security, reliability, or
performance in a lasting way, promote it to an ADR in
[`architecture-decisions/`](architecture-decisions) and link it here.

---

| ID | Date | Decision | Options considered | Why this one | Affects | Promoted to ADR? |
|---|---|---|---|---|---|---|
| DD-001 | 2026-08-15 | Use a modular monolith. | Simple monolith; modular monolith; service-based; serverless. | It is the only option that gives FF-001 and FF-002 a boundary they can actually inspect, and the core subdomain has to be separable from the views that show it. | All | **ADR-001** |
| DD-002 | 2026-08-15 | Use an embedded relational database — one file, in-process. | Server-based relational; embedded relational; managed platform database; document store. | Keeps every check constraint and foreign key the schema depends on while removing a whole operational component from a one-week build. | `database-design.md`, §12 deployment | **ADR-002** |
| DD-003 | 2026-08-15 | Email and password with server-side sessions. | Email/password; corporate SSO or OAuth; third-party identity provider; magic link. | The only option with no dependency outside the build (CON-006), and the only one that still works when a storm is degrading email. | REQ-NF-002, REQ-R-001 | **ADR-003** |
| DD-004 | 2026-08-15 | Enforce append-only on `decision_records` with `BEFORE UPDATE` / `BEFORE DELETE` triggers instead of a role grant. | Application-layer check; database triggers; reverse ADR-002 for its role system. | ADR-002 removed the role system BR-004 relied on. A trigger keeps the rule in the store rather than moving it to the layer the rule exists to distrust. | BR-004, FF-004 | **ADR-004** |
| DD-005 | 2026-08-15 | Three release gates chosen: every rank shows its reasons; every screen survives losing its data; all seven known data defects are caught. | — (selected from the driving characteristics and constraints) | They are the three properties whose loss would be invisible in a passing test suite. | FF-003, FF-005, FF-006 | n/a |
| DD-006 | 2026-08-15 | Module set fixed at five: loader, store, scoring, API layer, views. | Fewer modules with scoring inside the API layer; more modules splitting the loader per input type. | Five is the smallest set in which the core subdomain is its own module, which is the only boundary FF-002 needs. | `technical-spec.md` §2 | n/a — follows ADR-001 |
| DD-007 | 2026-08-15 | Sessions are server-side and **never sticky**, even though only one instance runs. | Sticky sessions; server-side sessions; stateless tokens. | Sticky sessions mean not stateless, and it is the one choice that shuts a door statelessness keeps open for nothing in return today. | `runtime-and-scale.md` §3 | n/a — follows ADR-003 |
| DD-008 | 2026-08-15 | Version one scores with a deterministic weighted rule; deep learning is rejected for this scorer permanently; the decision-tree family is the successor when data exists. | Deterministic rule; trained decision-tree ensemble; deep learning on tabular data. | There is no per-asset failure history to train on (A7), and the boundary already fixes the swap cost at one module — so shipping a rule costs nothing in the direction of a model. Deep learning fails BR-002 on explainability. | REQ-F-002, REQ-F-003, BR-002 | **ADR-005** |

---

## Design decision format (Ch. 10 §10.3)

```
Design Decision ID: DD-###
Related requirement: REQ-###
Decision:
Reason:
Consequences:
```

The block below is DD-004, filled in. It is recorded in detail because it is the one decision in
this round that was **forced** rather than chosen — a consequence of DD-002 that reached one of
the three driving characteristics, and would have been a silent downgrade if nobody had followed
the chain.

```
Design Decision ID: DD-004
Related requirement: BR-004, REQ-F-009, REQ-R-002
Decision:
  Enforce the append-only rule on decision_records with BEFORE UPDATE and BEFORE DELETE
  triggers that abort the statement, replacing the role-grant mechanism specified in
  database-design.md §3.
Reason:
  DD-002 chose an embedded relational database, which has no role system. The original
  mechanism — an application role holding no UPDATE or DELETE grant — is unavailable.
  Auditability is one of the three driving characteristics, so accepting an application-layer
  check would have weakened a driver without anyone deciding to.
Consequences:
  - FF-004's check changes; its guarantee does not. It now asserts that both triggers exist
    AND that an UPDATE issued against decision_records is refused by the database.
  - One weakness remains and is not fixed by this decision: a migration can drop a trigger,
    and the role-grant version separated that power from ordinary development. The migration
    checklist must treat removing either trigger as requiring a superseding ADR.
  - The two separate database credentials specified in technical-spec.md §7.5 no longer apply
    — there are no roles to separate. That section changes with this decision (CHG-002).
  - The agent must never write an UPDATE or DELETE against decision_records, and must never
    drop or recreate either trigger inside an unrelated migration.
```

---

## When does a requirement need a design decision? (Ch. 10 §10.3)

Ask: **"Can this requirement be implemented in more than one way?"**
If yes, document the chosen direction *before* creating tasks — otherwise the agent
picks a convenient implementation that may not match your intended architecture.

---

## Promote to an ADR when the decision…

- changes the architecture style or module boundaries,
- affects security or data-protection posture,
- affects reliability, failure behavior, or recovery,
- affects performance or cost at scale,
- would be expensive or risky to reverse later,
- creates a rule the AI assistant must follow during every future implementation.

---

> Blueprint: blueprints/01-docs/05-architecture/decisions.md
