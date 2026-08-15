# Reliability Specification

> Source: Ch. 22 — Reliability and Error Handling.
> Reliable software is not software that never fails. It fails in **controlled,
> understandable, and recoverable** ways.

> **Spec rule:** do not describe reliability as a general wish. Write it as a specific
> rule: *"If X fails, the system must do Y, record Z, and show message M."*

**Feature name:** Load a prepared storm and serve it — the whole runtime path of version one

**Requirement ID:** REQ-NF-003, REQ-F-001, REQ-F-010

Reliability is one of the three driving characteristics, and it is written against one fact:
this product is used *during* the event it describes. A screen that fails at a convenient moment
does not exist here — every failure lands in the middle of a storm, in front of someone deciding
where to send people.

---

## 1. Normal behavior

An admin uploads a prepared storm. The files are accepted, then parsed in a background job:
records are joined into one per asset, the seven known defect rules run, and assets that cannot
be matched are flagged for a person rather than merged. The scenario becomes selectable
alongside any others already loaded. From there the ranking, the planning view and the dispatch
board read stored results; applying a forecast change writes a new revision and re-ranks, leaving
the previous order retrievable. Every ranking delivered and every human decision appends a row
that cannot afterwards be altered.

---

## 2. Failure sources to consider (Ch. 22 §22.2)

| Failure source | Question to ask | Example recovery rule |
|---|---|---|
| User input | Missing, invalid, or unexpected data? | Reject with field-level validation messages. |
| Database | Write fails or takes too long? | Do not show success. Return a retry-safe error and log the failure. |
| Network | Request times out? | Apply a timeout rule and let the user retry safely. |
| External service | Third-party API unavailable? | Queue the action for later or mark it pending. |
| Background job | Job fails after the user left the page? | Store job status, retry if safe, expose the final result. |

**The external-service row does not apply to this system**, at any version — Round 6 confirmed
none. That removes a whole class of failure and is the main reliability benefit of CON-005 and
CON-006. The row stays visible so its absence is a recorded fact rather than an oversight.

**One source the generic list does not name matters most here: the data itself.** The prepared
files are known to arrive with seven measured defects. That is not a failure source in the
sense of something breaking — it is the normal condition, handled at load time rather than
recovered from at read time.

---

## 3. Important failure states

Copy per failure state.

```
- Failure state: [name]
  - Trigger:        [what causes it]
  - Recovery path:  [what the system does next]
  - User message:   [plain language, safe, with a next action]
  - Log event:      [EVENT_NAME with safe context fields]
  - Test case:      TEST-###
```

The three that matter most, filled in. Test case identifiers are written in Round 7 and are
shown as `—` rather than as a stub nobody can follow.

```
- Failure state: Scenario parse fails partway
  - Trigger:        A file parses for some inputs and fails for others, or the job dies
  - Recovery path:  Abandon the whole load. Create no scenario. Leave every already-loaded
                    scenario untouched and still rankable.
  - User message:   "This storm could not be loaded: <file> failed at <stage>. Nothing was
                    changed. You can fix the file and upload again."
  - Log event:      SCENARIO_PARSE_FAILED with scenario_name, file_name, stage, user_id
  - Test case:      — (Round 7)

- Failure state: A prepared data file goes missing after load
  - Trigger:        The file is deleted or unreadable while the scenario is in use
  - Recovery path:  Serve the last good picture. Mark it stale, show its age, name the file.
                    Never an empty screen, never an error page.
  - User message:   "Showing the picture from <time> — <file> is no longer readable."
  - Log event:      SCENARIO_DATA_UNREADABLE with scenario_id, file_name, last_good_at
  - Test case:      — (Round 7)

- Failure state: An asset cannot be scored
  - Trigger:        Missing or contradictory inputs for one asset
  - Recovery path:  Show the asset as UNSCORED in the ranking, with the reason it could not
                    be scored. NEVER omit it, and NEVER give it a low score.
  - User message:   "Not scored — <reason>." shown in place of a rank.
  - Log event:      ASSET_SCORING_FAILED with scenario_id, asset_id, reason
  - Test case:      — (Round 7)
```

**The third one is the most dangerous failure in this product.** An asset dropped from the
ranking, or defaulted to a low score, is indistinguishable on screen from an asset that is
genuinely safe — and the consequence is a crew not sent to something that failed. Silence must
never be readable as safety.

| Error state | Recovery path | What to test |
|---|---|---|
| Oversize or wrong-type upload | Refuse before parsing, naming the file. | An oversize file creates no scenario row and writes no file to disk. |
| Scenario parse fails partway | Abandon the whole load; previously loaded storms still rank. | A file valid for three of five inputs creates nothing. |
| Prepared file missing after load | Last good picture, marked stale and dated, file named. | Every screen stays readable and non-empty. |
| Asset cannot be scored | Rendered as unscored with a reason. | The asset appears in the list and is not ranked low. |
| Wrong credentials | Safe message that does not reveal which field was wrong. | A wrong email and a wrong password give identical output. |
| Expired session | Return to sign-in, preserving the intended destination. | A protected route redirects rather than erroring. |
| Database write fails on a decision | No success shown; the operator's note kept on screen. | A simulated failure never shows a recorded decision and never loses the note. |

