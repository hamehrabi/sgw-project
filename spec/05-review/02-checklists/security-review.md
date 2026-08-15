# Security Review Checklist

> Source: Appendix M + Ch. 21 §21.8.
> Use this **before accepting AI-generated code** that handles users, data, files, APIs,
> payments, or administrative actions — and again before deployment.

> Copy this file to `security-review-<feature>.md` and fill it in, once per review. **The
> header fields below stay blank in this copy** — a review that has not happened has no
> reviewer and no date, and writing a plausible one is worse than leaving it empty.

**Feature / module:**
**Reviewer:**
**Date:**
**Related requirements:** SEC-###

---

## Authentication

- [ ] Protected actions require authentication.
- [ ] Session or token handling is defined.
- [ ] Expired or invalid credentials are handled safely.
- [ ] Authentication errors do not reveal sensitive information.
- [ ] Password reset flows expire and do not confirm whether an account exists.
- [ ] Logout ends the session server-side, not only client-side.

**The reset row reads differently here.** There is no reset link and no email (CHG-004): an
admin sets a temporary password. The equivalent checks are that the target reaches only the
change-password screen, that the old password stops working, that resetting an unknown user
returns the same response as resetting a known one, and that **the reset does not change the
target's role** (SEC-Z-006). The last one is the escalation path this flow could quietly become.

## Authorization and access control

- [ ] Each protected action checks the user's role or ownership.
- [ ] Users cannot access another user's data by changing IDs.
- [ ] Admin actions are separated from normal user actions.
- [ ] **Default access is deny unless explicitly allowed.**
- [ ] Authorization is enforced on the **server**, not just hidden in the UI.
- [ ] Tenant/project isolation is applied to every query.

The last row: **there is no tenant isolation**, by decision (one organisation,
`database-design.md` §5). The check that replaces it is **`scenario_id` scoping on every read** —
ITEST-005 asserts that two loaded storms never blend into one ranking. A missing scope here is
not a leak between customers; it is a ranking assembled from two different storms, which looks
entirely plausible on screen.

## Validation, data, and secrets

- [ ] All user input is validated at the boundary.
- [ ] Backend validation exists even where the frontend already validates.
- [ ] Sensitive fields are protected in storage and logs.
- [ ] Secrets are not hardcoded or printed.
- [ ] No secrets appear in source, examples, screenshots, or error messages.
- [ ] Errors are safe for users and useful for internal logs.
- [ ] Security tests cover **abuse cases**, not only happy paths.

## Spec-level checks (Ch. 21 §21.8)

- [ ] Every protected feature has an authentication requirement.
- [ ] Every sensitive action has an authorization rule.
- [ ] Role permissions are documented in a table.
- [ ] User input rules are specific and testable.
- [ ] Sensitive data is not logged or returned unnecessarily.
- [ ] Security requirements are linked to tests.
- [ ] The AI agent has clear instructions not to add unapproved access paths.

---

## The four checks specific to this system

Run these in addition to the lists above. Each is asserted somewhere below the application on
purpose, because an application-level version would pass while being wrong.

| Check | How to verify | Why not at the application layer |
|---|---|---|
| **The decision record is un-editable** | Issue an `UPDATE` and a `DELETE` against `decision_records` directly, as the application runs. Both must be refused **by the database** (STEST-008). | A service-layer rule is removed by the first refactor with every functional test still green. ADR-004 puts it in triggers for exactly this reason. |
| **No outbound path exists** | Search the built artifact for any outbound network call; check the endpoint index for any write toward a source system (STEST-010). | *The platform can never command the grid* is only provable as an absence. A refusal can be bypassed; missing code cannot. |
| **Both triggers survived the migration** | After every deploy, confirm `decision_records_no_update` and `decision_records_no_delete` exist. | A migration can drop a trigger, and nothing in the test suite notices. ADR-004 names this as its residual weakness. |
| **Nothing uploaded is served back** | Confirm no route returns an uploaded file's contents to a browser. | It is the condition under which "no malware scanner" (CON-006) stays acceptable. If it ever stops being true, that decision must be reopened. |

---

## Findings

| # | Severity | Area | Risk | Evidence | Recommended fix | Status |
|---|---|---|---|---|---|---|
| 1 | Critical / High / Medium / Low | | | | | Open |

**Severity guide (Ch. 24 §24.4)**

| Condition | Severity | Response |
|---|---|---|
| Unauthorized user reaches a restricted endpoint. | **Critical** | Review authorization rule and security logs immediately. |
| A valid user cannot authenticate. | **High** | Investigate immediately; protect account access. |
| Sensitive value appears in a log. | **High** | Purge, rotate the secret, fix the log call. |
| External API call fails repeatedly. | Medium | Apply fallback or degrade gracefully. |

Two rows are worth adding for this system, both **Critical**: an `UPDATE` against
`decision_records` that succeeds, and a full asset location or connection appearing in a log.
The first destroys the evidence the platform exists to produce; the second is a map of critical
infrastructure in a file that gets shipped to wherever logs go.

---

## Decision

- [ ] **Pass** — no security blockers.
- [ ] **Pass with follow-up** — issues logged, none blocking.
- [ ] **Block release** — must be fixed before merge/deploy.

---

> Blueprint: blueprints/05-review/02-checklists/security-review.md
