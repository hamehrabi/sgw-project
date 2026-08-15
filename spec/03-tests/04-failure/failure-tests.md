# failure-tests.md — Failure Test Cases

> **Purpose (Ch. 4 §4.6):** Checks invalid inputs, permissions, missing data, and error
> paths.
> **Sources:** Ch. 4 §4.6, Ch. 17 §17.7, Ch. 22.

Planning worksheet for discovering these cases →
[`edge-cases-and-failures.md`](edge-cases-and-failures.md).
This file holds the resulting **test cases**.

> **Beginner rule (Ch. 17 §17.1):** do not ask an AI agent to build a feature until you
> can write at least three checks for it — one normal case, one **edge case**, and one
> **failure case**.

---

## Failure test cases

| Test ID | Requirement | Failure condition | Input / trigger | Expected result | Log event expected | Status |
|---|---|---|---|---|---|---|
| FTEST-001 | REQ-F-010 | Scenario parse fails partway | A prepared storm valid for three of five inputs | The load fails as a whole; **no scenario row**; every already-loaded scenario still ranks; the failing file and stage are named | `SCENARIO_PARSE_FAILED` | Planned |
| FTEST-002 | REQ-NF-003 | A prepared data file becomes unreadable after load | Remove or corrupt one file while the scenario is in use | **Consequence corrected by CHG-013.** Every screen renders **unchanged and correct** — the joined view is served from stored rows, so the loss cannot reach it; **no blank screen, no error page**; the failing file is named to an admin, and replay and recovery are reported as affected | `SCENARIO_DATA_UNREADABLE` | Planned |
| FTEST-003 | REQ-NF-003 | Stale data presented without saying so | Advance the clock past the last good load | Every screen states that it is stale **and how old it is**; the banner is not dismissible | `SCENARIO_DATA_STALE` | Planned |
| FTEST-004 | BR-002 | An asset cannot be scored | An asset with contradictory inputs | It appears in the ranking as **UNSCORED with its reason** — not omitted, and not given a low score | `ASSET_SCORING_FAILED` | Planned |
| FTEST-005 | REQ-F-005, REQ-F-006 | Database write fails on a decision or a placement | Force the write to fail | No success shown; **no row written**; the operator's typed note or placement is still on screen | `DB_WRITE_FAILED` | Planned |
| FTEST-006 | REQ-F-006, BR-004 | Duplicate submission | The same decision request sent twice | One row only; the second returns 409 naming the existing decision | `DECISION_ALREADY_RECORDED` | Planned |
| FTEST-007 | SEC-A-002 | Expired session | Present a session past its idle limit | 401 and a return to sign-in preserving the intended destination; **no crash** | `SESSION_EXPIRED` | Planned |
| FTEST-008 | REQ-F-010 | Background job dies | Kill the parse worker mid-parse | Status `failed` with the stage named; no scenario created; the admin sees the reason rather than a spinner | `SCENARIO_PARSE_FAILED` | Planned |
| FTEST-009 | REQ-F-001 | Concurrency on the single writer | A parse job and an operator decision contend for the write | Neither is lost and neither shows a false success; the loser retries or reports honestly | `DB_WRITE_CONTENDED` | Planned |
| FTEST-010 | REQ-NF-002 | Unexpected server error | Force an unhandled exception on any route | Generic message to the user; **no stack trace, path, query, or file path in the response**; details logged internally with a request id | `UNHANDLED_ERROR` | Planned |

**There is no external-service row, and no retries-exhausted row.** Version one depends on no
external service (Round 6), and the only retryable operation is a read. That absence is a result
of CON-005 and CON-006 rather than a gap in this table — the two rows would be untestable, and
an untestable row that looks covered is worse than a missing one.

---

## Case template

```
Test ID:
Requirement:
Failure condition:
Preconditions:
Trigger / input:

Expected user-facing result:
Expected status code:
Expected system state:      [what must NOT have been written]
Expected log event:         [EVENT_NAME + safe context fields]
Expected recovery path:

Must NOT happen:
  - No stack trace, path, token, or private data in the response.
  - No partial write left behind.
  - No silent success.

Status: Planned / Written / Passing / Failing / Blocked
```

---

## Written out — the two that guard against a calm wrong screen