---

## 4. Timeout rules

| Operation | Maximum wait |
|---|---|
| Scenario upload (accepting the bytes) | Bounded; the number waits on Q-017's file sizes |
| Scenario parse job | Bounded; on expiry the load fails whole, as above |
| Any read request | Bounded well inside REQ-NF-001's limits — a read that hangs is worse than a read that fails, because the operator waits instead of acting |
| Database write | Bounded; a timeout is reported as a failure, never as a success |

## 5. Retry rules

| Decision | Rule |
|---|---|
| Timeout | Set a maximum wait so the system never hangs forever. |
| Retry count | Limit retries. Do not retry endlessly. |
| Retry delay | Wait briefly before retrying instead of hammering the service. |
| Idempotency | Only retry operations that will not create duplicate harmful effects. |
| Stop condition | Define when the system gives up and reports a controlled failure. |

| Operation | Safe to retry? | Max retries | Delay | On give-up |
|---|---|---|---|---|
| Scenario upload, by the person | Yes | manual only | — | Nothing partial remains; no scenario is created |
| Scenario parse, automatically | **No** | 0 | — | Load fails whole, names the file, loaded scenarios untouched |
| Decision write | **No** | 0 | — | Error shown, the operator's note kept, no row written |
| Read request | Yes | 1, client-side | 1 s | Last good picture with the staleness banner |

> Uncontrolled retry logic creates new problems: duplicate records, hidden failures,
> and hammered dependencies.

**Why the parse is never retried automatically:** a malformed file is a fact about the file, not
a transient condition. Retrying turns a fast, legible failure into a slow one, and during a
storm the admin needs to know within seconds that the storm did not load.

**Why a decision write is never retried:** a retry that succeeded twice would be two audit rows
for one human decision, and BR-004 forbids removing either.

## 6. Background job and queue rules

| Requirement | Definition |
|---|---|
| Job name | `parse_prepared_scenario` |
| Trigger | An upload whose size and type have already been accepted |
| Input data | The stored upload identifier and the scenario metadata. **Never the file contents in the job payload.** |
| Retry rule | None, for the reason above. |
| Failure state | `failed`, with the failing file and the stage named. No scenario is created. |
| User visibility | The admin sees *uploading → parsing → ready* or *failed*, with the reason. One undifferentiated spinner would hide which stage broke, which is the difference between a fixable file and a broken system. |

## 7. Logging requirements

| Log requirement | Good practice |
|---|---|
| Event name | Clear names such as `AUTH_LOGIN_FAILED`, `JOB_RETRY_SCHEDULED`. |
| Severity | Use `info`, `warning`, `error`, `critical` consistently. |
| Request / correlation ID | Attach a request ID so related events can be traced. |
| Safe context | User ID, role, action — never secrets or raw credentials. |
| Failure reason | Error type or safe error code, not a sensitive dump. |
| Outcome | Whether the system recovered, retried, queued, or stopped safely. |

**Must never be logged:** passwords · tokens · reset links · full secret values · raw
payment data.

Three more join that list here, from Round 6's answers: full asset locations and connections
(log `asset_id`), household-level damage locations (aggregate to neighbourhood), and the
contents of any uploaded file.

**Structured log example (Ch. 24 §24.3)**
```json
{
  "level": "error",
  "event": "report_export_failed",
  "request_id": "REQ-20491",
  "user_id": "USER-118",
  "project_id": "PROJ-42",
  "reason": "database_timeout",
  "duration_ms": 12000,
  "recovery_action": "user_can_retry"
}
```

## 8. Data safety rules

| Rule | Definition |
|---|---|
| Partial write protection | A scenario load is one transaction. Either the whole storm exists or none of it does — there is no state in which three of five inputs are loaded, because a half-loaded storm ranks confidently on incomplete facts. |
| Duplicate protection | `(scenario_id, asset_id, forecast_revision)` is unique on `risk_scores`, so a re-run cannot produce two rankings for one revision. A damage report carries at most one repair job, so two reports at one location cannot become two crew trips. A second decision on one recommendation returns 409 rather than a second row. |
| Ordering guarantees | Forecast revisions are ordered and monotonic: applying a change writes revision *n+1* and never rewrites *n*. The decision record is ordered by `occurred_at` and is append-only, so its order is its history rather than a view of it. |

## 9. User-facing error messages

