# Pull Request / Review Package Template

> Source: Ch. 15 §15.6, Ch. 28 §28.10, Appendix L.
> A pull request is a **review packet** — code changes, test evidence, requirement links,
> and review notes collected before work is merged. Treat it as your final safety gate,
> not a formality.

> **If a pull request cannot explain what changed and why, it is not ready to merge.**

---

## Template

```
Title: [REQ-ID] Short behavior summary

Requirement Link:
- REQ-###: [requirement summary]

Related Task:
- TASK-###

What Changed:
- 
- 
- 

How I Tested It:
- 
- 
- 

Files Changed:
- 
- 

Tests Added / Updated:
- TEST-###

Security Notes:
- [auth, authorization, validation, secrets, data exposure]

Database or API Changes:
- [schema changes, contract changes, breaking vs. non-breaking]

Rollback Notes:
- [how to return to the previous stable state]

Assumptions Made:
- 

Open Questions:
- 

Reviewer checklist:
[ ] Requirement is satisfied
[ ] Tests prove the behavior
[ ] Security boundary is preserved
[ ] Only approved files changed
[ ] Spec and traceability matrix are updated
```

---

## Three fields this project adds to every pull request

Each closes a gap the standard template leaves, and each corresponds to something that can be
undone silently on this system.

```
Files Changed Outside The Task Plan:
- [list, or "none"]

Store Constraints Touched:
- [any check constraint, foreign key, or trigger added, altered, or dropped — and the
   business rule it enforces. "none" is a valid and common answer.]

Fitness Functions Run:
- [FF-001..FF-006, and their result. If the gate is not wired yet, say which were checked
   by hand and which were not checked at all.]
```

**Why each one exists:**

| Field | The failure it catches |
|---|---|
| Files changed outside the task plan | The one thing no test can report. It makes silent scope expansion self-declared rather than discovered three tasks later, and its value comes from usually saying *none*. |
| Store constraints touched | ADR-004's named weakness: a migration can drop an append-only trigger, and nothing in the suite notices. Any migration in a diff must say what it did to the constraints. |
| Fitness functions run | The register says `Not wired yet` on all six. A pull request that claims "all checks pass" while the gate does not exist is the exact decay `fitness-functions.md` was written to prevent. |

---

## Workflow steps (Ch. 28 §28.10)

| Step | Purpose | Required evidence | AI-agent rule |
|---|---|---|---|
| Create branch | Separate one change from the main working version. | Branch name includes task ID. | Agent works on one task only. |
| Commit small changes | Make progress reviewable. | Commit message names requirement and task. | No large mystery commits. |
| Open review request | Explain what changed and why. | Summary, tests, screenshots if useful. | AI output must be reviewed by a human. |
| Run checks | Prove the change is safe. | Tests, linting, security review, smoke check. | Do not merge failing checks. |
| Merge after approval | Move verified change into the main line. | Reviewer approval and updated traceability. | Update specs if behavior changed. |

**The last column is not advisory here.** CON-008 makes an agent the author of every change, so
*AI output must be reviewed by a human* is the only step in the chain that is not performed by
the thing being checked.

---

## The first pull request — what TASK-001's should contain

Written now so it can be compared against what actually arrives.

| Field | What to expect |
|---|---|
| Requirement Link | REQ-NF-002, REQ-R-001, SEC-A-001…005, SEC-Z-001 |
| Files Changed | `04-src/views/` (AppShell), `04-src/api/` (two endpoints, one session check), `04-src/store/` (users table and migration), and the two test directories |
| Tests Added | STEST-001…004, UTEST-001 |
| Security Notes | The whole change is a security boundary. Confirm the session check is **one** thing in the API layer, not a check per handler, and that no credential appears in any log or body. |
| Database or API Changes | New table with `check role in ('admin','user')`. Non-breaking — nothing exists to break. |
| Store Constraints Touched | The role check constraint. No trigger — `decision_records` does not exist yet and this task must not create it. |
| Assumptions Made | Should be **none**. If the session timeout was chosen rather than read from configuration, Q-021 was answered by an agent and the pull request must be returned. |
| Fitness Functions Run | FF-001 and FF-002 by hand — the other four have nothing to check yet. |

---

> Blueprint: blueprints/05-review/03-version-control/pull-request-template.md
