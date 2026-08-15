# Environment Configuration

> Source: Ch. 23 §23.3 + Ch. 21 §21.6.
> Configuration = the values that change between environments **without changing the code**.
> Good configuration management prevents the most common AI-generated-code mistake:
> environment-specific values placed directly inside source files.

---

## Configuration table

| Config key | Purpose | Example value | Required in | Security note |
|---|---|---|---|---|
| `APP_ENV` | Identifies the current environment. | `local` / `test` / `production` | all | Not secret. |
| `SESSION_SIGNING_KEY` | Signs the server-side session (ADR-003). | long random value | all | **Secret** — never logged. Rotating it signs everyone out, which is the intended behaviour. |
| `SESSION_IDLE_TIMEOUT_MINUTES` | Idle expiry — implements SEC-A-002. | `240` (ADR-006) | all | Not secret. Still fails at startup if absent. |
| `SESSION_ABSOLUTE_MAX_HOURS` | Absolute session cap, regardless of activity (ADR-006). | `12` — one shift | all | Not secret. Fails at startup if absent. |
| `PASSWORD_HASH_COST` | Hashing cost factor. | tuned per host | all | Secret-adjacent; not logged. |
| `DATABASE_PATH` | Where the single embedded database file lives (ADR-002). | a path on the persistent disk | all | Not secret, and never logged or returned — a path is a hint about the host. |
| `SCENARIO_UPLOAD_DIR` | Where uploaded storm files are stored, under generated identifiers. | a path on the persistent disk | all | Same. |
| `SCENARIO_MAX_FILE_BYTES` | Upload limit per file. | `8388608` (8 MB) | all | Not secret. Roughly double the largest demo CSV. |
| `SCENARIO_MAX_TOTAL_BYTES` | Upload limit per scenario. | `10485760` (10 MB) | all | Demo scale is under 5 MB (Q-017). |
| `SCENARIO_PARSE_TIMEOUT_SECONDS` | Bound on the parse job. | `120` | all | Generous for ~7,500 CSV rows. |
| `LOG_LEVEL` | Controls logging detail. | `info` / `warn` / `error` | all | **Never `debug` in production** — request bodies contain asset locations. |

*Replace with your project's real values. Every key here must also exist in
[`../.env.example`](../../.) as a placeholder.*

**All keys now have values** (CHG-006), and **none of them has a default.** Q-017 and Q-021 are
answered, so the blanks are filled — but the startup failure stays. A default is what turns a
decision back into a guess the next time somebody deploys without reading this file.

**Three keys the blueprint expects are absent, and the absences are results:** there is no
`DATABASE_URL` (the store is a file), no `EMAIL_API_KEY` (no email service — Round 6), and no
`EXTERNAL_CALL_TIMEOUT_SECONDS` or `_MAX_RETRIES` (there are no external calls to time out).
If a key of any of those kinds ever appears here, an external dependency was added without a
decision — check the change log before adding it.

---

## Values by environment

| Key | Local | Test | Production |
|---|---|---|---|
| `APP_ENV` | `local` | `test` | `production` |
| `LOG_LEVEL` | `debug` | `info` | `info` |
| `SESSION_IDLE_TIMEOUT_MINUTES` | generous | short, to exercise SEC-A-002 | `240` (ADR-006) |
| `SESSION_SIGNING_KEY` | dev value | test value | **managed secret** |
| `DATABASE_PATH` | scratch file | fixture file | persistent disk |
| `SCENARIO_UPLOAD_DIR` | scratch dir | fixture dir | persistent disk |
| Scenario size limits | generous | **at the real limit**, so STEST-006 has something to breach | 8 MB / 10 MB |

**The test row for the session timeout is the useful one.** A test environment with the same
generous timeout as local can never exercise expiry, so SEC-A-002 goes untested by accident
rather than by decision.

---

## Rules

- **Never hardcode** an environment-specific value in source (Ch. 23 §23.3).
- **Never commit** real secrets — placeholders only in documentation (Ch. 21 §21.6).
- Missing or invalid configuration must **block deployment**, not fail silently at runtime
  (Ch. 28 §28.12).
- A secret that appears in a log is an incident: purge it, rotate the value, and fix the
  log call.
- Every config key is documented here **before** the code reads it.

**The third rule is stronger here than usual and worth reading as written:** *block*, not
*default*. Every value now has an answer, and **none of them has a fallback in code.** An
implementation that supplies a sensible default has converted a recorded decision back into a
guess — and a sensible default is exactly what an agent produces when the specification does not
forbid it, which is why TASK-001's stop condition still names it.

---

## Secret inventory

| Secret | Where configured | Rotation owner | Last rotated | Must never appear in |
|---|---|---|---|---|
| `SESSION_SIGNING_KEY` | environment | [TODO: who rotates this secret? — see Q-026] | — | source, logs, error messages, client responses |
| `PASSWORD_HASH_COST` | environment | [TODO: who rotates this secret? — see Q-026] | — | source, logs, error messages |

**Two secrets, and that is the whole inventory.** CON-006 removed every paid service and Round 6
removed every external one, so there is no provider key to rotate and no database password to
protect. It is the clearest operational dividend of those two constraints, and it is worth
naming because a later external dependency would add rows here first.

---

## Pre-deploy configuration check

- [ ] Every key in `.env.example` has a real value set in the target environment.
- [ ] No secret is present in the repository history.
- [ ] `LOG_LEVEL` is not `debug` in production.
- [ ] Timeouts and retry limits are set (not defaulting to "forever").
- [ ] Feature flags are set intentionally for this release.

One more passes now; one still fails:

- [x] **The previously blank keys have real values** — session limits from ADR-006, scenario
      limits from Q-017. This check blocked every deployment until both questions were answered,
      which is the check doing its job rather than an obstacle.
- [ ] **The application was confirmed to refuse startup on a missing value** — tested, not
      assumed. It is the one behaviour standing between an open question and a silent default.

---

> Blueprint: blueprints/07-ops/01-deployment/environment-config.md
