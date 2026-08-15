# Edge Cases and Failure Conditions

> Source: Ch. 17 §17.7, Ch. 4 §4.6 (`failure-tests.md`), Ch. 30 §30.2.
> An **edge case** is an unusual but possible situation. A **failure condition** is a
> situation where the system cannot complete the request safely. Both must be planned
> before implementation — they are easy for AI agents to miss.

**Method:** start with the normal case, then ask what could be *empty, too long,
duplicated, expired, unavailable, unauthorized, or invalid*.

---

## Case table

| Case ID | Requirement ID | Case type | Input / condition | Risk covered | Status |
|---|---|---|---|---|---|
| FTEST-001 | REQ-F-010 | Failure | A prepared storm valid for three of five inputs | A half-loaded storm that ranks confidently on a third of the facts | Planned |
| FTEST-002 | REQ-NF-003 | Failure | A data file removed or corrupted after a successful load | The platform failing during the event it exists to serve | Planned |
| FTEST-003 | REQ-NF-003 | Edge | Time passes; the picture is old but the data is intact | Old data read as current — a crew placed against yesterday's forecast | Planned |
| FTEST-004 | BR-002 | Failure | An asset with contradictory inputs | An asset missing from a ranking, read as an asset that is safe | Planned |
| FTEST-005 | REQ-F-005 | Failure | The store fails the write as a placement is saved | A placement lost mid-storm | Planned |
| FTEST-006 | REQ-F-006 | Edge | The same decision request arrives twice | Two audit rows for one human decision | Planned |
| FTEST-007 | SEC-A-002 | Failure | A session presented past its idle limit | A stale session still acting | Planned |
| FTEST-008 | REQ-F-010 | Failure | The parse worker is killed mid-parse | A spinner that never resolves, hiding which stage broke | Planned |
| FTEST-009 | REQ-F-001 | Edge | A parse job and an operator decision contend for the single writer | A silent lost write under ADR-002's one-writer store | Planned |
| FTEST-010 | REQ-NF-002 | Failure | An unhandled exception on any route | A stack trace or file path reaching a browser | Planned |
| UTEST-003 | REQ-F-001 | Edge | A condition value six years old | A stale inspection presented like a live reading | Planned |
| UTEST-006 | REQ-F-001 | Edge | An outage total of zero | A percentage computed from a broken denominator | Planned |
| UTEST-007 | REQ-F-001 | Boundary | More customers out than a county contains | An impossible figure passed downstream as fact | Planned |
| UTEST-010 | REQ-F-002 | Edge | Two assets with identical scores | An order that changes between reads for no reason a user can see |Planned |
| UTEST-011 | REQ-F-008 | Edge | A dismissal with no reason given | An anonymous dismissal — control made cheap and untraceable | Planned |
| STEST-005 | SEC-Z-002 | Security | A `user` role calling the upload endpoint directly | A non-admin replacing the storm everyone is deciding against | Planned |
| STEST-006 | SEC-Z-002 | Security | A file with an allowed extension and disallowed content | Untrusted content parsed because the extension looked right | Planned |
| STEST-008 | SEC-Z-004 | Security | A direct `UPDATE` on `decision_records` | An audit trail its own subjects can rewrite | Planned |
| EV-007 | REQ-F-002 | Edge | A storm more severe than any in the golden set | A confident ranking extrapolated beyond anything it has seen | Planned |