```
Test ID:            FTEST-004
Requirement:        BR-002, REQ-F-002
Failure condition:  An asset's inputs are missing or contradictory, so no score can be
                    produced for it
Preconditions:      A loaded scenario; one asset seeded with contradictory inputs
Trigger / input:    Run the ranking

Expected user-facing result: The asset appears in the list, in place, marked UNSCORED,
                             with the reason it could not be scored
Expected status code:        200 — the ranking succeeded; one asset did not
Expected system state:       No risk_scores row for that asset. Every other asset scored.
Expected log event:          ASSET_SCORING_FAILED with scenario_id, asset_id, reason
Expected recovery path:      None automatic. A person sees it and decides.

Must NOT happen:
  - The asset is absent from the list
  - The asset is present with a score of zero, or any default score
  - The asset is present with a rank and no reason
  - The list renders as though every asset was scored

Failure meaning: an asset silently missing from a ranking is indistinguishable, on screen,
from an asset that is safe — and the consequence is a crew not sent to something that
failed. This is the most dangerous single failure in the product, and it is the one an
implementation will most naturally get wrong, because dropping the row is the tidiest code.

Status: Planned
```

```
Test ID:            FTEST-002
Requirement:        REQ-NF-003
Failure condition:  A prepared data file becomes missing or unreadable after the scenario
                    loaded successfully
Preconditions:      A loaded, ranked scenario; all four screens reachable
Trigger / input:    Delete or corrupt one of its files

Expected user-facing result: Every screen still renders the last good picture, each one
                             stating that it is stale, how old it is, and which file failed
Expected status code:        200 on every screen
Expected system state:       The stored scenario is untouched. No partial re-load.
Expected log event:          SCENARIO_DATA_UNREADABLE with scenario_id, file_name,
                             last_good_at
Expected recovery path:      The admin replaces the file and re-loads. Until then, work
                             continues on stated-stale data.

Must NOT happen:
  - Any blank screen
  - Any error page
  - Any screen showing old data WITHOUT saying it is old
  - The staleness banner being dismissible

Failure meaning: the platform stopped working during the event it exists to serve. Worse,
the third bullet is the version that looks fine — current-looking stale data is how a
crew gets placed against yesterday's forecast.

Status: Planned
```

---

## Error state → recovery path (Ch. 22 §22.3)

Every error state needs a recovery path, a user message, a log event, and a test.

| Error state | Recovery path | What to test |
|---|---|---|
| Invalid login input | Reject and show clear field-level feedback. | Empty password returns a validation error. |
| Wrong credentials | Safe message without revealing which field was wrong. | Incorrect email or password produces the **same** message. |
| Database timeout | Stop the request, log the timeout, ask the user to try again. | A simulated timeout does not show successful login. |
| Expired session | Redirect to login and preserve the next safe destination. | A protected route redirects instead of crashing. |

---

## Error-handling behavior to assert (Ch. 7 §7.10)

| Error situation | Expected behavior |
|---|---|
| Missing required field | Reject, explain the missing field, keep the user input on screen. |
| Not signed in | Return 401 and ask the user to sign in. |
| No permission | Return 403 and explain the user cannot access the resource. |
| Resource not found | Return 404 with a safe message. |
| External service failure | Retry if safe, otherwise show a temporary failure message. |
| Unexpected server error | Return a general error message and log the details internally. |

---

## Testing error handling with AI help (Ch. 18 §18.5)

AI-generated error tests are often too simple. Ask for **exact** expected messages, status
codes, and recovery behavior.

| Error type | Example scenario | Expected behavior |
|---|---|---|
| Missing required input | Email field empty during login. | Validation error explains that email is required. |
| Invalid input format | Email does not contain a valid format. | Validation error explains the format problem. |
| Wrong credentials | Password does not match account. | Authentication fails **without creating a session**. |
| Unauthorized access | User tries to access a private resource. | Access error; private data hidden. |
| Temporary service issue | External service unavailable. | System retries or reports failure **without corrupting data**. |

---

## Regression failures

Every fixed bug adds a case here that **fails before** the fix and **passes after**
(Ch. 19 §19.6).

| Test ID | Bug ID | Failure it prevents | Added on |
|---|---|---|---|

No bug has been found, because no code exists. The table stays empty rather than carrying a
placeholder row.

---

## Rules

- A failure test asserts the **safe** outcome, not just "an error happened."
- Assert what must **not** be in the response: stack traces, internal paths, tokens,
  whether an account exists.
- Assert system state: a failed request must leave no partial write.
- Never delete or weaken a failure test to make code pass.

**One rule is specific to this product and sits above those four: assert that a failure is
visible.** The ordinary failure test asks whether the system stayed safe. Here the expensive
failure is a system that stayed safe and *looked fine* — an empty ranking, a clear board, a
missing asset. FTEST-002, FTEST-003 and FTEST-004 each assert something is **shown**, and each
is the test most likely to be quietly weakened into "no exception was raised".

---

> Blueprint: blueprints/03-tests/04-failure/failure-tests.md
