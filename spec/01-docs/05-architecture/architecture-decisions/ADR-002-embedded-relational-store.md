# ADR-002: Use an embedded relational database

**ADR ID:** ADR-002
**Status:** Accepted
**Date:** 2026-08-15
**Decision owner:** Tech lead (not yet named)
**Review date:** Before any deployment that serves more than one concurrent writer

---

## Context

The schema in `database-design.md` rests on three things a store either enforces or does not:
check constraints (BR-002's *a rank cannot be stored without reasons*, BR-003's *a condition
cannot be stored without its age*), foreign keys scoped by `scenario_id`, and an append-only
guarantee on `decision_records` (BR-004).

Around that: about one week to build (CON-002), under 50 users, no paid services (CON-006), one
organisation with no tenant isolation, and a deployment target still undecided until Round 8.

## Options considered

1. **Server-based relational database** — enforces all three guarantees, including
   append-only through a per-role grant. Costs a second process to install, configure, back
   up and connect to, before a single screen exists, and it presumes a deployment target that
   Round 8 has not chosen.
2. **Embedded relational database** — the same constraint vocabulary, running inside the
   application process, with the whole database as one file. No server, no connection string,
   no credential rotation. Costs a role system it does not have, and single-writer
   concurrency.
3. **Document store** — right where the shape of a record genuinely varies. Here it does not:
   the seven entities are fixed and heavily related, and the rules worth protecting are
   precisely the ones a document store leaves to the application.

*Compared on:* which interface is simpler · which is more general · which forces callers
to do work that should be inside · which is cheaper to reverse.

## Decision

Use an **embedded relational database** — one file, in-process, with the full schema, check
constraints, and foreign keys from `database-design.md` §3.

## Reason

It keeps every constraint the design depends on while removing an entire operational component
from a one-week build. At under 50 users with a single instance and no tenant isolation, the
capabilities a server-based store adds — concurrent writers, network access, role separation —
are either unneeded or replaceable, and the one that is genuinely needed (append-only) has a
direct substitute (ADR-004).

Reversal is cheap in the direction that matters: the schema is ordinary relational SQL, so
moving to a server-based store later is a migration, not a redesign. A document store would
have made that a redesign.

## Consequences

- **Positive:** No second process to run, secure, or back up — a backup is a file copy, which
  is what makes Round 8's recovery story simple. Check constraints and foreign keys work
  exactly as specified. The whole store is one artifact, which suits a probe that is meant to
  be handed to someone and run.
- **Trade-off or limitation:** **No role system.** BR-004's original enforcement — an
  application role holding no `UPDATE` on `decision_records` — is not available, and that is a
  real loss on one of the three driving characteristics. ADR-004 replaces it rather than
  accepting it. Second limitation: one writer at a time. At 50 users with a background parse
  job this is invisible, but it is the thing that stops being true first.
- **Rule the AI assistant must follow during implementation:** Every constraint in
  `database-design.md` §3 is written into the schema, not into application code. Never
  implement a check in the service layer that the store could refuse. The database file is
  never committed to version control.

> **If no trade-off is visible, keep looking.** A choice with no downside was never a
> choice — you are comparing in the abstract instead of weighted for this context.

## Compliance

| Enforced by | Where |
|---|---|
| FF-004 (via ADR-004), manual review by the tech lead on the schema | [`../../04-technical-spec/fitness-functions.md`](../../04-technical-spec/fitness-functions.md) |

## Revisit when

Any of: concurrent writers become normal rather than incidental; the first live source-system
connection makes the write path continuous rather than upload-driven; or the platform must run
as more than one instance. Any one of those makes single-writer the binding limit, and each is
observable rather than a matter of judgement.

## Impact

| Dimension | Impact |
|---|---|
| Security | Mixed. No network-reachable database and no credential to rotate — but no role separation either, which is why ADR-004 exists. |
| Reliability | Positive. One fewer process that can be down. A corrupt database file is a single, obvious failure rather than a partial one. |
| Performance | Positive at this size — no network hop on any read. Negative the moment writes are concurrent. |
| Cost | Positive. Nothing to pay for, which is CON-006 satisfied by construction. |
| Maintainability | Positive for one team; the migration path to a server-based store is ordinary SQL. |

## Related

- Related requirements: BR-002, BR-003, BR-004, REQ-F-009
- Related technical spec sections: §5 Database Requirements, §12 Deployment Approach
- Supersedes / superseded by: — (forces ADR-004)

---

> Blueprint: blueprints/01-docs/05-architecture/architecture-decisions/ADR-000-template.md
