# Project Context Pack

> Source: Ch. 12 §12.8 + Appendix I.
> A **focused** package of project information for **one task**. Not the whole project.

> **Context pack rule:** give the agent enough context to succeed, but not so much that it
> loses the task. The best context pack is specific, traceable, and current.
>
> **Too little context** → the agent guesses. **Too much context** → the agent gets confused.

---

## Template (Ch. 12 §12.8)

```markdown
# Project Context Pack

## 1. Project Background
Project name:   [Name]
Purpose:        [What the system helps users do]
Primary users:  [User roles]
Current stage:  [Planning / building / testing / improving]

## 2. Current Task
Task:            [One focused task]
Expected output: [What should be created or changed]
Do not change:   [Files, schema, features, or decisions to protect]

## 3. Relevant Requirements
Requirement ID:        [REQ-###]
Requirement statement: [What the system must do]
Acceptance criteria:
- [Criterion 1]
- [Criterion 2]
- [Criterion 3]

## 4. Technical Decisions
Architecture rule: [Relevant architecture decision / ADR]
Data rule:         [Relevant database or model rule]
API rule:          [Relevant endpoint or contract rule]
Security rule:     [Relevant authentication or authorization rule]

## 5. File Map
[Show only the folders and files relevant to this task]

## 6. Coding Standards
- Keep functions small and readable.
- Validate all inputs.
- Return safe error messages.
- Add or update tests for changed behavior.

## 7. Tests to Run
- [TEST-### and expected outcome]

## 8. Review Rules
Before finishing, explain:
- What changed
- Which requirement was implemented
- Which tests should pass
- Any assumption made
```

---

## The pack for TASK-001 — ready to hand over

```markdown
# Project Context Pack — TASK-001

## 1. Project Background
Project name:   SGW Resilience Platform, version one
Purpose:        Loads a prepared storm scenario, ranks assets by risk with plain-words
                reasons, and records every recommendation and every human decision.
                It recommends; people decide.
Primary users:  operations manager, dispatcher. Two roles: admin, user.
Current stage:  Implementation, first task.

## 2. Current Task
Task:            Sign in with two roles, and the application shell.
Expected output: Both processes (ADR-008) — a FastAPI/Python service holding api, store,
                 scoring, loader, and a Next.js app holding views. The users table and its
                 migration; the two auth endpoints; the session check in the API layer;
                 the AppShell component.
Do not change:   No OpenAI call anywhere — ADR-009's phrasing layer is the scoring work,
                 not this task. Nothing under 01-docs/ — the specification is an input, never an output.
                 decision_records and its triggers (they do not exist yet; do not create
                 them). The scoring module (it does not exist yet; do not anticipate it).

## 3. Relevant Requirements
Requirement ID:        REQ-NF-002, REQ-R-001
Requirement statement: Only signed-in users may reach any view; an admin and a user see
                       different things; every sign-in and every access is recorded.
Acceptance criteria:
- A signed-out request to any data route returns 401 with no project data.
- A wrong email and a wrong password produce an IDENTICAL response.
- Six failed attempts on one account in ten minutes return 429, INCLUDING when each
  attempt comes from a different address.
- No log line, body, or error contains a password, hash, or session value.
- Signing out server-side makes the held session unusable on the next request.
- A role other than admin or user is refused by the database.
- The application fails at STARTUP, named, when a required config value is missing.

## 4. Technical Decisions
Architecture rule: ADR-001 + ADR-008 — five named modules across TWO processes. views is
                   the Next.js app; api, store, scoring, loader are the FastAPI service. A
                   view never imports scoring — now a process line, not a convention. A
                   handler never contains a scoring or matching rule.
Data rule:         ADR-002 — every constraint lives in the schema, not in code. The users
                   table carries check role in ('admin','user'). Never commit the db file.
API rule:          POST /api/v1/auth/session, DELETE /api/v1/auth/session. Response shape
                   from api-specification.md. No hash and no session internals returned.
Security rule:     ADR-003 / SEC-A-001..005 — hashed passwords only, server-side session
                   checked on EVERY request, per-account AND per-IP login rate limit.

## 5. File Map
BACKEND  (FastAPI / Python — ADR-008)
  api/       the two auth endpoints + the ONE session check
  store/     users table and its migration (raw SQL)
FRONTEND (Next.js / TypeScript — ADR-008)
  views/     AppShell only
03-tests/05-executable/integration/   # STEST-001..004
03-tests/05-executable/unit/          # UTEST-001

## 6. Coding Standards
- Validation at the boundary, before any write.
- The session check is ONE thing in the API layer, not a check per handler.
- Every log line carries a request id and never a credential.
- Comments explain why, citing the ADR or SEC id.

## 7. Tests to Run
- STEST-001  signed-out reaches no data route
- STEST-002  an expired and a signed-out session are both refused server-side
- STEST-003  unknown email and wrong password are indistinguishable
- STEST-004  six attempts on one account from six addresses returns 429
- UTEST-001  no credential appears in any log line or response body

## 8. Review Rules
Before finishing, explain what changed, which requirement it implements, which tests
should pass, every assumption made, and any file changed outside the file map above.

## STOP CONDITION
No open question blocks this task. Q-021 is ANSWERED: 240 minutes idle, 12 hours absolute
(ADR-006), already set in .env.example. Read both from config, hard-code neither, and fail
at startup if either is absent. Do NOT call OpenAI — ADR-009 belongs to the scoring work.
Stop and ask if the spec appears to require a third role, self-service registration, an
email service, or any edit under 01-docs/.
```

