# Monitoring Plan

> Source: Ch. 24 (Monitoring, Maintenance, and Spec Drift) + Ch. 30 §30.2.
> Define monitoring **in the spec, before deployment**. Adding monitoring only after a
> failure is a beginner mistake.

> **Production is not the end.** It is where your software begins meeting real users,
> real traffic, real errors, and real maintenance pressure.

**Appetite: structured logs plus error alerts** (Round 8). Not full metrics, tracing and
dashboards — that is a project of its own and there is nothing to trace across, since version
one has no external services.

---

## 1. What to monitor (Ch. 24 §24.2)

Start with the features that matter most: login, payments, dashboards, uploads,
background jobs, API calls, and anything connected to user trust.

| Area | Question it answers | Signal | Trigger | Response | Owner |
|---|---|---|---|---|---|
| Availability | Can users reach the system? | External check on the health endpoint | any non-200 | Investigate; roll back if release-related | [TODO: who owns this signal? — see Q-026] |
| Availability | Is the process serving? | 5xx rate | > 2% over 5 min | Roll back (rollback-plan §4) | [TODO: who owns this signal? — see Q-026] |
| Correctness | **Is any ranking being served without reasons?** | Count of ranked items with an empty `reasons` array | **any occurrence** | **Roll back immediately.** BR-002 has been breached and the store should have refused it | [TODO: who owns this signal? — see Q-026] |
| Correctness | **Are assets failing to score?** | `ASSET_SCORING_FAILED` count per scenario | any rise against the previous load of the same storm | Investigate the loader before the scorer — the inputs changed shape | [TODO: who owns this signal? — see Q-026] |
| Correctness | Did a scenario load fail? | `SCENARIO_PARSE_FAILED` | any | Tell the admin which file and stage; no scenario was created | [TODO: who owns this signal? — see Q-026] |
| Correctness | Is the picture stale? | `SCENARIO_DATA_STALE` age | beyond the age the banner claims | Investigate the file; the banner must not under-report | [TODO: who owns this signal? — see Q-026] |
| Performance | Is the re-rank usable? | Time to updated ranking | beyond **5 s for 220 assets** (REQ-NF-001) | Profile the scoring pass first | [TODO: who owns this signal? — see Q-026] |
| Errors | What is breaking? | Error count and rate by event | rising | Group before acting; ten reports of one bug is one bug | [TODO: who owns this signal? — see Q-026] |
| Usage | **Are reasons being read?** | Ratio of decisions taken to `ReasonPanel` opens | falling | **Not an alert — the headline product signal.** It is success metric 3, and a fall means over-trust | Product owner |
| Security | Sign-in under attack? | `AUTH_LOGIN_FAILED` per account | ≥ 5 in 10 min | Rate limit fires (SEC-A-005); review if repeated | [TODO: who owns this signal? — see Q-026] |
| Security | Probing? | `AUTHZ_DENIED` spike | rising | Review actor and endpoint | [TODO: who owns this signal? — see Q-026] |
| Security | **Was the audit trail touched?** | Any refused `UPDATE`/`DELETE` on `decision_records` | **any occurrence** | **Critical.** Something tried. The trigger held; find out what issued it | [TODO: who owns this signal? — see Q-026] |

**Three rows here are not in any generic monitoring plan, and they are the ones worth having.**
A ranking without reasons, an asset that failed to score, and an attempt on the audit trail are
each invisible to availability and error-rate monitoring — the system is up, requests succeed,
and the product is quietly failing at the three things it exists to do.

**The usage row is the one to read weekly rather than alert on.** If operators stop opening the
reasons, nothing breaks and nothing errors — and assumption A3 has failed in the dangerous
direction.

## 2. Logging and observability (Ch. 24 §24.3)

Logs are the **messages**. Observability is the ability to use those messages *with*
metrics, traces, and alerts to understand the system.

| Log type | Use it when | What to include |
|---|---|---|
| Info | A normal important event occurs. | Operation name, request ID, status, relevant object ID |
| Warning | Something unusual happens but the system recovers. | Condition, recovery action, affected workflow |
| Error | A workflow fails or produces an unexpected result. | Error message, stack trace, request ID, user-safe context |
| Audit | A sensitive action occurs. | Actor, action, target, time, permission result |
| Performance | A task or request is slow. | Duration, endpoint, query or job type, threshold exceeded |

**The audit row has a home other than the log here**, and the distinction matters: recommendations
and human decisions go to `decision_records`, which is append-only and is *evidence*. Logs are
operational and are rotated. Never rely on a log line as the record of a decision, and never put
a decision record's contents into a log.

**Structured log example**
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

> A useful log tells you what happened, where, and which request or user action caused it.
> A noisy log repeats low-value information until important signals become hard to find.

**Never log:** passwords · tokens · reset links · full secret values · raw payment data.

Plus, on this system: **full asset locations and connections** (log `asset_id`),
**household-level damage locations** (aggregate to neighbourhood — REQ-NF-007), and **the
contents of an uploaded file**.

### The events this system emits

