# product-spec.md — Product Requirements Document (PRD)

> **Purpose (Ch. 4 §4.4):** Explains user flows, feature scope, and user experience.
> **When you use it:** Before design and implementation.
> **Sources:** Ch. 6, Appendix B.

> **Beginner rule (Ch. 6):** do not describe database tables, frameworks, endpoints, or
> file structure here. Those decisions belong in [`technical-spec.md`](../04-technical-spec/technical-spec.md).

**Product name:** SGW Resilience Platform — version one
**Version:** PRD v1.1
**Owner:** Product owner (not yet named)
**Date:** 2026-08-15

This is the specification for what gets **built**. It is narrower than the source PRD in
`proj-knowledge/`, which describes the whole platform; version one is the P0 probe from that
document, and the difference between the two is recorded in
[`constraints-and-non-goals.md`](../01-intent/constraints-and-non-goals.md).

---

## 1. Product summary

An internal dashboard that loads a prepared storm scenario and shows SGW's operations manager
and dispatcher one joined picture of every asset, ranked by risk, with a plain-words reason
beside each rank. The manager places crews against that ranking before the storm; the dispatcher
works one shared list of damage and repair jobs during it. Every recommendation the system makes
and every decision a person takes is written to a record that nobody can edit afterwards. It
recommends and never acts: no crew is moved, no valve is closed, and no command reaches any
system that controls the grid or the water network. Version one runs entirely on files an admin
uploads, so it can be exercised end to end without connecting to anything SGW operates.

## 2. Problem statement

SGW's storm decisions are made by capable people, but the facts those decisions need sit in four
systems that do not share data. The crew plan is built by hand over hours and restarts whenever
the forecast shifts; the damage picture is assembled from radio calls, alarms and a whiteboard;
and no numbers are ready when a regulator calls. The cost is longer outages, penalty fees,
premium-priced emergency crews and rising insurance. Two of the six parts of a sound decision are
broken — the information, and the reasoning that rests on it — and only those two.

## 3. Product goal

> [This product helps] **[target user]** [achieve outcome] [under important constraint].

**This product helps SGW's operations manager and dispatcher decide where crews go and what is
repaired first, from one current shared set of facts with a stated reason behind every rank,
while every decision stays theirs.**

| Weak goal | Stronger goal |
|---|---|
| Build a task app. | Help small teams create, assign, and track daily work in one place. |
| Make customer support better. | Help support teams answer repeated questions faster with an AI-assisted knowledge base. |
| Create an analytics dashboard. | Help managers see key business numbers without opening spreadsheets. |

## 4. Success metrics

| # | Metric | Type |
|---|---|---|
| 1 | The operations manager reaches a crew placement from a loaded scenario faster than the same decision takes today. Starting target: under one hour, including after a forecast change. The baseline it must beat has not been measured — see Q-018. | Measurable user or business result |
| 2 | The dispatcher reaches one full damage picture in under five minutes, against a baseline of roughly thirty. Same caveat: the baseline is a reasoned figure from the source PRD, not a measurement (Q-018). | Quality or adoption signal |
| 3 | The share of rankings acted on **without the reasons being opened**. If people accept ranks without reading why, BR-002 is buying nothing and over-trust is already happening — the failure the whole reasons-beside-the-rank design exists to prevent. | Failure or risk signal to monitor |

*Examples:* "80 percent of new users create their first task within five minutes." ·
"Average first response time is reduced by 30 percent." · "Managers can view the five core
metrics on one dashboard."

**Two measures from the source PRD are deliberately NOT version-one metrics.** *Real failures
flagged in advance, seven in ten* needs a risk model validated against SGW's own failure history,
which version one does not have and cannot fake. *Operators change their plan in one storm in
three* needs real operators in scenario testing, which is a Phase 1 exit test rather than a
first-month metric. Both are recorded here so their absence reads as a decision.

## 5. Goals / Non-goals

**Goals**
- One joined picture of every asset, with the source and age of every value on it
- A risk ranking that can be argued with, because its reasons are on the screen beside it
- A plan that adjusts when the forecast moves, instead of being rebuilt
- A record of what was recommended and what was decided, that survives the storm