| Weak message | Better message | Why it is better |
|---|---|---|
| `DatabaseError: connection refused` | "We could not save your changes right now. Please try again." | Understandable; reveals no internals. |
| `Invalid request` | "Please enter a project name before saving." | Tells the user exactly what to fix. |
| `Unauthorized` | "You do not have permission to edit this project." | Explains without exposing security details. |
| `Job failed` | "Your report could not be generated. You can try again or contact support." | Gives a next action. |

Round 6 chose **a clear message and a retry option** as the standing pattern. One exception is
already specified and is not a departure from it: where a retry cannot help — a malformed file,
a decision already recorded — the message says what happened and what to do instead, rather than
offering a retry that will fail identically.

## 10. Monitoring / alerting notes

→ [`../ops/monitoring-plan.md`](../../07-ops/02-monitoring/monitoring-plan.md)

---

## Definition of done (Ch. 22 §22.8)

- [x] All expected failure states are handled.
- [x] Logs are safe and useful.
- [x] User-facing errors are clear.
- [ ] Tests cover normal behavior **and** failure behavior.

## Reliability review checklist (Ch. 22)

| Check | Yes / No |
|---|---|
| Each important feature has known failure states. | Yes |
| Each failure state has a recovery path. | Yes |
| Timeouts are defined for slow operations. | Partly — every operation has a bound, but three numbers wait on Q-017 |
| Retry rules are limited and safe. | Yes |
| Background jobs have status and failure handling. | Yes |
| Logs are useful and do not expose secrets. | Yes |
| User-facing error messages are clear and safe. | Yes |
| Tests cover both normal and failure behavior. | No — Round 7 writes them |

---

# ADDENDUM — Transactional Reliability

> Added from the architecture review. Source: Khononov, *Learning DDD*, Ch. 5 & 9.
> These two rules prevent the most common causes of production data corruption.

## A1. The dual-write problem — use the outbox

There is **no transaction spanning a database and a message bus.** This is broken:

```
commit task to database        ✅
publish TaskCreated to bus     💥  process dies here
```

The task exists; no consumer ever hears about it. Publishing *before* the commit is worse
— the event escapes and cannot be retracted if the commit then fails.

**The outbox pattern:**

1. Commit the state change **and** the outgoing events in the **same atomic transaction**
   (an `outbox` table, or events embedded in the document).
2. A relay reads newly committed events from the database.
3. The relay publishes them to the bus.
4. On success it marks them published.

| Guarantee | Consequence |
|---|---|
| **At-least-once** | If the relay dies after publishing but before marking, the message goes out **again**. Every consumer must be able to **deduplicate**. |

| Checklist | |
|---|---|
| Any event that must reliably leave a transaction uses the outbox | [ ] |
| Consumers deduplicate on a message ID | [ ] |
| Consumers tolerate out-of-order arrival | [ ] |
| The relay is monitored — a stalled relay is silent data loss | [ ] |

**Not applicable to version one, and the checklist above is unticked for that reason rather
than for being unmet.** There is no message bus and nothing leaves the process: one modular
monolith (ADR-001), one embedded store (ADR-002), no external services (Round 6). Every write
this system performs is inside one transaction against one database.

*Revisit when:* anything is published outside the process — the first live source-system
connection, or any notification path. On that day the dual-write problem arrives in full, and
this section is already written.

## A2. Transaction boundaries

| Rule | Meaning |
|---|---|
| **One aggregate instance per transaction** | Needing to commit two together is the signal your boundaries are wrong. |
| **Inside the boundary: strongly consistent** | Only data that must be consistent *right now* belongs inside. |
| **Outside: eventually consistent** | Reference other aggregates **by ID**, never by embedding. |
| **Optimistic concurrency is mandatory** | Carry a version; assert on write that the version read is the version being overwritten. Your store must support it. |

> If you are reaching for a saga to paper over operations that truly must be atomic,
> **your boundaries are wrong.** Fix the boundary; do not add the saga.

| Entity / aggregate | Transaction boundary | Consistency outside | Concurrency control |
|---|---|---|---|
| **Scenario** | The scenario, its assets, and one complete forecast revision of risk scores | Damage reports and repair jobs, by ID | Load is one transaction; a revision is one transaction |
| **Repair job** | One job and the damage reports attached to it | Assets and scenario, by ID | `version` field — two dispatchers claiming one job must not both win |
| **Decision record** | One row | Everything it describes, by type and id — never by foreign key | None needed; append-only, so there is nothing to overwrite |

**The decision record deliberately references its subject by type and id rather than by foreign
key.** That looks like a weaker design and is the correct one: an audit row must outlive the
thing it describes, and a foreign key would either block the deletion of a scenario or cascade
away the record of what was decided about it.

**A scenario load is one transaction on purpose**, even though it is large. The alternative —
committing each input file as it parses — is exactly the half-loaded storm §3 forbids, and it
would rank confidently on a third of the facts.

---

> Blueprint: blueprints/01-docs/07-security-and-reliability/reliability-specification.md
