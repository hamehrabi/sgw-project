# deployment-checklist.md — Deployment Checklist

> **Purpose (Ch. 4 §4.3):** The `/ops` folder stores deployment and maintenance notes.
> This is the release gate you run every time.
> **Sources:** Ch. 16 §16.9, Ch. 23 §23.8, Appendix N.

**Detail documents in this folder**

| Document | Covers |
|---|---|
| [`deployment-plan.md`](deployment-plan.md) | Full release plan template (Ch. 23 §23.9). |
| [`cicd-pipeline.md`](cicd-pipeline.md) | Install → lint → test → build → smoke gates. |
| [`database-migration-plan.md`](database-migration-plan.md) | Reversibility, backfill, deploy order. |
| [`rollback-plan.md`](rollback-plan.md) | Stable version, triggers, owner, comms. |
| [`production-readiness-checklist.md`](production-readiness-checklist.md) | Full Appendix N pass + sign-off. |
| [`environment-config.md`](environment-config.md) | Every config key and its security note. |
| [`runbook.md`](../02-monitoring/runbook.md) | What to do when something breaks. |

> **No container file ships with this workspace.** Packaging is a decision about your stack,
> not a template — write the image definition next to the code and record what it assumes
> here, under *Deployment readiness*. A `Dockerfile` copied from a specification kit is the
> one you never read.

> **Practical rule (Ch. 23):** do not ask an AI agent to "make this production ready" after
> the code is already messy. Give the agent deployment requirements **before**
> implementation begins.

**What the image must assume**, recorded here as the blueprint asks: one container on a cloud VM,
with a **persistent disk** for the database file and the scenario uploads. That is not a
preference — ADR-002 puts the whole store in one file, so an ephemeral filesystem loses every
decision record on restart.

---

## Release identity

| Field | Value |
|---|---|
| Release name / version | |
| Date | |
| Release owner | |
| **Rollback owner** | |
| Requirements included | REQ-### |

---

## Pre-release checklist (Ch. 23 §23.8)

| Check | Question | Status |
|---|---|---|
| Requirements | Do released features match approved requirements? | Not started / Ready / Blocked |
| Tests | Do unit, integration, and key end-to-end tests pass? | |
| Configuration | Are required environment variables documented? | |
| Secrets | Are secrets stored outside source code? | |
| Build | Does the production build complete successfully? | |
| Migration | Are database changes planned and reversible where possible? | |
| Monitoring | Are logs and error checks available after deployment? | |
| Rollback | Is the rollback path clear before release? | |
| **Fitness functions** | Do FF-001 to FF-006 run, and pass? | |
| **Append-only triggers** | Do both `decision_records` triggers exist *after* migrations? | |

**The last two rows are added and neither is optional.** Fitness functions are a separate gate
from tests — one proves behaviour, the other proves the structure has not moved — and the
triggers are BR-004's only enforcement, which a migration can remove without anything noticing.

## Deployment readiness (Ch. 16 §16.9)

- [ ] Requirements were satisfied.
- [ ] Technical design was followed.
- [ ] Tests passed.
- [ ] No unrelated files were changed.
- [ ] Configuration values are known.
- [ ] Database changes are documented.
- [ ] Error handling is acceptable.
- [ ] Rollback steps are written.
- [ ] Monitoring or manual checks are planned.

> **Never deploy a feature you cannot explain, test, and roll back.** If you cannot
> describe what changed, why it changed, how it was tested, and what you will do if it
> fails, the feature is not ready.

---

## Environments (Ch. 23 §23.2)

| Environment | Purpose | Typical data | Release rule |
|---|---|---|---|
| Local | You build and run the app while developing. | Small fake data | Fast changes are allowed. |
| Test | You run automated checks and verify behavior. | Controlled sample data | Only tested changes move forward. |
| Production | Real users depend on this. | Real user data | Only reviewed, deployable changes enter. |

> An environment is not just a server. It is a **promise about how carefully code should be
> handled** there. Local can be flexible. Production must be controlled.

---

## Deployment steps

```
1. Install dependencies.
2. Run linting and static checks.
3. Run unit and integration tests.
4. Build the production application.
5. Apply database migrations.
6. Start the application.
7. Run a smoke test against the health endpoint.
8. Monitor logs for the first release window.
```

For this system, with the two insertions from `deployment-plan.md`:

```
3a. Run the six fitness functions. Separate stage; a failure blocks.
5a. Confirm both decision_records triggers exist — attempt an UPDATE, require refusal.
6a. Confirm the application refused to start with any required config value missing.
```

Commands for this project:
```
Install:  npm ci
Lint:     npm run lint
Test:     npx vitest run  &&  npx playwright test
Fitness:  npm run fitness   # FF-001..FF-006
Build:    npm run build
Migrate:  npx drizzle-kit migrate
Start:    npm start
Smoke:    end-to-end-tests.md, production smoke section
```

---

## Post-deploy smoke test

1. Sign in as a test user.
2. Create the primary entity.
3. Add a child record.
4. Perform the core action.
5. Trigger the main failure path and confirm the safe message.
6. Confirm logs and audit events exist.
7. Confirm monitoring shows no critical errors.

**As it applies here:** sign in · upload a small prepared storm · confirm it ranks and that
**every rank carries reasons** · accept one recommendation · **remove one of its data files and
confirm the staleness banner appears rather than a blank screen** · confirm the decision record
holds both the recommendation and the acceptance · confirm no critical error.

Step 5 is the one worth running against the deployed system rather than only in test: the
failure it exercises is the one that only ever happens mid-storm.

**Evidence captured:**

---

## Deployment approval (Appendix N)

- [ ] The release owner has reviewed the final checklist.
- [ ] A rollback owner is named.
- [ ] Monitoring is active **before** users depend on the feature.
- [ ] The team knows what signals indicate failure.
- [ ] Specs are updated to match the deployed behavior.

| Role | Name | Date | Decision |
|---|---|---|---|
| Release owner | | | Approve / Hold |
| Rollback owner | | | Acknowledged |
| Security reviewer | | | Pass / Block |

**Two rows cannot be signed today for reasons that are not about readiness.** No name exists for
any role (Q-026), and three rollback triggers in `rollback-plan.md` are marked *roll back
immediately* — which requires somebody pre-authorised to do it without waiting for approval.

---

> Blueprint: blueprints/07-ops/01-deployment/deployment-checklist.md
