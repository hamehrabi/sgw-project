# TASK-001: Sign in with two roles, and the application shell

> Source: Ch. 4 §4.5 (`TASK-001.md` starter) + Ch. 14 (agent-friendly task template) +
> Ch. 16 §16.5 (engineering task template).
> Copy to `TASK-###-short-name.md`. One task = one outcome.

---

**Task ID:** TASK-001
**Task title:** Sign in with two roles, and the application shell
**Priority:** P0
**Status:** Not started
**Assigned to:** AI agent

---

## Source requirement or spec section

REQ-NF-002 · REQ-R-001 · SEC-A-001, SEC-A-002, SEC-A-003, SEC-A-005 · SEC-Z-001 ·
ADR-001 (modular monolith) · ADR-002 (embedded store) · ADR-003 (email and password with
server-side sessions)

## Business reason

Every other task reads or writes scenario data, and every one of those reads must be refused
for a signed-out request. This is the thinnest vertical slice that exists — sign in, see an
empty shell — and it is the one that makes every later slice testable for who may see it.

## Goal

A person can sign in with an email and password, receive a server-side session, and reach an
application shell that shows their role. A signed-out request reaches no data route.

## Inputs

- `01-docs/07-security-and-reliability/security-specification.md` §1, §2 — SEC-A and SEC-Z rows
- `01-docs/06-api-and-data-design/api-specification.md` — the two auth endpoints
- `01-docs/06-api-and-data-design/database-design.md` §3 — the `users` table
- `01-docs/04-technical-spec/technical-spec.md` §2 — the modules and their import direction
- **ADR-008** — the frontend/backend split, and which module lives in which process
- `01-docs/04-technical-spec/frontend-component-spec.md` — `AppShell`
- `01-docs/04-technical-spec/runtime-and-scale.md` §1 — the login rate limit
- `spec/.env.example` — the configuration this task reads

## Expected files or components

**Two processes** (ADR-008). Backend: a FastAPI/Python service holding the `api`, `store`,
`scoring` and `loader` packages — this task creates the package skeleton, the `users` table and
its migration, and the two auth endpoints. Frontend: a Next.js/TypeScript app holding `views`,
with `AppShell` only. Exact paths are the agent's to choose inside each process; the **boundary
between them is not**, and the frontend never touches the store.

## Expected output

- The application starts and serves a health check.
- `POST /api/v1/auth/session` and `DELETE /api/v1/auth/session` behave as specified.
- A `users` table exists with the role check constraint from `database-design.md` §3.
- `AppShell` renders nothing until the role is known.
- Every data route — none of which exist yet — is refused for a signed-out request by a check
  that lives in the API layer, not in each handler.

## Step-by-step instructions

1. Create both processes: the FastAPI service with its four packages, and the Next.js app.
   Keep the import direction ADR-001 fixes; ADR-008 puts two of the modules across a process
   line, which makes it stronger, not weaker.
2. Add configuration loading from environment variables. **Fail at startup**, with a clear
   message, if a required value is absent — never at the first request during a storm.
3. Create the `users` table exactly as `database-design.md` §3 specifies, including
   `check role in ('admin','user')`.
4. Implement password hashing. Store the hash only.
5. Implement `POST /api/v1/auth/session`: validate, compare in constant time, create a
   server-side session, return no hash and no session internals.
6. Implement `DELETE /api/v1/auth/session`: end the session **server-side**.
7. Implement the session check as one thing in the API layer that every route passes through.
8. Implement the login rate limit: per account **and** per IP, returning 429 with `Retry-After`.
9. Build `AppShell`: role visible, no content until the role is known.

## Dependencies

None. This is the first task.

## Constraints / Boundaries

- Do not change unrelated files.
- Do not add unrequested features.
- Do not rename public interfaces unless this task explicitly requires it.
- Do not introduce a new dependency without approval.
- **Do not call OpenAI.** ADR-009's phrasing layer belongs to the scoring work, not to sign-in.
- **Do not add a third role.** Two exist (REQ-R-001), and the database refuses a third.
- **Do not add self-service registration.** Nobody creates their own account in this product.
- **Do not add a second factor.** Q-022 is answered: **none in version one**, TOTP at P1.
  Building one now implements a deferred decision, not an open one.
- **Do not implement password reset.** That is A-003, and it is admin-performed (CHG-004).

## Do not change

`decision_records` and its two append-only triggers — they do not exist yet and this task must
not create them. The scoring module — it does not exist yet and nothing here may anticipate it.
Anything under `01-docs/`: the specification is an input to this task, not an output of it.

## Acceptance check / Done criteria

1. A signed-out request to any route other than the health check and the sign-in endpoint
   returns 401 and no body containing project data.
2. A wrong email and a wrong password produce an **identical** response — same status, same
   body, same timing characteristics as far as a constant-time comparison provides.
3. Six failed attempts against one account within ten minutes return 429 with `Retry-After`,
   **including when each attempt arrives from a different address**.
4. No log line, response body, or error message contains a password, a hash, or a session value.
5. Signing out server-side makes the previously held session unusable on the next request.
6. Attempting to insert a user with a role other than `admin` or `user` is refused by the
   database.
7. The application fails at startup, with a named message, when a required configuration value
   is missing.

## Tests to run or create

> **Test rows are DEFINED in their test files (`03-tests/…`), and only there.** This table
> CITES them: the id and the file that owns it, never the scenario or expected result
> restated. A task that restates a test carries a second copy with nothing keeping the two in
> step — consistent on the day it is written, wrong the first time the owning file changes. A
> reviewer reads the id and opens the owning file. (`fitness-functions.md`'s register states
> the same rule for `FF-` ids, for the same reason.)

| Test ID | Defined in |
|---|---|
| STEST-001 | `03-tests/03-non-functional/security-tests.md` |
| STEST-002 | `03-tests/03-non-functional/security-tests.md` |
| STEST-003 | `03-tests/03-non-functional/security-tests.md` |
| STEST-004 | `03-tests/03-non-functional/security-tests.md` |
| UTEST-001 | `03-tests/02-functional/unit-tests.md` |

## Review checklist

- [ ] Code matches the source requirement.
- [ ] No unrelated feature was added.
- [ ] Tests pass.
- [ ] Error messages are clear and safe.
- [ ] Only approved files changed.
- [ ] Traceability matrix updated.

## Out of scope

- Password reset of any kind
- A second authentication factor
- Any scenario, asset, ranking, board, or decision behaviour
- Any styling beyond what makes the shell legible

## Stop condition

**Stop and ask** if any of these is true rather than proceeding:

- A required configuration value has no obvious meaning. **`SESSION_IDLE_TIMEOUT_MINUTES` is
  no longer one of them** — Q-021 is answered and ADR-006 sets 240 minutes idle, 12 hours
  absolute, both already in `.env.example`. Read both values; never hard-code either; still fail
  at startup if either is absent.
- The specification appears to require a third role, self-service registration, or an email.
  None of those exist here, and a reading that produces one is a misreading.
- Implementing the session check appears to require a change under `01-docs/`.

---

> Blueprint: blueprints/02-tasks/02-task-files/TASK-001.md
