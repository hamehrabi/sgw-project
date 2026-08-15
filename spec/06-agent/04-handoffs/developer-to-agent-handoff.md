# Developer-to-Agent Handoff

> Source: Ch. 29 §29.3 + Ch. 11 §11.4.
> This is **not** a normal task assignment. An AI agent has no hidden project memory unless
> you provide it.

> **Agent control rule:** the agent should never receive a task that the team cannot
> review. If the output cannot be checked against requirements, tests, or architecture, the
> task is too vague.

---

## Template (Ch. 29 §29.3)

```
Task ID:
Linked requirement(s):
Goal:

Relevant context to use:
  - [requirement / spec section / API contract / ADR]

Files or modules in scope:
Files or modules out of scope:

Constraints:
  - 
  - 

Expected output:
  - [code / tests / documentation / review notes / questions]

Tests to create or update:
  - TEST-###

Questions to ask before changing code:
  - 

Review checklist:
  [ ] 
  [ ] 

Do not proceed if:
  - 
```

---

## The first handoff — TASK-001, ready to send

```
Task ID:              TASK-001
Linked requirement(s): REQ-NF-002, REQ-R-001, SEC-A-001..005, SEC-Z-001
Goal:                 A person signs in with email and password, receives a server-side
                      session, and reaches a shell showing their role. A signed-out
                      request reaches no data route.

Relevant context to use:
  - 02-tasks/02-task-files/TASK-001.md          (the task, in full)
  - 06-agent/02-context/context-pack.md         (the pack for this task)
  - 01-docs/07-security-and-reliability/security-specification.md  §1, §2
  - 01-docs/06-api-and-data-design/api-specification.md            auth endpoints
  - 01-docs/06-api-and-data-design/database-design.md              §3, users table
  - ADR-001 (modules), ADR-002 (store), ADR-003 (auth)

Files or modules in scope:
  04-src/views/    (AppShell only)
  04-src/api/      (two auth endpoints, one session check)
  04-src/store/    (users table and its migration)
  03-tests/05-executable/unit/ and integration/

Files or modules out of scope:
  Everything under 01-docs/ — the specification is an INPUT, never an output.
  decision_records and its triggers — they do not exist yet; do not create them.
  The scoring module — it does not exist yet; do not anticipate it.

Constraints:
  - Two roles only. The database refuses a third.
  - No self-service registration. Nobody creates their own account in this product.
  - No password reset — that is A-003, and it is admin-performed.
  - No second authentication factor — Q-022 is open.
  - Fail at STARTUP on a missing configuration value, never at the first request.

Expected output:
  - Code, the migration, and the five named tests
  - The completion note from agent-rules-and-coding-standards.md

Tests to create or update:
  - STEST-001, STEST-002, STEST-003, STEST-004  (security-tests.md)
  - UTEST-001                                   (unit-tests.md)

Questions to ask before changing code:
  - None expected. If one arises, ask before coding, not after.

Review checklist:
  [ ] A signed-out request to any data route returns 401 with no project data
  [ ] Wrong email and wrong password produce an IDENTICAL response
  [ ] Six attempts on one account from six different addresses returns 429
  [ ] No credential appears in any log line, body, or error
  [ ] The session check is ONE thing in the API layer, not a check per handler
  [ ] No file changed outside the in-scope list

Do not proceed if:
  - You are about to choose a value for SESSION_IDLE_TIMEOUT_MINUTES.
    Q-021 IS OPEN. Build the expiry check, read the value, fail at startup if absent.
  - The task appears to require a third role, registration, or an email.
    None exist here, and a reading that produces one is a misreading.
  - Implementing the session check appears to require editing anything in 01-docs/.
```

---

## The instruction pattern (Ch. 11 §11.4)

```
Task:             [State the exact task]
Source of truth:  [Requirement ID, spec section, or task file]
Allowed files:    [List files or folders the agent may inspect or edit]
Do not change:    [List files, behavior, or design choices that are off-limits]
Expected output:  [Code, tests, documentation, or review notes]
Completion check: [How the work will be verified]
```

---

## Handoff elements (Ch. 29 §29.3)

| Element | What to include | Why it matters | Bad example to avoid |
|---|---|---|---|
| Task boundary | One feature, one bug, one test set, or one document section. | Prevents the agent from changing unrelated work. | "Improve the whole app." |
| Relevant context | Requirements, design notes, API rules, examples, tests. | Gives the agent the source of truth. | "You know what I mean." |
| Forbidden changes | Files, behavior, data, roles, or APIs that must not change. | Protects stable parts of the system. | No boundaries mentioned. |
| Expected output | Code, tests, explanation, checklist, or questions. | Makes completion reviewable. | "Do it well." |
| Review rules | What humans will check before accepting output. | Keeps accountability with the team. | No review criteria. |

**A sixth element is mandatory on this project: the *do not proceed if*.** Five open questions
have plausible invented answers, and an agent that invents one produces work that is
indistinguishable from work that followed a decision. The handoff above ends with three of them
for a reason.

---

## Pre-flight checklist (Ch. 11)

Before you let an agent work, confirm that:

- [x] The task is linked to a requirement, specification, or traceability row.
- [x] The task is small enough to review in one sitting.
- [x] The agent knows which files it may change.
- [x] The agent knows what **not** to change.
- [x] The agent must explain its plan before implementation.
- [x] The expected tests or manual checks are clear.
- [x] The agent must summarize changes, risks, and open questions.

Checked against TASK-001, which is the only task currently handoff-ready. TASK-002 fails the
first box — not for want of a requirement, but because Q-017 leaves it without a format to build
against.

---

## Chat assistant vs. coding agent (Ch. 11 §11.2)

Use both — but do not confuse their roles. First use chat to think through the problem;
then use the agent to perform a narrow, approved implementation task.

| Situation | Use a chat assistant when… | Use a coding agent when… |
|---|---|---|
| Planning | You need to understand options, risks, or structure. | You already have a task and need changes applied. |
| Specification work | You are drafting requirements, PRDs, or technical specs. | You want the agent to update local spec files from approved text. |
| Implementation | You want pseudocode or an explanation before building. | You want code changes made in approved files. |
| Review | You want an independent critique of a design or snippet. | You want the agent to run checks and report mismatches. |

**The specification row has a project-specific exception.** Rule 12 in `AGENT.md` says nothing
under `01-docs/` is an output of any task, so a coding agent with file access never edits the
specification here — even from approved text. A specification change is a change-log entry made
deliberately, not a side effect of a build session.

---

## What agents are good and weak at (Ch. 11 §11.1)

| Agents are good at… | Agents are weak at… |
|---|---|
| Generating boilerplate from clear instructions. | Reading your mind when requirements are vague. |
| Following small, well-scoped implementation tasks. | Knowing which trade-off your business prefers. |
| Creating tests from acceptance criteria. | Detecting every security or performance risk without guidance. |
| Explaining code and proposing refactors. | Understanding undocumented legacy behavior. |
| Speeding up repetitive edits. | Protecting your architecture if you give it no boundaries. |

**The third row on the right is this project's live risk.** An agent will implement the allow
path and forget the deny path — which is why `security-tests.md` carries a deny test for every
*No* in the role matrix, and why two of those tests deliberately sit below the application, at
the database and at the built artifact.

---

> Blueprint: blueprints/06-agent/04-handoffs/developer-to-agent-handoff.md
