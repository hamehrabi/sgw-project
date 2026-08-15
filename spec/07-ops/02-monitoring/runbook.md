# Operational Runbook

> Source: Appendix N ("Are known issues, user messages, and operational runbooks
> documented?") + Ch. 22 + Ch. 24.
> What to do when something breaks — written **before** you need it.

---

## Service facts

| Item | Value |
|---|---|
| Service name | SGW Resilience Platform |
| Repository / location | This repository; the specification is in `spec/` |
| Environments | local / test / production |
| Health endpoint | `/health` |
| Log location | Structured logs to stdout, collected from the container |
| Metrics dashboard | **None.** Round 8 chose logs plus error alerts, not dashboards |
| Error tracker | **None off-site.** Round 6 declined error tracking — it would send stack traces containing critical-infrastructure context outside SGW |
| On-call owner | [TODO — see Q-026] |
| Rollback approver | [TODO — see Q-026] |

**The two "None" rows are decisions, not gaps**, and they change how an incident is worked: you
have logs and alerts, not a dashboard to stare at. Start from the event name and the request id.

## Start / stop / restart

```
Start:    npm start            (or: docker start <container>)
Stop:     docker stop <container>
Restart:  docker restart <container>
Status:   curl -f <base-url>/health
Logs:     container logs, filtered by event name and request_id
```

---

## Incident procedure

1. **Confirm the signal.** What alerted? What is the evidence?
2. **Check the health endpoint** and the core user flow.
3. **Check recent changes.** Was there a deploy or migration in the window?
4. **Classify severity** (see table below).
5. **Decide: mitigate or roll back** → [`../ops/rollback-plan.md`](../01-deployment/rollback-plan.md)
6. **Communicate** if users are affected.
7. **Record** in [`../ops/maintenance-log.md`](../03-maintenance/maintenance-log.md)
   and [`../review/debugging-specification.md`](../../05-review/04-debugging/debugging-specification.md).

| Severity | Condition | Response time | Action |
|---|---|---|---|
| **Critical** | Data exposure, unauthorized access, total outage. | Immediate | Roll back; security review. |
| **High** | Core flow broken for many users; auth failing. | < 30 min | Investigate; roll back if not fixed quickly. |
| **Medium** | A secondary feature fails; job retries exhausted. | Same day | Fix forward with a task and test. |
| **Low** | Cosmetic or rare edge case. | Next cycle | Log as feedback. |

**Three conditions are Critical here that the generic table does not name**, and each is a
system that appears healthy:

| Condition | Why Critical |
|---|---|
| A ranked item was served with no reasons | BR-002 breached, and the store should have refused it. Something is writing around the constraint. |
| An asset is absent from a ranking with no UNSCORED entry | A crew may not be sent somewhere that failed. Nothing is down; the product is lying. |
| A mutation on `decision_records` succeeded | The audit trail is editable. Every record since the last verified deploy is now in question. |

**Step 3 has a project-specific first question: was there a *migration* in the window?** A
migration that dropped a trigger produces no error at all, and the third condition above is its
only symptom.

---

## Common failure playbooks

### Application will not start
- [ ] Check for missing/invalid environment variables (`environment-config.md`).
- [ ] Check the migration state — did a migration run partially?
- [ ] Check the last deploy log for build errors.

**Check the first item first, and expect it to be the answer.** Four required values have no
default by design — the session timeout and three scenario limits — and the application is
specified to refuse startup rather than guess. A refusal to start here is usually the safeguard
working, not a fault.

### High error rate after deploy
- [ ] Compare the error signature against the previous release.
- [ ] Check whether a rollback trigger threshold was crossed.
- [ ] Roll back; then diagnose from the failing test, not from guesswork.

### Slow responses
- [ ] Identify **which** user action is slow (Ch. 24 §24.5).
- [ ] Check for queries inside loops, overfetching, unbounded result sets.
- [ ] Compare against the target in `../tests/performance-tests.md`.

**The first suspect is a query inside the scoring loop.** Scoring iterates every asset in a
scenario; it is the only unbounded loop in the product. **Do not add a cache** —
`runtime-and-scale.md` §2 refuses one with reasons, and a cache introduced during an incident is
a correctness risk added under pressure.

### External dependency failing
- [ ] Confirm the timeout and retry limits are being applied.
- [ ] Confirm the failure path shows the user the specified safe message.
- [ ] Confirm queued/pending work is not lost.

**This playbook cannot apply.** There are no external dependencies (Round 6). If it ever does
apply, one was added without a decision — check the change log before debugging it.

### Background jobs stuck
- [ ] Check job status values and retry counts.
- [ ] Check whether failures are idempotent-safe to retry.
- [ ] Confirm users see the correct pending/failed status.

One job exists: the scenario parse. Its retry count is **zero by design** — a malformed file is
not a transient error. A parse "stuck" is either still running within its timeout, or it failed
and the admin should be seeing the failing file and stage rather than a spinner.

### A screen looks empty and nobody is sure whether that is correct
- [ ] Check whether the scenario loaded — `SCENARIO_PARSE_FAILED` in the window?
- [ ] Check whether the ranking computed — any `RANKING_DELIVERED` for that scenario?
- [ ] Check `ASSET_SCORING_FAILED` counts — is the list short because assets were dropped?
- [ ] Check the staleness banner state and `SCENARIO_DATA_UNREADABLE`.

**This playbook has no equivalent in the blueprint and is the one most likely to be needed.** It
is the incident that arrives as a question rather than an alert, and every step answers it from
the data rather than from the screen.

---

## Manual recovery procedures

| Situation | Procedure | Risk | Approver |
|---|---|---|---|
| A migration dropped an append-only trigger | Re-apply both triggers; audit every `decision_records` row written since the migration | The audit guarantee lapsed for that window and cannot be retroactively proven | [TODO: who approves this recovery? — see Q-026] |
| A scenario is corrupt but the platform is healthy | Delete the scenario and re-upload the prepared files | None — scenarios are re-derivable | [TODO: who approves this recovery? — see Q-026] |
| The database file is lost | → [`backup-and-recovery.md`](../01-deployment/backup-and-recovery.md) | Up to 24 hours of decision records, which cannot be reconstructed | [TODO: who approves this recovery? — see Q-026] |

---

## Do **not** do these during an incident

- Do not ask an AI agent to "fix everything" — work from evidence, one cause at a time
  (Ch. 19 §19.4).
- Do not deploy an unreviewed change to production to "try something."
- Do not disable a test or a validation rule to make an error disappear.
- Do not skip recording the incident once service is restored.

Three more, specific to this system, each of which would look like a reasonable emergency fix:

- **Do not drop a `decision_records` trigger to unblock a migration.** It removes BR-004's only
  enforcement and nothing will report it afterwards.
- **Do not give an unscorable asset a default score to make a screen look complete.** That is the
  failure, not the fix.
- **Do not restore the database file to undo a code problem.** It discards every decision
  recorded since the backup. Roll the code back; the data is a separate decision with a separate
  approver.

---

> Blueprint: blueprints/07-ops/02-monitoring/runbook.md