| Event | Level | Context fields |
|---|---|---|
| `AUTH_LOGIN_SUCCESS` | info | request_id, user_id |
| `AUTH_LOGIN_FAILED` | warning | request_id, user_id, attempt_count |
| `AUTH_RATE_LIMITED` | warning | request_id, user_id, retry_after |
| `SESSION_EXPIRED` | info | request_id, user_id |
| `AUTHZ_DENIED` | warning | request_id, user_id, role, endpoint |
| `SCENARIO_UPLOAD_ACCEPTED` | info | request_id, user_id, scenario_name |
| `SCENARIO_UPLOAD_REFUSED` | warning | request_id, user_id, file_name, reason (size / type) |
| `SCENARIO_PARSE_FAILED` | error | request_id, scenario_name, file_name, stage |
| `SCENARIO_DATA_UNREADABLE` | error | scenario_id, file_name, last_good_at |
| `SCENARIO_DATA_STALE` | warning | scenario_id, age_minutes |
| `ASSET_MATCH_NEEDS_REVIEW` | info | scenario_id, asset_id, external_ids |
| `ASSET_SCORING_FAILED` | error | scenario_id, asset_id, reason |
| `RANKING_DELIVERED` | info | request_id, scenario_id, forecast_revision, item_count, scoring_rule_version |
| `DECISION_RECORDED` | info | request_id, user_id, decision_record_id, kind |
| `DECISION_ALREADY_RECORDED` | warning | request_id, recommendation_id |
| `DECISION_MUTATION_REFUSED` | **critical** | request_id, statement_kind |
| `DB_WRITE_FAILED` | error | request_id, operation, duration_ms |

`RANKING_DELIVERED` carries `scoring_rule_version` for a reason: Q-025 makes weight changes the
expected activity, and a ranking that cannot say what scored it cannot be reproduced or audited.

## 3. Error tracking (Ch. 24 §24.4)

Group failures so you see **patterns**, not ten disconnected reports of the same bug.

| Error condition | Capture | Severity | Response |
|---|---|---|---|
| A valid user cannot authenticate. | Request ID, user ID, auth step, error class | **High** | Investigate immediately; protect account access. |
| A core job fails after timeout. | Job ID, duration, timeout value | Medium | Check queue, database, retry logic. |
| Unauthorized user reaches a restricted endpoint. | Actor, endpoint, permission result | **Critical** | Review authorization rule and security logs. |
| External API call fails repeatedly. | Provider, status code, retry count | Medium | Apply fallback or degrade gracefully. |
| **A mutation on `decision_records` was refused.** | Request ID, statement kind | **Critical** | The trigger held. Find what issued it — either a code path that must not exist, or a direct database session. |
| **An asset was not scored.** | Scenario, asset, reason | **High** | Not an outage. A crew may not be sent somewhere that needed one. |

The fourth row does not apply — there is no external API. It stays visible so its absence is a
recorded fact rather than an oversight.

## 4. Performance monitoring (Ch. 24 §24.5)

Begin with a specific question: *which user action is slow, how slow is it, what is the
target, and what part of the system is likely responsible?* Do not begin with random
optimization.

| Workflow | Metric | Target | Action if exceeded |
|---|---|---|---|
| Re-rank after a forecast change | Time to updated ranking on screen | **unset — Q-012** | Profile the scoring pass first; it is the only unbounded loop. Do **not** add a cache — `runtime-and-scale.md` §2 refuses one, with reasons. |
| New damage report to the board | Time to appear | **unset — Q-012** | Check for an unindexed scan on `damage_reports(scenario_id, status)`. |
| Scenario parse | Job completion time | **unset — Q-017** | It is a background job; a slow parse is visible to the admin as *parsing*, not as a hang. |

**All three targets are unset, and monitoring them without a target is still worth doing.**
Recording the numbers from the first real prepared dataset is how Q-012 gets answered — with a
measurement rather than another estimate.

## 5. User feedback loop

→ [`../review/feedback-register.md`](../../05-review/01-logs/feedback-register.md)

Monitoring tells you what the system is doing; feedback tells you how it *feels*. A system
can have zero errors and still be confusing.

**On this product the gap is wider than usual.** The two failures that would end the project —
*"I'd have sent them there anyway"* and *"I just take the top of the list"* — produce no error,
no alert and no metric. Monitoring cannot see either. The feedback register is the only
instrument that can.

---

## Monitoring and maintenance specification (Ch. 24)

| Section | What to define |
|---|---|
| Feature or workflow | Name the production workflow being monitored. |
| Monitoring signals | Logs, metrics, errors, performance values, user feedback sources. |
| Health expectations | What healthy behavior looks like. |
| Alert conditions | When a signal should trigger attention. |
| Owner or reviewer | Who reviews the signal or issue. |
| Spec update rule | When the specification must be updated. |
| Test update rule | When tests must be added or changed. |
| Release follow-up | What must be checked after the next deployment. |

**Every owner in this file is a `[TODO]` pointing at Q-026.** An alert with no owner is an alert
nobody answers, and three of the conditions above are marked *roll back immediately*. Naming the
person is not administrative tidiness; it is the difference between a plan and a response.

---

> Blueprint: blueprints/07-ops/02-monitoring/monitoring-plan.md
