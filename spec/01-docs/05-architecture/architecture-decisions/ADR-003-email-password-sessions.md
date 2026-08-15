# ADR-003: Email and password with server-side sessions

**ADR ID:** ADR-003
**Status:** Accepted
**Date:** 2026-08-15
**Decision owner:** Tech lead (not yet named)
**Review date:** Before the platform is used outside a scenario test

---

## Context

Two roles exist, admin and user (REQ-R-001), and sign-in is inside version one. CON-006 forbids
paid third-party services. The platform is internal, under 50 users, one organisation, and the
build horizon is about a week.

`subdomain-map.md` classifies authentication as **Generic** — everyone needs it, nobody wins
with it — so the goal is the cheapest thing that separates who may load a scenario from who may
only act on one, not a well-modelled identity system.

The source PRD (§8) requires a second factor for the full platform. Whether version one carries
one is a separate decision (Q-022), not settled here.

## Options considered

1. **Email and password, server-side sessions** — nothing to buy, nothing to depend on, and
   testable without any external account, which matters when the whole product is exercised
   through prepared scenarios. Costs owning password hashing, reset, and lockout.
2. **Corporate SSO / OAuth** — the realistic long-term answer for a utility control room, and
   no password stored anywhere. Costs a dependency on SGW's identity team, which version one
   has no access to, and an outage path outside SGW's control on the day of a storm.
3. **Magic link, passwordless** — removes the password entirely, and moves the whole problem
   into email delivery. Email delivery is an external service, which CON-006 constrains, and
   an authentication method that fails when email is slow is the wrong one for an application
   used during an emergency.

*Compared on:* which interface is simpler · which is more general · which forces callers
to do work that should be inside · which is cheaper to reverse.

## Decision

Use **email and password with server-side sessions**. Passwords are stored as hashes and never
logged. A session is created server-side at sign-in, checked server-side on every request, and
ended server-side at sign-out.

## Reason

It is the only option that has no dependency outside the build, which is what CON-006 asks for
and what lets the whole product be exercised from prepared data without a live account
anywhere. For a Generic subdomain the correct instinct is to buy — and the correct instinct is
overruled here by a constraint, not forgotten. That is why the subdomain map already flags
authentication as *build thin, flag to buy later*.

Option 3 was rejected on a stronger ground than cost: an authentication path that depends on
email delivery is one that degrades exactly when a storm is degrading everything else.

## Consequences

- **Positive:** No external dependency, no account to provision, no provider outage on the
  critical path. Sign-in works in a scenario test with no network at all.
- **Trade-off or limitation:** The project now owns password handling — hashing, reset, and
  lockout — which is work with a known-bad failure mode and no product value. It is also the
  option a real deployment is least likely to keep: corporate SSO is where this ends up, and
  this decision is deliberately the cheap version that gets replaced.
- **Rule the AI assistant must follow during implementation:** Never store or log a password,
  a hash, or a session identifier. Never check a session only in the browser. Never add a
  sign-in path, an account-creation path, or a role, beyond the two in REQ-R-001, without a
  new ADR.

> **If no trade-off is visible, keep looking.** A choice with no downside was never a
> choice — you are comparing in the abstract instead of weighted for this context.

## Compliance

| Enforced by | Where |
|---|---|
| Manual review by the tech lead, plus the deny tests in `technical-spec.md` §11 | [`../../04-technical-spec/fitness-functions.md`](../../04-technical-spec/fitness-functions.md) |

No fitness function guards this one, and that is stated rather than implied: authentication is
Generic, so it is governed by tests of its behaviour rather than by a structural guard.

## Revisit when

The platform is used by anyone outside the scenario-test group, **or** SGW's identity team
becomes available to the project. Either makes the corporate SSO option cheaper than the
password handling this decision takes on.

## Impact

| Dimension | Impact |
|---|---|
| Security | Mixed. No third-party account to compromise, but password handling is now the project's own risk, and no second factor is yet decided (Q-022). |
| Reliability | Positive. Nothing outside the process has to be reachable for someone to sign in during a storm. |
| Performance | Neutral. A session lookup per request against a local store. |
| Cost | Positive. Zero, which is what CON-006 requires. |
| Maintainability | Negative in the medium term. This is the component most likely to be replaced, and the subdomain map already says so. |

## Related

- Related requirements: REQ-NF-002, REQ-R-001, REQ-R-002
- Related technical spec sections: §7.1 Authentication, §7.5 Secrets management
- Open questions this does **not** settle: Q-021 (session lifetime), Q-022 (second factor)
- Supersedes / superseded by: —

---

> Blueprint: blueprints/01-docs/05-architecture/architecture-decisions/ADR-000-template.md
