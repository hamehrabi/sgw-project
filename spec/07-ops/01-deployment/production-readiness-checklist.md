# Production Readiness Checklist

> Source: Appendix N + Ch. 23 §23.8 + Ch. 28 §28.13.
> A feature is **not** production-ready just because it works locally. It must be
> configured, observable, recoverable, secure, and maintainable.

**Release:**
**Date:**
**Release owner:**

---

## Readiness areas (Appendix N)

| Area | Readiness questions | Status |
|---|---|---|
| Requirements | Do released behaviors match approved requirements and acceptance criteria? | Not started / Ready / Blocked |
| Tests | Have unit, integration, end-to-end, security, and regression tests passed? | |
| Configuration | Are environment variables documented and separated by environment? | |
| Secrets | Are secrets stored outside source code? | |
| Build | Does the production build complete successfully? | |
| Database | Are migrations reversible or safely recoverable? | |
| Security | Have authentication, authorization, validation, and secrets been reviewed? | |
| Reliability | Are timeouts, retries, recovery paths, and background jobs specified? | |
| Monitoring | Are logs, metrics, traces, and alerts available for critical workflows? | |
| Rollback | Is there a clear rollback or roll-forward plan? | |
| Support | Are known issues, user messages, and operational runbooks documented? | |

---

## What would block a release today

Filled in now, against the specification rather than against code, so the blockers are known
before anyone is under time pressure to wave them through.

| Area | Verdict today | Why |
|---|---|---|
| Requirements | **Blocked** | REQ-NF-006 (accessibility) has no design link and no test — Q-013 was never answered. It is a requirement in name only, and the honest fix is to answer it or move it to non-goals. |
| Configuration | **Blocked** | Four required values have no value: the session timeout (Q-021) and three scenario limits (Q-017). The application is specified to refuse startup rather than default them, so this blocks by design. |
| Database | Ready in plan | Every migration is reversible and schema-first. **Untested** — no migration has been run. |
| Security | Ready in plan | 12 controls, each with acceptance criteria; two asserted below the application layer. No second factor (Q-022) — a decision nobody has made. |
| Reliability | Ready in plan | Timeouts, retry rules, failure states and background-job behaviour are all specified. Three timeout numbers wait on Q-017. |
| Monitoring | Ready in plan | Signals and log events named. **Every owner is a `[TODO]`** — Q-026. |
| Rollback | Ready in plan | Triggers written, three pre-authorised. **No rollback owner named** — Q-026. |
| Support | **Blocked** | A restore has never been performed or timed, so the four-hour recovery objective is an aspiration. `backup-and-recovery.md` §5 is empty. |

**Four blockers, and only one of them is about code.** Two are unanswered questions, one is a
missing name, and one is a rehearsal nobody has run. All four can be closed before a single line
is written — which is the argument for filling this checklist now rather than at the release.

---

## Deployment checklist (Ch. 23 §23.8)

| Check | Question | Status |
|---|---|---|
| Requirements | Do released features match approved requirements? | |
| Tests | Do unit, integration, and key end-to-end tests pass? | |
| Configuration | Are required environment variables documented? | |
| Secrets | Are secrets stored outside source code? | |
| Build | Does the production build complete successfully? | |
| Migration | Are database changes planned and reversible where possible? | |
| Monitoring | Are logs and error checks available after deployment? | |
| Rollback | Is the rollback path clear before release? | |

---

## Deployment approval (Appendix N)

- [ ] The release owner has reviewed the final checklist.
- [ ] A **rollback owner is named**.
- [ ] Monitoring is active **before** users depend on the feature.
- [ ] The team knows what signals indicate failure.
- [ ] Specs are updated to match the deployed behavior.

---

## Final release review (Ch. 28 §28.13)

| Review area | Question | Evidence required | Decision |
|---|---|---|---|
| Requirements | Did we build what was requested? | Requirements document and traceability matrix. | Pass / Fix gaps |
| Behavior | Does the system do what the spec says? | Test results and review screens. | Pass / Improve |
| Security | Can users access only allowed data? | Permission tests and code review evidence. | Pass / **Block release** |
| Reliability | Does the system recover from common failures? | Retry, timeout, queue, and logging tests. | Pass / Add failure handling |
| Deployment | Can we release and roll back safely? | Deployment checklist and rollback plan. | Pass / Delay release |
| Maintenance | Will the spec stay current after release? | Feedback loop, monitoring, spec-drift process. | Pass / Assign owner |

**Requirements sits above Tests on purpose, and this project has a live case for why.** REQ-NF-006
has a requirement and no test. A suite reporting *all tests pass* would be true and meaningless
about it, because there is no test to fail. A release reviewed on test results alone would ship
with an untested accessibility requirement and nobody would notice.

### Three additional review rows for this system

| Review area | Question | Evidence required | Decision |
|---|---|---|---|
| **The core promise** | Does every rank on every screen carry its reasons? | ATEST-004 passing, plus a screenshot | Pass / **Block release** |
| **The audit guarantee** | Does the database refuse an `UPDATE` on `decision_records`? | STEST-008 passing, asserted against the database | Pass / **Block release** |
| **The absence guarantee** | Is there any outbound path to a system controlling the grid or water? | STEST-010: zero | Pass / **Block release** |

All three block rather than warn, and all three are cheap to check. They are the three claims
the platform is sold on, and each is the kind that stays true right up until nobody checks it.

---

## Post-release smoke test

Run against the **deployed** system, not localhost.

1. Sign in as a test user.
2. Create the primary entity.
3. Add a child record.
4. Perform the core action.
5. Trigger the main failure path and confirm the safe message.
6. Confirm logs and audit events exist.
7. Confirm monitoring shows no critical errors.

**Evidence captured:**

---

## Sign-off

| Role | Name | Date | Decision |
|---|---|---|---|
| Release owner | | | Approve / Hold |
| Rollback owner | | | Acknowledged |
| Security reviewer | | | Pass / Block |

---

> Blueprint: blueprints/07-ops/01-deployment/production-readiness-checklist.md