---

## The context slice pattern (Ch. 12 §12.3)

For a focused task, supply exactly five things:

1. **Current goal** — what you want done now.
2. **Relevant requirement** — the requirement being implemented.
3. **Technical rule** — architecture, API, database, or style constraint.
4. **Acceptance criteria** — how you will judge the result.
5. **Restrictions** — what the agent must not change.

```
Current goal: Implement the login validation logic.
Relevant requirement: Users must log in with email and password.
Acceptance criteria:
- Email is required and must be valid.
- Password is required.
- Invalid credentials return a safe error message.
Technical rule: Do not reveal whether the email or password was wrong.
Restriction: Do not change the database schema in this task.
```

**A sixth thing belongs in every pack on this project: the stop condition.** Open questions have
answers an agent could plausibly invent, and an invented answer is indistinguishable from a
decision once it is in code. `AGENT.md` lists the stop-and-ask set; each pack repeats the ones its
task can reach. **CHG-006 answered fourteen of them, so a pack written earlier can now block a task
for a question that is closed** — check the register, not the pack, when the two disagree.

---

## What to include and exclude (Ch. 12 §12.5)

| Task type | Include | Usually exclude |
|---|---|---|
| Frontend screen | User story, UI behavior, component rules, error states | Database migration details |
| API endpoint | Request/response contract, validation rules, auth rule, tests | Full product roadmap |
| Database change | Entity fields, relationships, constraints, migration notes | UI copy and screen layout |
| Test writing | Acceptance criteria, expected behavior, edge cases | Unrelated features |

**One exclusion does not apply here.** For any task touching a screen, the five states from
`frontend-component-spec.md` are always included — particularly the empty state, because three
of this product's screens read as good news when they are blank.

---

## File map example (Ch. 12 §12.4)

A file map prevents the agent from creating duplicate folders, placing code in the wrong
layer, or ignoring the structure you already chose. List only what the current task needs.

```
project-name/
  01-docs/
    requirements.md          # user-facing and system requirements
    technical-spec.md
  06-agent/
    context-pack.md          # compact agent context for current work
  04-src/
    pages/                   # screen-level frontend pages
    components/              # reusable interface pieces
    api/                     # API route handlers or client calls
    services/                # business logic
    data/                    # data access and schema helpers
```

**This project's real map differs twice over, and both differences matter.** `04-src/README.md`
replaces the generic `services/` with **`scoring/`** and **`loader/`** — only one is the core
subdomain, and only one may never be imported by a view. And **ADR-008 splits the map across two
processes**: `views/` is a Next.js app, everything else is a FastAPI service. Use the real map.

---

## Preventing context confusion (Ch. 12 §12.6)

Context confusion happens when the agent receives mixed, stale, incomplete, or conflicting
information — then follows the wrong instruction even when your current prompt is clear.

**Common triggers:**
- Old requirements that were never removed.
- Two different names for the same feature.
- A prompt that conflicts with the technical specification.
- File maps that no longer match the actual structure.
- Acceptance criteria not linked to the current task.

**Rule:** when a decision changes, **update the context before you ask for more work**.
Do not rely on the agent to guess which instruction is newer.

**This workspace already contains one live version of that trap.** Five changes were made to
accepted documents during the interview (CHG-001 to CHG-005), and each one left an older
sentence somewhere that a careless reader could still find — the reset-link flow, the two
database credentials, the grant-based enforcement of BR-004. Each was corrected in place and
recorded, and the change log is the only reliable way to tell which reading is current. **If a
document and the change log disagree, the change log is newer.**

## Updating the context pack (Ch. 12 §12.7)

Update **after review**, not during uncontrolled generation:
complete a small task → review the output → decide what changed → update the pack →
start the next task.

- [ ] Did the requirement change?
- [ ] Did the technical decision change?
- [ ] Did the file structure change?
- [ ] Did a new rule need to be added?
- [ ] Did an old rule become false?
- [ ] Does the next task need a smaller context slice?

---

## Prompt to use with the pack (Ch. 12)

```
Using the Project Context Pack above, implement only the current task. Do not add
unrelated features. Do not change protected files or decisions. After completing the work,
summarize what changed, list the requirement implemented, and identify the tests that
should pass.
```

---

> Blueprint: blueprints/06-agent/02-context/context-pack.md
