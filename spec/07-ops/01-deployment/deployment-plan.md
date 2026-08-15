# Deployment Plan

> Source: Ch. 23 §23.9 (Deployment Planning Template) + Ch. 16 §16.9.
> **Practical rule:** do not ask an AI agent to "make this production ready" after the code
> is already messy. Give the agent deployment requirements **before** implementation begins.

---

## Template (Ch. 23)

```
1.  Release name:
2.  Release goal:
3.  Approved requirements included:
4.  Environments:
      - Local:
      - Test:
      - Production:
5.  Required configuration values:
6.  Secrets that must not appear in code:
7.  Build command:
8.  Test command:
9.  Database migration plan:
10. Deployment steps:
11. Smoke test:
12. Monitoring checks:
13. Rollback steps:
14. Final approval checklist:
```

---

## The plan for version one

```
1.  Release name:  SGW Resilience Platform v0.1.0 — the P0 probe
2.  Release goal:  An operations manager can load a prepared storm, read a ranked risk
                   list with reasons, and record a crew placement; a dispatcher can work
                   a shared damage board. Every recommendation and decision is recorded
                   and cannot afterwards be altered.
3.  Approved requirements included:
       REQ-F-001 to REQ-F-010, REQ-NF-002, REQ-NF-003, REQ-NF-005,
       REQ-R-001 to REQ-R-003, BR-001 to BR-005,
       SEC-A-001 to SEC-A-005, SEC-Z-001 to SEC-Z-006
       NOT included: REQ-NF-001 (limits unset — Q-012), REQ-NF-004 (same),
       REQ-NF-006 (no standard — Q-013), REQ-NF-007 in part (CON-003 — Q-007)
4.  Environments:
       Local:      the container, a scratch database file, a small prepared scenario
       Test:       the same container image, a fixture carrying all seven data defects
       Production: one container on a cloud VM, persistent disk for the database file
                   and the scenario uploads
5.  Required configuration values:
       APP_ENV, SESSION_SIGNING_KEY, SESSION_IDLE_TIMEOUT_MINUTES, PASSWORD_HASH_COST,
       DATABASE_PATH, SCENARIO_UPLOAD_DIR, SCENARIO_MAX_FILE_BYTES,
       SCENARIO_MAX_TOTAL_BYTES, SCENARIO_PARSE_TIMEOUT_SECONDS
       Four of those have NO VALUE YET: the session timeout (Q-021) and the three
       scenario limits (Q-017). The application must fail at startup, named, rather
       than default them.
6.  Secrets that must not appear in code:
       SESSION_SIGNING_KEY, PASSWORD_HASH_COST.
       There is NO database credential — the store is a file (ADR-002), so access to it
       is filesystem access. There is no API key of any kind, because there is no
       external service (Round 6).
7.  Build command:   npm run build  (Next.js / TypeScript — ADR is Q-027's answer)
8.  Test command:    the suite AND the six fitness functions. Not the suite alone.
9.  Database migration plan:
       → database-migration-plan.md. One rule outranks the rest: the two
       decision_records triggers must exist after every migration run (ADR-004).
10. Deployment steps: below.
11. Smoke test:      end-to-end-tests.md, production smoke section.
12. Monitoring checks: monitoring-plan.md — structured logs plus error alerts.
13. Rollback steps:  rollback-plan.md.
14. Final approval:  production-readiness-checklist.md.
```

---

## 3. Environments (Ch. 23 §23.2)

| Environment | Purpose | Typical data | Release rule |
|---|---|---|---|
| Local | You build and run the app while developing. | Small fake data | Fast changes are allowed. |
| Test | You run automated checks and verify behavior. | Controlled sample data | Only tested changes move forward. |
| Production | Real users depend on this. | Real user data | Only reviewed, deployable changes enter. |

> An environment is not just a server. It is a **promise about how carefully code should be
> handled** in that place. Local can be flexible. Production must be controlled.

**The test environment carries a specific obligation here:** its data is the fixture with all
seven measured defects injected on purpose. A test environment seeded with clean data would pass
every check and prove nothing, because the whole loader exists to survive dirty data.

## 4. Configuration

→ [`../ops/environment-config.md`](environment-config.md) · [`../.env.example`](../../.)

