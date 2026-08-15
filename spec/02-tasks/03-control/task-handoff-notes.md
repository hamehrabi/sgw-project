# Task Handoff Notes

> Source: Ch. 30 §30.2, Ch. 29 §29.3, Ch. 11 §11.7.
> Notes passed between a human and an agent, or between sessions, when a task is picked
> up, paused, or returned.

---

## Handoff entries

```
Task ID:
Date:
From → To:          [human → agent | agent → human | session A → session B]
Current status:     [Not started / In progress / Blocked / In review]

What is done:
What is not done:
Files touched so far:
Assumptions made:
Open questions blocking progress:
Next concrete step:
Do not change:
Tests currently passing:
Tests currently failing:
```

**No task has been handed off yet** — no code exists. The first entry will be written when
TASK-001 is picked up.

**The `Assumptions made` field is the one that earns this file.** An agent that reports an
assumption lets it be corrected; an agent that does not report it ships it. On this project
three assumptions are especially likely and especially costly: what a missing configuration
value should default to (nothing — fail at startup), what to do with an asset that cannot be
matched (flag it, never merge it), and what an empty result means on screen (say so, never let
it read as safety).

---

## Agent three-stage workflow (Ch. 11 §11.7)

The agent must not skip a stage. You check the right-hand column.

| Stage | Agent must do | You check |
|---|---|---|
| **Prepare** | Restate the task, list relevant files, identify assumptions. | The agent understands the scope and is not expanding it. |
| **Implement** | Change only approved files; keep the solution small. | Code matches the spec and creates no surprise behavior. |
| **Report** | Summarize changes, tests, risks, and unresolved questions. | You can review without hunting through every file blindly. |

> **Practical rule:** if an agent cannot explain what it changed, why it changed it, and
> how to verify it, the task is not complete.

---

## Mid-work checkpoint (Ch. 29 §29.7)

Trigger a checkpoint when the agent or developer finds ambiguity.

| Check | Answer |
|---|---|
| What assumption is being made? | |
| What is blocking progress? | |
| Which design choice is in question? | |
| Decision needed from whom? | |
| Revised task boundary: | |

The table is left empty because no checkpoint has been triggered. It is copied per checkpoint,
not filled once.

**Five open questions will trigger a checkpoint if an agent reaches them**, and each has a
correct response that is *stop*, not *choose*:

| Question | What an agent must do rather than decide |
|---|---|
| Q-017 — scenario formats and sizes | Stop. A parser cannot be written against a guessed format, and a guessed size limit reads exactly like a measured one. |
| Q-021 — session lifetime | Stop at the configuration value. Build the expiry check; do not pick a duration. |
| Q-022 — second factor | Stop. Adding one decides an open question; leaving it out is the current specified state, which is different from deciding it. |
| Q-025 — scoring factors and weights | Stop. ADR-005 fixes the *kind* of scorer, not its content. Weights chosen by an agent would be indistinguishable from weights chosen by the operations manager. |
| Q-007 — which data must not be stored | Stop before adding any field not already in `database-design.md` §3. |

---

## Control rules while a task is in flight (Ch. 11 §11.5)

| Control rule | How you apply it |
|---|---|
| One task at a time | Do not combine login, registration, password reset, and roles in one request. |
| Approved files only | Tell the agent which folders or files it may edit. |
| Plan before edit | Ask for a short plan before allowing implementation. |
| No silent assumptions | Require the agent to report unclear requirements before coding. |
| Tests required | Every behavior change includes or updates a test. |
| Review before next task | Do not move on until you have checked the current result. |

One rule is specific to this workspace and sits above those six: **nothing under `01-docs/` is
an output of any task.** The specification is an input. An agent that finds itself editing a
requirement to make its code pass has inverted the whole method, and the change belongs in
`01-docs/09-change-control/spec-change-log.md` as a decision before it belongs in code.

---

> Blueprint: blueprints/02-tasks/03-control/task-handoff-notes.md