> **"Case ID" CITES the test that covers the case — it does not mint a new identifier.**
> A case found here becomes a test somewhere: a failure case is an `FTEST-###` in
> [`failure-tests.md`](failure-tests.md), a boundary case is a `UTEST-###` in
> [`unit-tests.md`](../02-functional/unit-tests.md). Write that id here once it exists. Until it
> does, leave the sanctioned marker naming the question — the same `[TODO: ...]` form every
> other unknown uses.
>
> **And do not restate the test's expected result here.** A run that cites correctly can still
> copy the outcome into this table in its own words, and then two files describe the same
> assertion differently — "400; no row written" here against "400 + field-named message;
> nothing saved" there. Nothing is contradictory on the day it is written and nothing keeps
> them equal afterwards. **This table records what was DISCOVERED — the input or condition, the
> case type, the risk it covers — and points at the test for what the system must do.**
>
> This table used to arrive numbered `FTEST-001`…`FTEST-005` — **the same identifiers
> `failure-tests.md` mints, for different conditions.** `FTEST-002` was "Invalid format" there
> and "Value too long" here, so every workspace carried both and neither knew about the other.
>
> The worked example below already did it the right way: its discovery table cites `FTEST-001`
> and `UTEST-005` side by side, because a discovery table's job is to point at coverage, not to
> create a second numbering of it.

**Case types:** Normal · Edge · Failure · Security · Boundary

---

## The seven questions (Ch. 17 §17.7)

| Question to ask | Example |
|---|---|
| What if the value is empty? | A task title is blank. |
| What if the value is too long? | A project name has 500 characters. |
| What if the value is duplicated? | A user clicks submit twice. |
| What if the value is expired? | A reset token is used after expiry. |
| What if the user is not allowed? | A team member edits an owner-only setting. |
| What if the dependency fails? | An email service cannot send an invitation. |
| What if the action is repeated? | The same request arrives twice. |

### The seven questions, answered for this product

| Question | This project's case | Case type | Test that covers it |
|---|---|---|---|
| What if the value is empty? | A ranking with no items, and a board with no reports | Edge | FTEST-004 covers the dangerous half; `frontend-component-spec.md` fixes the wording for the rest |
| What if the value is too long? | An uploaded scenario over the size limit | Failure | STEST-006 — **and the limit itself is Q-017** |
| What if the value is duplicated? | The same decision submitted twice; the same scenario uploaded twice | Edge | FTEST-006, ITEST-005 |
| What if the value is expired? | A session past its idle limit; a condition observation six years old | Failure / Edge | FTEST-007, UTEST-003 |
| What if the user is not allowed? | A `user` role uploading a scenario or reading the decision record | Security | STEST-005, STEST-007 |
| What if the dependency fails? | **Not applicable — there is no external dependency** (Round 6). The nearest equivalent is a prepared file becoming unreadable | Failure | FTEST-002 |
| What if the action is repeated? | A retried decision write | Edge | FTEST-006, ITEST-002 |

**An eighth question belongs on this product and is not in the standard list:** *what if the
answer is nothing, and nothing looks like good news?* An empty ranking reads as no risk, an
empty board reads as all clear, and a missing asset reads as a safe asset. Three of the four
most valuable tests in this suite exist for that question alone.

---

## Failure sources checklist (Ch. 22 §22.2)

- [x] User input — missing, invalid, unexpected
- [x] Database — write failure, timeout, constraint violation
- [x] Network — request timeout, connection reset
- [ ] External service — unavailable, rate-limited, unexpected response shape
- [x] Background job — fails after the user has left the page
- [x] Concurrency — two users edit the same record
- [x] Authorization — role changes mid-session

**The external-service box is unticked because there is nothing to tick**, not because it was
skipped: version one depends on no external service (Round 6, CON-005, CON-006). It becomes live
the day the first source-system connection is made, and this is the line that says so.

**Concurrency is the one that was nearly missed here.** ADR-002 chose an embedded store with a
single writer, which is invisible at 50 users — until the parse job and an operator's decision
land together during a storm, which is exactly when both are busiest. FTEST-009 exists because
the *single writer* trade-off was written down in ADR-002 rather than discovered.

Each failure state must have a **recovery path, user message, log event, and test case** →
[`../docs/reliability-specification.md`](../../01-docs/07-security-and-reliability/reliability-specification.md)

---

> Blueprint: blueprints/03-tests/04-failure/edge-cases-and-failures.md
