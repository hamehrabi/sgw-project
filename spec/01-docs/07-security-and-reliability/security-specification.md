# Security Specification

> Source: Ch. 21 — Security-First Spec-Driven Engineering.
> **Beginner rule:** do not write "make it secure" as a requirement. Write the exact
> security behavior you expect. A clear rule can be reviewed, tested, and implemented.
> A vague security wish cannot.

**You decide the security policy in the specification. The agent does not.**

---

## 1. Authentication (*who are you?*)

| Area | Requirement |
|---|---|
| Account access | Email and password, with a server-side session checked on every request (ADR-003). No external identity provider. |
| Session lifetime | **240 minutes idle, 12 hours absolute** (ADR-006), both checked server-side on every request. **Admin actions re-authenticate regardless of session age.** |
| Password handling | Stored as a hash only. Never stored, logged, echoed, or returned in plain text. |
| Account recovery | **An admin resets the password by hand**, setting a temporary one the user must change at next sign-in. No email is sent, because version one has no external services (CHG-004, Q-024). |
| Logout | The session ends server-side. A logout the server does not know about is a session still open. |
| Multi-factor (if any) | **None in version one** (CON-006). Recorded as P1: **TOTP, never SMS**. |

| ID | Authentication requirement | Acceptance criteria |
|---|---|---|
| SEC-A-001 | A user must sign in with an email and password before reaching any scenario, asset, ranking, board, or decision data. | A signed-out request to any data route returns 401 and no body containing scenario data. |
| SEC-A-002 | A session expires after **240 minutes idle** or **12 hours absolute**, whichever comes first, checked on the server on every request. Admin actions re-authenticate regardless of session age. | A request carrying an expired session returns 401 even when the browser still holds the value. An admin action with a 10-minute-old session still prompts for the password. |
| SEC-A-003 | Plain-text passwords are never stored, logged, or returned. | Storage holds only the hash; no log line and no response body contains a password field. |
| SEC-A-004 | Password recovery is an admin-set temporary password. It is **single-use** and **expires 24 hours** after issue, and the user must change it at first sign-in. No email is sent. | A user with a temporary password reaches only the change-password screen. A temporary password used twice, or used after 24 hours, is refused. |
| SEC-A-005 | Sign-in is rate-limited per account and per IP, and returns 429 with `Retry-After` when exceeded. | Six failed attempts on one account within ten minutes return 429, including when each attempt comes from a different address. |
| SEC-A-006 | No second authentication factor in version one; TOTP is recorded as P1 and SMS is excluded permanently. | No second-factor path exists in the build. The exposure is bounded by SEC-A-002's re-authentication on admin actions. |

**SEC-A-005 exists because the per-account half is the one that matters.** An IP-only limit is
walked straight past by a distributed attempt, and this is the only account system standing in
front of critical-infrastructure data.

---

## 2. Authorization / RBAC (*what are you allowed to do?*)

A user may be authenticated and still not allowed to perform an action.

### Role permission matrix

Two roles, and the enforcement for each row. The same matrix appears in `technical-spec.md`
§7.2 as a design statement; **this one carries the control that enforces it**, which is what
makes it the security document's version rather than a copy of that one.

| Action | Admin | User | Enforced by |
|---|---|---|---|
| Upload a prepared scenario | Yes | No | SEC-Z-002 |
| Delete or replace a scenario | Yes | No | SEC-Z-002 |
| Switch between loaded scenarios | Yes | Yes | SEC-Z-001 |
| View the joined asset view | Yes | Yes | SEC-Z-001 |
| View the ranked risk list and its reasons | Yes | Yes | SEC-Z-001 |
| Apply a forecast revision and re-rank | Yes | Yes | SEC-Z-001 |
| Record a crew placement | Yes | Yes | SEC-Z-001 |
| Accept, change, or reject a recommendation | Yes | Yes | SEC-Z-001 |
| Dismiss a false alarm | Yes | Yes | SEC-Z-001 |
| Read the decision record | Yes | No | SEC-Z-003 |
| Reset another user's password | Yes | No | SEC-Z-006 |
| **Edit or delete a decision record** | **No** | **No** | SEC-Z-004 |
| **Send any command to a grid or water control system** | **No** | **No** | SEC-Z-005 |

> A role table gives the agent a precise boundary. It does not need to guess whether a
> Member can invite users — the table already says no.

**Defensive authorization pattern (Ch. 21 §21.3)** — specify the *order* of the checks, not
the code that runs them. For every protected action, write three rules in this order: deny
when there is no signed-in user; deny when the resource belongs to a tenant the user is not
in; allow only when the user's role appears on an explicit allow-list. Each rule is one deny
test before any code exists, and the allow-list is a decision you make here rather than one
the agent infers. The worked example at the end of this file shows the three filled in.

**The middle check does not exist in this system, deliberately.** There is one organisation, so
the order is two checks: signed in → role on the allow-list. It is written down because a
missing check and a check nobody thought of look identical in code, and this line is where the
tenant check goes on the day one is needed.

