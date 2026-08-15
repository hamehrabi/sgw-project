# ADR-001: Use a modular monolith

**ADR ID:** ADR-001
**Status:** Accepted
**Date:** 2026-08-15
**Decision owner:** Tech lead (not yet named)
**Review date:** At the first live source-system connection

---

## Context

Version one is four capabilities built in about a week (CON-002) for under 50 users inside one
organisation, on uploaded files rather than live connections (CON-005). The three driving
characteristics are simplicity and feasibility, reliability and graceful failure, and
auditability; scalability was explicitly rejected with a revisit trigger.

The structural question is not how to scale but how to keep one thing separable: the scoring
module is the core subdomain, and REQ-NF-005 requires it to change without the planning view or
the dispatch board changing with it. Two of the five fitness functions — FF-001 and FF-002 —
exist to check exactly that, and both need a boundary that a tool can see.

## Options considered

1. **Simple monolith** — fastest to write inside a one-week horizon, and honest about a
   single author. The cost is decisive here: the boundaries live in someone's head rather
   than in the folder layout, so FF-001 and FF-002 have nothing to inspect and two of the
   five guards become documentation.
2. **Modular monolith** — one deployment, named modules, an import rule between them. Costs
   the discipline of respecting boundaries nobody is forced to respect at runtime.
3. **Service-based** — real independence, bought with a network between every call, a
   deployment story per service, and debugging across process boundaries. At 50 users and
   one week the cost is paid immediately and the benefit arrives never.

*Compared on:* which interface is simpler · which is more general · which forces callers
to do work that should be inside · which is cheaper to reverse.

## Decision

Use a **modular monolith**: one deployable process, with named modules for the loader, the
store, the scoring module, the API layer, and the views, and a one-directional import rule
between them.

## Reason

It is the only option on the list that makes the boundary this product actually cares about —
scoring separate from everything that displays scoring — into something checkable rather than
intended. A simple monolith would have been faster to start and would have disarmed FF-001 and
FF-002 on day one; services would have bought independence nobody needs at this size and
charged for it every day.

It is also the cheapest to reverse. A module can be lifted into a service later; logic that grew
across a single undifferentiated codebase cannot be lifted anywhere.

## Consequences

- **Positive:** FF-001 and FF-002 have real boundaries to check. The scoring module can be
  rewritten — and it will be, since it is the core subdomain — without touching either view.
  One process to deploy, one to run, one to debug.
- **Trade-off or limitation:** Nothing at runtime enforces the module boundary. It holds
  because a fitness function fails the build, and until that gate is wired (Round 7) it holds
  only because people are careful. That is a real gap, not a theoretical one.
- **Rule the AI assistant must follow during implementation:** Every piece of logic lives
  inside a named module. A view never imports the scoring module. A route handler never
  contains a scoring rule or a matching rule. Business logic never appears inside a UI
  component.

> **If no trade-off is visible, keep looking.** A choice with no downside was never a
> choice — you are comparing in the abstract instead of weighted for this context.

## Compliance

| Enforced by | Where |
|---|---|
| FF-001, FF-002 | [`../../04-technical-spec/fitness-functions.md`](../../04-technical-spec/fitness-functions.md) |

Both are currently marked `Not wired yet`. Until a pipeline exists, compliance is manual review
by the tech lead — and this ADR says so rather than implying a gate that is not running.

## Revisit when

The first live source-system connection is made, **or** a second team starts working on the
platform independently. Either is the change that makes one deployment a bottleneck rather than
a simplification. User count alone is not a trigger: 50 users and 500 users need the same shape.

## Impact

| Dimension | Impact |
|---|---|
| Security | Neutral. One process means one attack surface rather than several, and no internal network to secure. |
| Reliability | Positive. A failure is in one place, and there is no partial-availability state where three modules are up and one is not. |
| Performance | Positive at this size. Every call between modules is a function call rather than a network hop. |
| Cost | Positive. One instance, no service mesh, no inter-service infrastructure. |
| Maintainability | The point of the decision. Boundaries exist and are checkable; the core subdomain is separable from what displays it. |

## Related

- Related requirements: REQ-NF-005, and every requirement through the components in `technical-spec.md` §2
- Related technical spec sections: §2 Architecture Overview, §4 Backend Requirements
- Supersedes / superseded by: —

---

> Blueprint: blueprints/01-docs/05-architecture/architecture-decisions/ADR-000-template.md
