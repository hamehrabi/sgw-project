# CI/CD Pipeline Plan

> Source: Ch. 23 §23.4.
> CI/CD is a **repeatable path that checks your code before release**. The concept does not
> depend on any one platform — focus on the workflow, not the hosted service.

**The question every pipeline answers:** *what must pass before the code is allowed to move
forward?*

---

## Stages

| Stage | Question it answers | Example command | Gate |
|---|---|---|---|
| Install | Can the project dependencies be installed? | `npm install` | No missing dependencies. |
| Lint | Does the code follow basic rules? | `npm run lint` | No blocking style or syntax errors. |
| Test | Does expected behavior still work? | `npm test` | All required tests pass. |
| Build | Can the app be packaged for release? | `npm run build` | Build completes without errors. |
| Migrate | Are schema changes applied safely? | `npm run migrate` | Migration tested on staging data. |
| Smoke test | Does the app start and respond? | `npm run smoke` | Basic endpoint or page works. |
| Verify | Are metrics, permissions, and logs correct? | manual + checklist | Smoke evidence captured. |

*Replace the example commands with your project's real ones.*

---

## Your pipeline

```
1. Install:   npm ci
2. Lint:      npm run lint          # eslint + prettier
3. Test:      npx vitest run       # unit + integration
4. FITNESS:   npm run fitness      # FF-001..FF-006.
              A SEPARATE STAGE, not part of Test.
5. Build:     npm run build        # then the container image
6. Migrate:   npx drizzle-kit migrate
7. TRIGGERS:  confirm both decision_records triggers exist, by attempting an UPDATE
              and asserting the database refuses it
8. Deploy:    npm start            # next start, one process
9. Smoke:     end-to-end-tests.md, production smoke section
10. Monitor:  first release window
```

**Two stages are inserted that the blueprint's list does not have**, and both exist because
something in this system can be silently undone.

**Stage 4 — fitness functions as their own stage.** The suite proves the features behave; the
fitness functions prove the structure has not moved. Folding them into `Test` is how FF-002 —
no view imports the scoring module — decays while every feature test stays green. They are
`Not wired yet` in the register today; TASK-010 wires them, and until it does this stage is a
manual check that the pipeline must not pretend to run.

**Stage 7 — the trigger check, after migrate and before deploy.** BR-004's only enforcement is
two triggers (ADR-004), a migration can drop one, and nothing else in the pipeline would notice.
Checking the schema is not enough: attempt the `UPDATE` and require the refusal.

---

## Quality gates by environment (Ch. 27 §27.9)

| Stage | Required action | Quality gate | Rollback trigger |
|---|---|---|---|
| Prepare | Confirm environment variables and data sources. | Config checklist complete. | Missing or invalid configuration. |
| Migrate | Apply database changes. | Migration tested on staging data. | Migration error or data mismatch. |
| Build | Run tests and create the deployment package. | All required tests pass. | Failing test or unsafe warning. |
| Release | Deploy with monitoring enabled. | Health checks and core route pass. | High error rate or broken core route. |
| Verify | Check data accuracy, permissions, and logs. | Smoke test evidence captured. | Data leak risk, wrong result, or severe performance issue. |

**The Prepare gate fails today, and will keep failing until two questions are answered.** Four
required configuration values have no value — the session timeout (Q-021) and the three scenario
limits (Q-017) — and `environment-config.md` requires the application to refuse startup rather
than default them. That is the gate working, not an obstacle to route around.

---

## Rules

- **Do not merge failing checks** (Appendix L).
- A test that is skipped to make the pipeline pass is a **finding**, not a fix.
- Migrations run *before* the code that depends on them (Ch. 23 §23.6).
- Secrets come from the environment, never from the repository.
- Every pipeline failure that reaches production becomes a new test
  (`../review/debugging-specification.md`).

**A sixth rule, specific to this pipeline: "all checks pass" means stages 3, 4 and 7.** A
pipeline that reports green having run only the test suite is making a claim nobody earned —
which is the exact failure `fitness-functions.md` exists to prevent, committed by the thing
meant to enforce it.

---

## Local-only alternative

You do not need a hosted platform to get the benefit. A single script that runs the same
stages in order gives you the same gate:

```bash
#!/usr/bin/env bash
set -e
echo "== install ==" && <install command>
echo "== lint ==="   && <lint command>
echo "== test ==="   && <test command>
echo "== build =="   && <build command>
echo "== smoke ==="  && <smoke command>
echo "ALL GATES PASSED"
```

`set -e` makes the script stop at the first failure — that is the gate.

**This is the right shape for this project.** CON-006 rules out a paid platform, and a script
that fails fast delivers every benefit that matters: the same stages, in the same order, blocking
the same merges. The version that ships here has two extra lines:

```bash
echo "== fitness ==" && <FF-001..FF-006>
echo "== triggers ==" && <attempt an UPDATE on decision_records; require refusal>
```

Without `set -e`, the script prints `ALL GATES PASSED` even when a stage failed. Without those
two lines, it prints it while the structure has drifted and the audit trail is editable.

---

> Blueprint: blueprints/07-ops/01-deployment/cicd-pipeline.md