| ID | Authorization requirement | Acceptance criteria |
|---|---|---|
| SEC-Z-001 | Every endpoint checks, in order, that a session exists and that the user's role is on that action's allow-list, before any data is read or written. | A signed-out request returns 401 and touches no data. An out-of-role request returns 403 and writes nothing, including no partial write. |
| SEC-Z-002 | Only an admin may upload, replace, or delete a scenario. | A non-admin upload returns 403, creates no scenario, stores no file, and appends a refusal to the decision record (AC-009). |
| SEC-Z-003 | Only an admin may read the decision record. | A non-admin request to the decisions endpoint returns 403 and no rows. |
| SEC-Z-004 | No role, including admin, may update or delete a decision record. The database refuses the statement. | An `UPDATE` issued directly against `decision_records` is refused by the database, not by the application (FF-004, ADR-004). |
| SEC-Z-005 | No role may issue a command to a system that physically controls the grid or the water network. No such code path exists in either direction. | A review of the endpoint index finds no outbound write path; the dependency table in `technical-spec.md` §10 is empty. |
| SEC-Z-006 | An admin may set a temporary password for another user. Nobody, including an admin, may read another user's password hash. | An admin reset succeeds and forces a change at next sign-in; no endpoint or log returns a hash. |

**SEC-Z-005 is asserted structurally rather than tested behaviourally**, and that is the
stronger form: it is not that the system refuses to send a command, it is that no code exists
which could. Version one's entire boundary is a file read (CON-005, BR-005).

---

## 3. Input validation

Validation happens at **system boundaries**. Do not rely only on the frontend — API
requests can come from outside the visible interface.

| Input | Validation rule | Error behavior |
|---|---|---|
| Email at sign-in | Required; trimmed; length-bounded before any lookup. | Identical response for an unknown email and a wrong password — the message must not distinguish them. |
| Password at sign-in | Required; compared against the hash in constant time; never echoed back in any form. | The same safe message, and a 429 once SEC-A-005's limit is reached. |
| Temporary password change | Required; length-bounded; must differ from the temporary one. | Field-level message; the user stays on the change screen and reaches nothing else. |
| Uploaded scenario files | Within the size limit (Q-017); type on the allow-list, verified by content inspection rather than by extension; parses; passes the seven defect rules. | 413 over size, 415 off the allow-list, 422 on a validation failure. Refused before parsing wherever the check allows it, naming the file. |
| Role value | Must be exactly `admin` or `user`. | 400. A third role cannot arrive through an API call — only through a migration and a new ADR. |
| `scenario_id` in any path | Required; must exist. | 404 with a safe message. The response for "does not exist" and "you may not see it" is identical. |

---

## 4. Data protection

| Area | Question | Rule |
|---|---|---|
| Data minimization | Do you need this data? | Do not collect personal data not needed for the feature. |
| Storage | How should data be stored? | Sensitive account data must use approved storage mechanisms. |
| Transport | How does data move? | Private user data only through protected channels. |
| Logging | What must **not** be logged? | Never log passwords, tokens, reset links, or full secret values. |
| Retention | How long is data kept? | Follow the retention rule in the product specification. |

**The four classes named in Round 6, and what each rule means here:**

| Class | Rule |
|---|---|
| Credentials, sessions, keys | Never logged, never returned, never included in an error message. A password appears exactly once — in the sign-in request body — and is a hash from that point onward. |
| Asset locations and connections | Stored, reachable only by a signed-in user, and **logged as `asset_id` only**. A readable copy of this is a map of critical infrastructure, which is why the source PRD builds the entire platform behind a one-way wall. |
| Personal data | User emails, and any damage report close enough to a household to identify one. Logged as `user_id`; damage locations aggregated to neighbourhood level in every log and export (REQ-NF-007). |
| Customer business data | Outage and restoration detail. Shown to signed-in users, never exported anywhere by version one — there is nowhere to export it to. |

The data named in CON-003 must not be stored at all, and which data that is remains open —
see Q-007. Retention for the decision record is likewise unset — see Q-015.

---

## 5. Secrets management

Secrets are values that allow access to protected systems: API keys, database passwords,
signing keys, private tokens.

- Never hardcode a secret into source code, templates, screenshots, logs, or examples.
- Use placeholders in documentation → [`../.env.example`](../../.)
- Document where each real value is configured → [`../ops/environment-config.md`](../../07-ops/01-deployment/environment-config.md)

| Secret | Where configured | Must never appear in | Code reference |
|---|---|---|---|
| Session signing key | environment variable | source, logs, error messages, client responses | by configuration name only |
| Password hashing parameters | environment variable | source, logs, error messages, client responses | by configuration name only |
| Database file path | environment variable | logs, error messages, client responses | by configuration name only |

**There is no database credential**, because ADR-002 chose an embedded store: the database is a
file, and access to it is filesystem access. That removes a secret to rotate and removes the
role separation that BR-004 originally relied on — ADR-004 replaces the mechanism, and the
residual weakness is recorded there rather than here.

---

## 6. Secure error handling