| Config key | Purpose | Example value | Security note |
|---|---|---|---|
| `APP_ENV` | Identifies the current environment. | local / test / production | Not secret. |
| `SESSION_SIGNING_KEY` | Signs the server-side session. | long random value | **Secret.** Never logged. Rotating it signs everyone out — intended, not a side effect. |
| `SESSION_IDLE_TIMEOUT_MINUTES` | Idle expiry (SEC-A-002). | **unset — Q-021** | Not secret. **Fail at startup if absent.** |
| `PASSWORD_HASH_COST` | Hashing cost factor. | tuned per host | **Secret-adjacent.** Not logged. |
| `DATABASE_PATH` | Where the single database file lives. | a path on the persistent disk | Not secret, and never logged — the path hints at the host. |
| `SCENARIO_UPLOAD_DIR` | Where uploaded storm files are stored. | a path on the persistent disk | Same. |
| `SCENARIO_MAX_FILE_BYTES` | Upload limit per file. | **unset — Q-017** | Not secret. **Required once an upload path exists.** |
| `SCENARIO_MAX_TOTAL_BYTES` | Upload limit per scenario. | **unset — Q-017** | Same. |
| `SCENARIO_PARSE_TIMEOUT_SECONDS` | Bound on the parse job. | **unset — Q-017** | Same. |

## 5. Secrets that must not appear in code

- `SESSION_SIGNING_KEY`
- `PASSWORD_HASH_COST`

That is the whole list, and its shortness is a result rather than an oversight: CON-006 removed
every paid service and Round 6 removed every external one, so there is no API key, no SMTP
credential, and no database password to protect.

## 6. Build and test commands

```
Install:  npm ci
Lint:     npm run lint
Test:     npx vitest run && npx playwright test
Gate:     npm run gate  — the suite PLUS FF-001..FF-006 PLUS the trigger check.
          This is what "all checks" means.
Build:    npm run build  — then the container image
Start:    npm start
Smoke:    end-to-end-tests.md, production smoke section
```

**Every command is a `[TODO]` because CON-001 mandates no technology and Round 8 chose a
deployment shape rather than a stack.** Writing plausible commands here would read as decisions.
They are filled in by the pull request that completes TASK-001 — and the `Gate` line is the one
that must not quietly become the same as `Test`.

## 7. Database migration plan

→ [`database-migration-plan.md`](database-migration-plan.md)

## 8. Deployment steps

1. Install dependencies.
2. Run linting and static checks.
3. Run unit and integration tests.
4. Build the production application.
5. Apply database migrations.
6. Start the application.
7. Run a smoke test against the health endpoint.
8. Monitor logs for the first release window.

**Two steps are inserted for this system:**

- **After step 5: confirm both `decision_records` triggers exist.** BR-004's only enforcement
  lives there (ADR-004), and a migration can drop one with nothing in the suite noticing.
- **After step 6, before step 7: confirm the application refused to start on any missing
  configuration value.** Four required values have no default (Q-017, Q-021), and a container
  that starts with a guessed session timeout is a container that answered an open question.

## 9. Smoke test

→ [`../tests/end-to-end-tests.md`](../../03-tests/02-functional/end-to-end-tests.md) (Production smoke test)

## 10. Monitoring checks

→ [`monitoring-plan.md`](../02-monitoring/monitoring-plan.md)

## 11. Rollback

→ [`rollback-plan.md`](rollback-plan.md)

## 12. Final approval

→ [`production-readiness-checklist.md`](production-readiness-checklist.md)

---

## Deployment readiness checklist (Ch. 16 §16.9)

- [ ] Requirements were satisfied.
- [ ] Technical design was followed.
- [ ] Tests passed.
- [ ] No unrelated files were changed.
- [ ] Configuration values are known.
- [ ] Database changes are documented.
- [ ] Error handling is acceptable.
- [ ] Rollback steps are written.
- [ ] Monitoring or manual checks are planned.

Every box is unticked because nothing has been built. **The fifth would fail today even if code
existed** — four required configuration values have no value, and both questions behind them are
open.

> **Never deploy a feature you cannot explain, test, and roll back.** If you cannot
> describe what changed, why it changed, how it was tested, and what you will do if it
> fails, the feature is not ready.

---

> Blueprint: blueprints/07-ops/01-deployment/deployment-plan.md
