# ADR-006: Session lifetime of 240 minutes idle, 12 hours absolute

**ADR ID:** ADR-006
**Status:** Accepted
**Date:** 2026-08-15
**Decision owner:** The developer (sole owner for the prototype — Q-026)
**Review date:** Before the platform is used outside a scenario test

---

## Context

ADR-003 chose email and password with a server-side session, and required that a session expires
and that expiry is checked on the server on every request — but not for how long. Q-021 held the
number open, and `.env.example` shipped `SESSION_IDLE_TIMEOUT_MINUTES` deliberately blank with a
startup failure rather than a default, so that nobody could answer it by accident.

Two facts about *this* system decide the number, and neither is a general security consideration:

- **Utility control rooms run 12-hour shifts.** A timeout tuned for an office application expires
  in the middle of one.
- **The platform is read-only toward the grid** (BR-005, SEC-Z-005). No session, however stale,
  can move a crew or send a command. Its blast radius is a view.

## Options considered

1. **A short idle timeout — 15 to 30 minutes**, the ordinary default for an application holding
   sensitive data. Costs the thing that matters most here: an operator returning from a
   radio call mid-storm finds a sign-in screen. That is a safety failure dressed as a control.
2. **240 minutes idle, 12 hours absolute** — half a shift of inactivity, one full shift in total.
   Costs a genuinely longer window in which an unattended screen stays live.
3. **No expiry at all** — maximum availability, and it makes SEC-A-002 unsatisfiable. Rejected: a
   session that never expires is not a session, and the requirement exists for a reason.

*Compared on:* which interface is simpler · which is more general · which forces callers
to do work that should be inside · which is cheaper to reverse.

## Decision

**240 minutes idle, 12 hours absolute.** Both checked server-side on every request.

**Admin actions re-authenticate regardless of session age** — loading or replacing a scenario,
deleting one, resolving unmatched assets, and resetting another user's password. The password is
re-entered at the moment of the action, not inherited from the session.

## Reason

The two halves of the decision defend against different things, which is why there are two
numbers rather than one. The idle timeout stops a forgotten screen staying live indefinitely;
the absolute cap stops a session outliving the shift that created it.

Re-authentication on admin actions is what makes the long window acceptable. Everything a stale
session can reach is a **view** — and every action that changes the world for another user is
gated on a password typed just now. That is a tighter control than a short timeout, and it costs
an operator nothing during the storm the platform exists for.

The short-timeout option was rejected on a safety argument, not a convenience one: this product's
whole premise is that it is usable during a hurricane by someone who has just put down a radio.

## Consequences

- **Positive:** No operator is signed out mid-storm by the clock. SEC-A-002 becomes testable — a
  test can now assert a specific duration. The `SESSION_IDLE_TIMEOUT_MINUTES` startup failure can
  finally be satisfied with a real value.
- **Trade-off or limitation:** A four-hour window in which an unattended, signed-in screen in a
  control room is readable by anyone who walks past. That is a real exposure and it is accepted
  knowingly: the mitigation is physical control of the room, which is outside this system, plus
  re-authentication on every action that writes something another person depends on.
- **Rule the AI assistant must follow during implementation:** Both limits are read from
  configuration and neither has a default — a missing value fails at startup. Never widen either
  to make a test convenient. Every admin action re-prompts for the password; never treat an
  existing session as sufficient authority for one.

> **If no trade-off is visible, keep looking.** A choice with no downside was never a
> choice — you are comparing in the abstract instead of weighted for this context.

## Compliance

| Enforced by | Where |
|---|---|
| SEC-A-002, STEST-002, and manual review of the admin re-authentication paths | [`../../04-technical-spec/fitness-functions.md`](../../04-technical-spec/fitness-functions.md) |

No fitness function guards this. Authentication is Generic in
[`subdomain-map.md`](../../01-intent/subdomain-map.md), so it is governed by tests of its
behaviour rather than by a structural guard — the same position ADR-003 took, and stated here
rather than implied.

## Revisit when

The platform is used by anyone outside the scenario-test group, **or** a second authentication
factor arrives (Q-022 records TOTP as P1). Either changes the calculation: a second factor makes
a longer session cheaper, and an external user group makes it more expensive.

## Impact

| Dimension | Impact |
|---|---|
| Security | Mixed, and deliberately so. A longer window on a read-only surface, bought against re-authentication on every write that matters. Weaker than a short timeout in one specific way: an unattended screen. |
| Reliability | Positive. The failure this prevents — an operator locked out mid-storm — is the one that costs something real. |
| Performance | Neutral. A session lookup per request against a local store. |
| Cost | Zero. |
| Maintainability | Positive. Two named numbers in configuration, no defaults, and a startup failure when either is absent. |

## Related

- Related requirements: SEC-A-002, SEC-A-004, SEC-Z-006, REQ-NF-002
- Related technical spec sections: §7.1 Authentication, §7.5 Secrets management
- Answers: Q-021. Does not settle Q-022 (second factor), recorded as P1: TOTP, never SMS.
- Supersedes / superseded by: — (extends ADR-003, which deferred this number)

---

> Blueprint: blueprints/01-docs/05-architecture/architecture-decisions/ADR-000-template.md