Error handling has two responsibilities: help the user recover, and protect the system
from exposing internal details.

| Problem | Unsafe response | Safer response |
|---|---|---|
| Login failed | Detailed account or password reason. | "The email or password is incorrect." |
| Access denied | Internal permission rule details. | "You do not have permission to perform this action." |
| Server failure | Stack trace or database error. | "Something went wrong. Please try again later." |
| Validation failure | Raw parser or framework error. | "The submitted value does not match the required format." |

One project-specific rule sits above these: **a failure must never render as safety.** A
ranking that could not be computed says so; it never shows an empty list that reads as no risk.
A board that could not load says so; it never shows an empty board that reads as no damage.
That is a security property here as much as a usability one, because the consequence is a crew
not sent.

---

## 7. Feature security specification

Copy per sensitive feature.

```
Feature:        [name]
Requirement ID: SEC-###

Authentication:  [who must be signed in]
Authorization:   [which roles may perform this]
Role assignment: [what roles can be granted, by whom]
Validation:      [required fields, formats, duplicate rules]
Data protection: [what must not be exposed or logged]
Secure errors:   [what unauthorized users receive]
Testing:         [allowed actor, disallowed actor, invalid input, duplicate, safe error]

Acceptance criteria:
1.
2.
3.
```

Two features are filled in below: the scenario upload, because it is the only place untrusted
input enters the system, and the admin password reset, because it is new in this round and it
lets one person take over another's account if it is specified loosely.

```
Feature:        Upload a prepared storm scenario
Requirement ID: SEC-Z-002

Authentication:  The uploader must be signed in.
Authorization:   Admin only. A user role receives 403 and no file is written to disk.
Role assignment: Roles are set in the database, not through any endpoint. There is no
                 self-service promotion path, at any version.
Validation:      Size within the limit (Q-017); type on the allow-list, verified by
                 content inspection and never by extension; the files parse; the seven
                 defect rules pass. A failure at any stage creates no scenario and leaves
                 every already-loaded scenario untouched.
Data protection: The uploaded file is stored under a generated identifier, never under the
                 supplied filename. Its contents are never logged. It is never served back
                 to any browser, which is what keeps the no-malware-scanner decision
                 acceptable.
Secure errors:   A non-admin receives a generic access-denied response that does not reveal
                 whether the upload endpoint exists or what it accepts.
Testing:         admin upload, user upload, oversize file, wrong type with a right
                 extension, file that parses but fails validation, duplicate upload

Acceptance criteria:
1. A signed-out request writes no file and returns 401.
2. A signed-in user with the user role returns 403, writes no file, and the refusal is
   appended to the decision record.
3. A file whose extension is on the allow-list but whose content is not is refused with 415.
4. A file that parses but fails a defect rule creates no scenario, and the previously
   loaded scenarios still rank.
5. The stored filename contains no part of the supplied filename.
6. No log line contains file contents.
```

```
Feature:        Admin resets another user's password
Requirement ID: SEC-Z-006, SEC-A-004

Authentication:  The admin must be signed in.
Authorization:   Admin only. No user may reset any password but their own, and no user may
                 reset another's under any circumstance.
Role assignment: Unchanged by this action. A reset never alters a role — a reset that could
                 also grant admin is a privilege-escalation path wearing a helpful label.
Validation:      The target user must exist. The temporary password is generated by the
                 system, never chosen by the admin, and is shown once.
Data protection: No password hash is ever returned or logged. The temporary password is
                 shown once in the response and never written to a log.
Secure errors:   A non-admin receives a generic access-denied response. Resetting a
                 non-existent user returns the same response as resetting an existing one.
Testing:         admin resets a user, user attempts to reset another user, user resets
                 self, reset of unknown user, sign-in with the temporary password, sign-in
                 after the change

Acceptance criteria:
1. A user role attempting to reset another user returns 403 and changes nothing.
2. After a reset, the target user can reach only the change-password screen.
3. The old password no longer authenticates.
4. The reset appends a row to the decision record naming the admin who performed it.
5. No response or log contains a password hash.
6. The reset does not change the target user's role.
```

---

## Security review checklist (Ch. 21 §21.8)

- [x] Every protected feature has an authentication requirement.
- [x] Every sensitive action has an authorization rule.
- [x] Role permissions are documented in a table.
- [x] User input rules are specific and testable.
- [x] Backend validation is required, not only frontend validation.
- [x] Sensitive data is not logged or returned unnecessarily.
- [x] Secrets are not stored in source code or examples.
- [x] Error messages are safe for users and useful enough for recovery.
- [ ] Security requirements are linked to tests.
- [ ] The AI agent has clear instructions not to add unapproved access paths.

The two unticked boxes are unreached rather than unmet: Round 7 writes the tests that link to
`SEC-A-###` and `SEC-Z-###`, and Round 8 writes `AGENT.md`. Ticking either now would claim work
nobody has done.

Full review pass → [`../review/security-review.md`](../../05-review/02-checklists/security-review.md)

---

> Blueprint: blueprints/01-docs/07-security-and-reliability/security-specification.md
