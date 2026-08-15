# Security Test Plan

> Source: Ch. 17 §17.5, Ch. 21, Ch. 27 §27.8.
> Security tests are **especially important** with AI-generated software, because an agent
> may implement the happy path and forget the denial path.

For every important feature ask:
1. Who is **allowed** to do this?
2. Who is **not allowed** to do this?
3. What input must be **rejected**?
4. What information must **never** be exposed?

---

| Test ID | Requirement | Risk | Scenario | Expected result | Status |
|---|---|---|---|---|---|
| STEST-001 | SEC-A-001, SEC-Z-001 | Unauthenticated access | Request any data route with no session — assets, ranking, board, decisions. | 401, and no body containing scenario data. | Planned |
| STEST-002 | SEC-A-002 | Session reuse after expiry | Present a session the server has expired, and one the user has signed out of. | 401 in both cases, checked on the **server**, even though the browser still holds the value. | Planned |
| STEST-003 | SEC-A-001, SEC-A-003 | Account enumeration and credential leakage | Sign in with an unregistered email; then with a wrong password. Force a server error during sign-in. | **Identical** response for both attempts. No password, hash, or session value in any response body, error, or log line. | Planned |
| STEST-004 | SEC-A-005 | Brute force | Six failed attempts on one account within ten minutes, **each from a different address**. | 429 with `Retry-After`. The per-IP limit alone must not be what stops it. | Planned |
| STEST-005 | SEC-Z-002, REQ-R-001 | Weak authorization | A `user` role calls the scenario upload endpoint **directly**, bypassing the interface. | 403; no scenario row; **no file written to disk**; a refusal recorded **in the security log** with actor, time, filename and reason (CHG-015). | Planned |
| STEST-006 | SEC-Z-002 | Broken validation | Upload a file whose extension is on the allow-list but whose content is not. Then one over the size limit. | 415 and 413 respectively, both refused before parsing, both naming the file. | Planned |
| STEST-007 | SEC-Z-003 | Weak authorization | A `user` role requests the decision record. | 403; zero rows returned. | Planned |
| STEST-008 | SEC-Z-004, REQ-R-002, BR-004 | The audit trail is editable | Issue an `UPDATE` and a `DELETE` against `decision_records` **directly against the database**, as the application runs. | Both refused **by the database** (ADR-004's triggers), not by the application. Row unchanged, byte for byte. | Planned |
| STEST-009 | REQ-NF-007 | Information leakage | Trigger logging and any export path with a damage report at household resolution. | Only neighbourhood-level figures appear. No asset location or connection appears in full — `asset_id` only. | Planned |
| STEST-010 | SEC-Z-005, REQ-R-003, BR-005 | An outbound path exists at all | Search the built artifact for any outbound network call, and the endpoint index for any write toward a source system. | **Zero.** This is asserted structurally: not that the system refuses to send a command, but that no code exists which could. | Planned |

---

## Security risk → test question (Ch. 17 §17.5)

| Security risk | Test planning question |
|---|---|
| Unauthorized access | What happens when a user tries to access data they do not own? |
| Broken validation | What happens when the request contains unexpected fields or dangerous input? |
| Information leakage | Does an error message reveal private data or system details? |
| Weak authorization | Can a normal user perform an admin-only action? |

**One row is absent from this list and from the suite, deliberately: cross-tenant access.**
There is one organisation and no `tenant_id` anywhere (Round 3), so there is no tenant boundary
to breach. Writing a test for it would manufacture a pass against a boundary that does not
exist. `database-design.md` §5 records the absence as a decision; the day it changes, this is
the paragraph that says a test is now owed.

---

## Per-role negative matrix

For each protected action, add one test per role that **must not** be able to perform it.

| Action | Admin | User | Signed out |
|---|---|---|---|
| Upload / replace / delete a scenario | allow | **deny 403 → STEST-005** | **deny 401 → STEST-001** |
| View assets, ranking, reasons, board | allow | allow | **deny 401 → STEST-001** |
| Apply a forecast revision | allow | allow | **deny 401 → STEST-001** |
| Accept / change / reject a recommendation | allow | allow | **deny 401 → STEST-001** |
| Dismiss a false alarm | allow | allow | **deny 401 → STEST-001** |
| Read the decision record | allow | **deny 403 → STEST-007** | **deny 401 → STEST-001** |
| Reset another user's password | allow | **deny 403 → STEST-011** | **deny 401 → STEST-001** |
| **Edit or delete a decision record** | **deny → STEST-008** | **deny → STEST-008** | **deny → STEST-008** |
| **Command a grid or water control system** | **deny → STEST-010** | **deny → STEST-010** | **deny → STEST-010** |

| Test ID | Requirement | Risk | Scenario | Expected result | Status |
|---|---|---|---|---|---|
| STEST-011 | SEC-Z-006, SEC-A-004 | Privilege escalation | A `user` role calls the password-reset endpoint for another user. Then an admin resets a user and the test checks the target's role. | 403 and no change in the first case. In the second, the password changes and **the role does not** — a reset that could also grant admin is an escalation path wearing a helpful label. | Planned |

> **Default access is deny unless explicitly allowed** (Appendix M).

---

## Rules

- Security tests must include **negative cases**, not only happy paths.
- Every rule in [`../docs/security-specification.md`](../../01-docs/07-security-and-reliability/security-specification.md)
  needs at least one test.
- Hiding a control in the UI is not a passing security test — assert the **server**
  rejects the request.

**Every test in this file calls the endpoint or the database directly.** None of them go through
the interface, and that is not an efficiency: `frontend-component-spec.md` hides the upload panel
from a non-admin, so an interface-driven test of STEST-005 would pass while the endpoint stayed
open. The interface hides controls *as well as*, never instead of, the server refusing them.

**Two tests here are structural rather than behavioural**, and both are stronger for it.
STEST-008 asserts the database refuses a statement, not that the application declines to issue
one — because a service-layer rule is removed by the first refactor with every functional test
still green. STEST-010 asserts that no outbound path exists to test, which is the only form in
which *the platform can never command the grid* is actually provable.

Full review pass → [`../review/security-review.md`](../../05-review/02-checklists/security-review.md)

---

> Blueprint: blueprints/03-tests/03-non-functional/security-tests.md