**Non-goals** → [`constraints-and-non-goals.md`](../01-intent/constraints-and-non-goals.md#non-goals--out-of-scope)

## 6. Primary users (personas)

A persona reminds you that software is built for people with goals, frustrations, limits,
and responsibilities — not for an abstract crowd.

**Persona 1**
- Role: Operations manager, working in the one to three days before the storm
- Goal: Decide where the repair crews wait — coast, inland, split, or hire premium-priced help
- Frustration: Hours spent collecting weather emails, map exports and phone calls, all of it thrown away the moment the forecast shifts
- Main use cases: Open the ranked list; read why an asset ranks high; apply the forecast change; record a crew placement
- Success condition: Reaches a placement decision from a loaded scenario without assembling anything by hand, and does it again after a forecast change without starting over

**Persona 2**
- Role: Dispatcher, working through the storm itself
- Goal: Decide what gets repaired first, and stop two crews being sent to the same place
- Frustration: Building one damage picture in their head from radio, alarms and a whiteboard, while new reports arrive faster than they can be written down
- Main use cases: Work the shared damage and repair board; dismiss a false alarm; accept or reject a recommendation
- Success condition: Holds one current damage picture without reconstructing it, and can show afterwards why a job was ordered as it was

**The field crew lead and the executive are not served by version one.** Their capabilities — the
offline crew app and the automatic summary writer — are deferred, so writing personas for them
here would describe users this build does not have. They return with those capabilities.

*Example (Ch. 6 §6.3)*

| Persona field | Example |
|---|---|
| Name or role | Project manager |
| Goal | Assign work and know what is delayed. |
| Frustration | Tasks are scattered across messages and notebooks. |
| Main use cases | Create project, assign task, review task status, follow up on overdue work. |
| Success condition | Can see all active work without asking every team member. |

## 7. Feature scope

**In scope for this version**

| Feature | In-scope behavior | Why it belongs now |
|---|---|---|
| Joined asset view | One record per substation, line, plant or pump, built from the uploaded files, with the source and age shown on every value and unmatched records flagged for a person. | Nothing else can be built on top of four disagreeing files. It is the missing-information half of the diagnosis. |
| Ranked risk list with reasons | Every asset in one list ordered by risk, each rank carrying plain-words reasons. | This is what the product competes on, and the two guesses that could end the project are both about it. |
| Planning view | The manager reads the ranking, applies the scenario's forecast change, and records a crew placement against it. | It is where the ranking becomes a decision. Without it the ranking is a report. |
| Dispatch board | One shared list of damage reports and repair jobs, with one-action dismissal of a false alarm. | The during-storm half of the same problem, and the only way to stop two crews reaching one location. |
| Scenario upload and switching | An admin drags prepared files in; several storms can be loaded at once and switched between. | CON-005 makes prepared data the only source, so getting data in is not a convenience — it is the entry point to the whole product. |

> **Scope control habit (Ch. 6 §6.4):** for every feature you include, write one sentence
> explaining why it belongs in this version. If you cannot explain the value, move it to
> out of scope.

## 8. Out of scope

**Not included in this version**

| Feature | Reason | Future status |
|---|---|---|
| Live connections to the four source systems | Version one runs on uploaded files. Connecting the systems is the largest cost in the plan and tests none of the guesses that could end the project. | Deferred — P1 |
| Water early-warning on sensor readings | Serves the during-storm decision rather than the ranked-risk guess version one exists to test. | Deferred — P1 |
| Automatic summary writer for leadership | A language model plus a human approval step is a body of work with its own failure mode. | Deferred — P1 |
| Offline crew app, field photo capture, route planning | All three are sequenced after operators trust the ranking, and none can be trusted before that. | Deferred — P2 |

Full non-goals list → [`constraints-and-non-goals.md`](../01-intent/constraints-and-non-goals.md#non-goals--out-of-scope)

## 9. User stories

Format: `US-###: As a [specific role], I want [one clear capability], so that [benefit].`

| ID | Story | Supports | Produces task | Produces test |
|---|---|---|---|---|
| US-001 | As an admin, I want to drag a prepared storm's files into the app, so that a scenario is ready to work on without anyone touching a server. | REQ-F-010 | — | — |
| US-002 | As an admin, I want to keep several storms loaded and switch between them, so that I can compare or re-run without destroying the one I have. | REQ-F-010 | — | — |
| US-003 | As an operations manager, I want one record per asset with the source and age of every value, so that I can tell a live reading from a six-year-old inspection. | REQ-F-001 | — | — |
| US-004 | As an operations manager, I want every asset in one list ordered by risk, so that I stop assembling the picture by hand. | REQ-F-002 | — | — |
| US-005 | As any user, I want the reasons for a rank on the screen beside it, so that I can disagree with the ranking instead of obeying it. | REQ-F-003 | — | — |
| US-006 | As an operations manager, I want the list to re-rank when the forecast changes, so that a shift adjusts my plan instead of restarting it. | REQ-F-004 | — | — |
| US-007 | As an operations manager, I want to record a crew placement against the ranking, so that the decision is captured where the evidence for it is. | REQ-F-005 | — | — |
| US-008 | As any user, I want to accept, change, or reject a recommendation, so that the system stays something that advises me. | REQ-F-006 | — | — |
| US-009 | As a dispatcher, I want one shared list of damage and repair jobs, so that no crew is sent to a location another crew is already at. | REQ-F-007 | — | — |
| US-010 | As a dispatcher, I want to dismiss a false alarm in one action, so that alarms which are cheap by design stay cheap to clear. | REQ-F-008 | — | — |
| US-011 | As an admin, I want an unalterable record of every recommendation and decision, so that the storm can be explained to a regulator afterwards. | REQ-F-009 | — | — |

> **"Produces task" and "Produces test" are written by a LATER round, not this one.** Tasks and
> tests do not exist yet when the stories are written, so the honest value here is `—`.
>
> **Never write `TASK-###` or `TEST-###` into these cells.** A stub reads as an identifier that
> exists — a reader follows it and finds nothing — and it is not the sanctioned way to record
> something unknown. If a story still has no task once the task list is written, that is a gap
> worth a `[TODO]`, not a stub.

| Weak story | Stronger story |
|---|---|
| As a user, I want tasks. | As a team member, I want to create a task with a due date so that I can record work that needs attention. |
| As an admin, I want control. | As an owner, I want to invite team members so that work can be shared inside one workspace. |
| As a manager, I want reports. | As a project manager, I want to see overdue tasks so that I can follow up quickly. |

## 10. User flows

A good flow includes the start point, user action, system response, success path, and
**at least one failure path**. Failure paths matter because real users make mistakes, lose
connection, forget fields, or lack permission.

**Flow name:** Place crews against the ranking
- Start: The operations manager opens the planning view with a scenario loaded.
- Action: Reads the ranked list, opens the reasons behind the top-ranked assets, then records a placement.
- Input: The placement — which crews wait where — against named assets.
- System response: Records the placement and writes one row to the decision record.
- Success path: The placement is saved, visible, and traceable to the ranking and forecast revision it was made against.
- Failure path: If a value the ranking rests on is stale, the screen says so with its age before the manager acts, rather than after. If the placement cannot be saved, the typed placement is kept on screen and the failure is named — a lost placement during a storm is worse than an error message.

**Flow name:** Load a prepared storm
- Start: An admin opens the scenario screen.
- Action: Drags the prepared files in.
- Input: The files, a scenario name, and a note saying where the data came from.
- System response: Validates types and size, parses the files, matches assets across their different codes, and reports what could not be matched.
- Success path: The scenario appears in the list alongside any others already loaded, and becomes selectable.
- Failure path: A file over the size limit or outside the allow-list is refused before parsing, naming which file and why. A file that parses but fails validation loads nothing and leaves the previously loaded scenarios untouched — a half-loaded storm is worse than a refused one. Assets that cannot be matched load with a `needs review` flag and are shown to a person; they are never merged on a guess.

*Example (Ch. 6 §6.7)*

| Flow step | Example: Create a task |
|---|---|
| Start | Team member opens the task dashboard. |
| Action | Team member selects Add Task. |
| Input | Enters title, description, due date, and status. |
| System response | System validates required fields. |
| Success path | Task is saved and appears in the task list. |
| Failure path | If the title is missing, the system shows a clear error and keeps the typed values. |

## 11. Feature priorities

| Priority | Meaning | Features |
|---|---|---|
| Must-have | The first useful version fails without it. | Scenario upload; joined asset view; ranked risk list with reasons; accept / change / reject; dispatch board; the decision record |
| Should-have | Important, but the product can still be tested without it. | Re-rank on forecast change; recording a crew placement; one-action false-alarm dismissal |
| Could-have | Useful improvement if time allows. | Switching between several loaded storms — one storm is enough to test the idea, several make it usable |
| Later / Won't | Not needed for the first version. | Everything in §8 |

> **Prioritization test (Ch. 6 §6.8):** if this feature is missing, can you still test the
> main product idea? If yes, it may not be a must-have for the first version.

## 12. Dependencies

The prepared storm datasets themselves are the only real dependency, and their shape is not yet
known (Q-017). Nothing else: CON-006 rules out paid services and CON-005 rules out live
connections, so version one depends on no provider, no API, and no system SGW operates. The one
thing only SGW can supply — its own history of which assets failed in past storms — is **not** a
version-one dependency, because validating the risk model against history is out of scope here;
it becomes the critical dependency the moment that validation is attempted.

## 13. Risks

| Risk | Type (product / technical / security / operational) | Mitigation |
|---|---|---|
| A combined ranked view does not actually change the crew decision (assumption A2). | Product | Version one exists to find this out cheaply. Success metric 1 measures it; if it fails, redesign rather than scale. |
| Operators do not act on a computer's ranking (assumption A3). | Product | Reasons beside every rank (BR-002), and success metric 3 watches whether they are actually read. |
| Four capabilities do not fit in about a week. | Operational | Priorities in §11 name what drops first, and Q-008 asks the question directly rather than discovering it on day six. |
| An uploaded file is malicious. | Security | Admin-only upload, allow-list by content inspection, generated filenames, never executed, never served back. No scanner in version one — recorded with a revisit trigger. |
| A ranking is trusted because it looks authoritative, when it rests on six-year-old data. | Product | BR-003: source and age on every value, estimated visually distinct from measured. |
| The prepared data does not resemble SGW's real data, so version one proves nothing. | Technical | The source PRD's seven measured defects are injected on purpose, and the loader is specified against them rather than against clean data. |

## 14. Open questions

→ [`open-questions.md`](../01-intent/open-questions.md)

## 15. Links to requirements

- Supports REQ-F-001 through REQ-F-010
- Supports REQ-NF-001, REQ-NF-003, REQ-NF-004
- Supports REQ-R-001, REQ-R-002, REQ-R-003
- Supports BR-001, BR-002, BR-003, BR-004, BR-005

---

## Per-requirement format (Appendix B)

```
Requirement ID: REQ-001
Title:
Description:
User Value:
Priority: Must / Should / Could / Won't
Acceptance Criteria:
Dependencies:
Notes:
```

| Priority | Meaning | How to use it |
|---|---|---|
| Must | Required for the first usable release. | Do not start implementation until this is clear. |
| Should | Important but not release-blocking. | Plan after Must requirements. |
| Could | Useful improvement. | Keep for later unless capacity remains. |
| Won't | Not included in this release. | Protects scope from uncontrolled growth. |

---

## PRD quality checklist (Ch. 6)

| Check | Question | ✔ |
|---|---|---|
| Clear product goal | Can you explain the product outcome in one sentence? | [x] |
| Known users | Have you identified the primary users and their goals? | [x] |
| Useful success metrics | Can you tell whether the product is working for users? | [ ] |
| Controlled scope | Does the PRD clearly state what is included now? | [x] |
| Protected focus | Does it clearly state what is out of scope? | [x] |
| User stories | Are the most important features written from the user point of view? | [x] |
| User flows | Can you follow the user path from start to success or failure? | [x] |
| Ready for technical spec | Can a technical designer use this without guessing the product direction? | [x] |

Success metrics is unticked because two of the three compare against a baseline nobody has
measured (Q-018). "Faster than today" is not yet a number anyone can pass or fail.

---

## Writing workflow (Ch. 6)

1. Start with [`requirements.md`](../02-requirements/requirements.md).
2. Write a short product summary in plain language.
3. Define one main product goal before listing features.
4. Add two or three success metrics that can be observed or measured.
5. Describe the main personas and their use cases.
6. Separate in-scope features from out-of-scope features.
7. Write user stories for the most important user outcomes.
8. Write simple user flows for the must-have features.
9. Prioritize features before moving to the technical specification.

---

**Next:** [`technical-spec.md`](../04-technical-spec/technical-spec.md)

---

> Blueprint: blueprints/01-docs/03-product-spec/product-spec.md
