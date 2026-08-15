# requirements.md — Requirements Document

> **Purpose (Ch. 4 §4.4):** Lists functional and non-functional requirements.
> **When you use it:** Before product and technical specs.
> **Source:** Ch. 5.

A useful requirement is **clear, testable, bounded, and traceable**.

**Project name:** SGW Resilience Platform

**Problem statement:** *(from [`intent.md`](../01-intent/intent.md))* SGW's storm decisions are
made by capable people, but the facts those decisions need sit in four systems that do not
share data. So the crew plan is built by hand over hours and restarts whenever the forecast
shifts, the damage picture during the storm is assembled from radio calls and a whiteboard, and
no numbers are ready when a regulator calls. Storm decisions should be made from one current,
shared set of facts, with people still making every decision.

**Primary users:**
- Operations manager — places crews before the storm
- Dispatcher — chooses what is repaired first during the storm

---

## 1. Functional requirements

Format: `REQ-F-###: [Actor] must be able to [action] [object] so that [outcome].`

**How priority was set.** *Must* is anything that carries the two guesses version one exists to
test — that a combined ranked view changes the crew decision, and that operators act on a
ranking that shows its reasons. *Should* is everything real that does not. This rule is written
here because the one-week horizon (CON-002) forces the distinction to be made by something, and
a priority chosen by whoever reads the file first is not a priority. See Q-008.

| ID | Requirement | Priority |
|---|---|---|
| REQ-F-001 | The system must join asset records from the prepared data files into one view per asset, carrying the source and the age of every value, so that nobody assembles facts by hand. | Must |
| REQ-F-002 | The operations manager must be able to see every asset ranked by risk in one list, so that crews are placed on evidence rather than recollection. | Must |
| REQ-F-003 | Every user must be able to see the reasons behind each risk rank, written in plain words, so that a person can judge the ranking instead of taking it on trust. | Must |
| REQ-F-004 | The operations manager must be able to re-rank the list against a changed forecast inside the prepared scenario, so that a forecast change adjusts the plan instead of restarting it. | Should |
| REQ-F-005 | The operations manager must be able to record a crew placement against the ranked list, so that the planning view produces a decision rather than a reading. | Should |
| REQ-F-006 | The operator must be able to accept, change, or reject every recommendation, and the system must never move a crew by itself, so that a human always makes the final decision. | Must |
| REQ-F-007 | The dispatcher must be able to see one shared list of damage reports and repair jobs, so that nothing is missed and no crew is sent to the same place twice. | Must |
| REQ-F-008 | The dispatcher must be able to dismiss a false alarm in one action, so that alarms which are cheap by design do not slow real work. | Should |
| REQ-F-009 | The system must record every recommendation and every human decision with a timestamp and the acting user, so that a storm can be explained after it ends. | Must |
| REQ-F-010 | An admin must be able to load a prepared storm scenario, so that version one can be exercised end to end without any live connection. | Must |

*Example:* `REQ-F-001: A team member must be able to create a task with a title,
description, due date, and status so that work can be tracked clearly.`

| Element | Question to ask | Example |
|---|---|---|
| Actor | Who performs the action? | Project manager |
| Action | What must they do? | Assign a task |
| Object | What is being acted on? | A task record |
| Result | What should happen after the action? | The assigned user can see the task |

---

## 2. Non-functional requirements

Format: `REQ-NF-###: [Quality condition with a measurable limit].`

| ID | Category | Requirement |
|---|---|---|
| REQ-NF-001 | Performance | Re-rank 220 assets in **under 5 s**; page load **under 2 s**; reason panel open **under 300 ms**. Measured on the fixture (Q-017), not promised — which is what separates these from the source PRD's own figures, which that document labels as starting targets. |
| REQ-NF-002 | Security | Only signed-in users may reach any view. An admin and a user see different things (§3). Every sign-in, every read of the decision record, and every accept, change or reject is recorded. |
| REQ-NF-003 | Reliability | If a prepared data file is missing or malformed, the system must show the last good picture, clearly marked as stale and dated, rather than an empty screen or an error page. It must name which file failed. |
| REQ-NF-004 | Usability | An operator under storm conditions reaches any critical action in two actions or fewer, without a manual. |
| REQ-NF-005 | Maintainability | The risk-scoring logic must be separable from the views that display it, so that the core subdomain can change without touching the planning view or the dispatch board. |
| REQ-NF-006 | Accessibility | **WCAG 2.1 AA**, as a constraint rather than a driver — the three drivers stand. `frontend-component-spec.md` already carries the two rules that do most of the work: `RiskList` is operable by keyboard alone, and colour is never the only signal for a rank. |
| REQ-NF-007 | Privacy | Screens show neighbourhood or feeder totals, never single households. The data enumerated in CON-003 is never stored, never logged and never rendered. A `critical_facility` boolean is permitted on an asset and is the only premise-adjacent field in the model. |

**Examples (Ch. 5 §5.3)**

| Category | Requirement example |
|---|---|
| Performance | The dashboard must load within three seconds for a workspace with up to 1,000 tasks. |
| Security | Only authenticated users may access workspace data. |
| Reliability | If task creation fails, the system must show an error and preserve the user's input. |
| Usability | A new user must be able to create their first task without reading a separate manual. |
| Maintainability | Task-related logic must be separated from user-authentication logic. |

> **Do not write impossible quality claims.** Avoid "the app must never fail" or "the
> system must always be fast." Replace them with measurable expectations, known limits,
> and graceful failure behavior.

---

## 3. User roles and permissions

Format: `REQ-R-###`. Define these **before** design begins, or the agent may build
features that expose data to the wrong users.

| Role | Can do | Cannot do |
|---|---|---|
| Admin | Load and replace a prepared storm scenario. See every view. Accept, change or reject a recommendation. Read the decision record. | Alter or delete a decision record once written. Issue any command to a system that controls the grid or the water network. |
| User | See the joined asset view, the ranked risk list and its reasons, the planning view and the dispatch board. Accept, change or reject a recommendation. Record a crew placement. Dismiss a false alarm. | Load or replace a prepared storm scenario. Alter or delete a decision record. Issue any command to a controlling system. |

| ID | Role requirement |
|---|---|
| REQ-R-001 | A user must be able to read every view and act on recommendations, but must not load or replace a prepared storm scenario. |
| REQ-R-002 | No role, including admin, may alter or delete a decision record once it is written — the audit trail must not be editable by the people it records. |
| REQ-R-003 | No role may issue a command to a system that physically controls the grid or the water network. Version one holds no such path in either direction (CON-005, CON-007). |

**Examples (Ch. 5 §5.4)**

| Role | Can do | Cannot do |
|---|---|---|
| Owner | Create workspace, invite users, manage billing, delete workspace. | Bypass audit rules or view another workspace. |
| Project manager | Create projects, assign tasks, update project settings. | Manage billing or delete the workspace. |
| Team member | Create tasks, update assigned tasks, comment on work. | Invite users or change workspace settings. |
| Viewer | Read permitted projects and tasks. | Create, edit, delete, or assign tasks. |

| Role requirement example |
|---|
| A Viewer must be able to read assigned project information but must not create, edit, assign, or delete tasks. |

**A role you list here is a role the agent will build.** Four roles is four permission paths,
four sets of deny tests, and an invitation flow. A single-user tool has one role; say so.

Full permission matrix and enforcement rules → [`technical-spec.md` §7 Security](../04-technical-spec/technical-spec.md#7-security-requirements)

---

## 4. Business rules

Policy decisions the software must enforce. Write them **separately from code
instructions** — when the rule changes you update the spec first, then the tests and code.

| ID | Rule | Why it matters |
|---|---|---|
| BR-001 | The system never moves a crew or takes any field action by itself. Every recommendation is accepted, changed or rejected by a person before it becomes a decision. | It is the rule the whole product is governed by. Remove it and the product changes category, from decision support to automation, with a different regulator and a different liability. |
| BR-002 | A risk rank is never shown without its reasons. | The core subdomain is the rank *and* its reasons together. A rank nobody can interrogate is the thing operators were predicted not to act on. |
| BR-003 | Every value on screen shows its source and its age, and an estimated value is visually distinct from a measured one. | Condition data is partly old and partly estimated. A six-year-old inspection presented like a live reading is a wrong decision waiting to happen. |
| BR-004 | The decision record is append-only. A correction is a new row, never an edit. | An audit trail its own subjects can rewrite proves nothing, and its value is realised exactly when someone would most want to change it. |
| BR-005 | Version one reads only from prepared data files. No connection to an operational system exists, in either direction. | It is what makes a one-week build honest, and it keeps the read-only wall true by construction rather than by discipline. |

**Examples (Ch. 5 §5.5)**

| Business rule | Why it matters |
|---|---|
| A completed task cannot be edited unless it is reopened. | Protects completed work from accidental changes. |
| Only an Owner can delete a workspace. | Prevents destructive actions by lower-permission users. |
| A task due date cannot be earlier than today when the task is created. | Prevents invalid planning data. |
| A user can belong to multiple workspaces, but workspace data must remain separate. | Protects data boundaries. |

---

## 5. System constraints

Maintained in [`constraints-and-non-goals.md`](../01-intent/constraints-and-non-goals.md),
which `intent.md` delegates them to. Referenced here as `CON-###`.

| ID | Constraint | Affects requirements |
|---|---|---|
| CON-001 | No technology is mandated. | None — the stack is decided in Round 5. |
| CON-002 | About one week to build version one. | REQ-F-004, REQ-F-005, REQ-F-008 (all *Should* for this reason) |
| CON-003 | Certain data must not be stored. | REQ-NF-007 |
| CON-004 | No environment ceiling imposed. | None. |
| CON-005 | Prepared data files only; no live connections. | REQ-F-001, REQ-F-010, REQ-R-003, BR-005 |
| CON-006 | No paid third-party services. | REQ-NF-002 (authentication is built, not bought) |
| CON-007 | Read-only toward controlling systems; neighbourhood-level display. | REQ-R-003, REQ-NF-007, BR-005 |
| CON-008 | Team skill not yet stated. | None yet — see Q-009. |

---

## 6. Acceptance criteria

Format: Given–When–Then. These become the acceptance tests in
[`../tests/acceptance-tests.md`](../../03-tests/02-functional/acceptance-tests.md).

| ID | Requirement | Criterion |
|---|---|---|
| AC-001 | REQ-F-001 | **Given** a prepared scenario whose asset records carry different codes for the same asset, **When** the joined view is built, **Then** each asset appears once and every value shows its source and its age. |
| AC-002 | REQ-F-001 | **Given** a prepared data file that is missing or malformed, **When** the joined view is built, **Then** the last good picture is shown, marked stale and dated, and the failing file is named. |
| AC-003 | REQ-F-002 | **Given** a signed-in operations manager and a loaded scenario, **When** they open the planning view, **Then** every asset in the scenario appears in one list ordered by risk. |
| AC-004 | REQ-F-003 | **Given** any risk rank on any screen, **When** a user looks at it, **Then** the reasons behind it are shown in plain words alongside it, never behind a separate request. |
| AC-005 | REQ-F-004 | **Given** a ranked list and a forecast change inside the scenario, **When** the change is applied, **Then** the list re-ranks and the previous order remains retrievable for comparison. |
| AC-006 | REQ-F-006 | **Given** a recommendation shown to an operator, **When** they accept, change, or reject it, **Then** the outcome is recorded and no crew movement is issued by the system itself. |
| AC-007 | REQ-F-007 | **Given** two damage reports for the same location, **When** the dispatcher opens the board, **Then** both are visible and linked to one job rather than two. |
| AC-008 | REQ-F-009 | **Given** any recommendation or human decision, **When** it occurs, **Then** a row is appended carrying the timestamp and the acting user, and no path exists to edit or remove it. |
| AC-009 | REQ-R-001 | **Given** a signed-in user who is not an admin, **When** they attempt to load or replace a prepared scenario, **Then** the action is refused and the refusal is recorded. |
| AC-010 | REQ-NF-003 | **Given** the platform running with stale data, **When** any screen is opened, **Then** the staleness and the age are stated on the screen rather than inferred by the reader. |

**Examples (Ch. 5 §5.7)**

| Requirement | Acceptance criteria |
|---|---|
| A team member must be able to create a task. | Given a signed-in team member, when they submit a valid task form, then the task is saved and shown in the task list. |
| A viewer must not edit tasks. | Given a signed-in viewer, when they open a task, then edit controls are hidden or disabled. |
| Task creation must handle errors. | Given a network failure, when the user submits the form, then the system shows an error and keeps the typed values. |

---

## 7. Open questions

→ [`open-questions.md`](../01-intent/open-questions.md)

---

## Requirement quality checklist (Ch. 5)

| Check | Question | ✔ |
|---|---|---|
| Clear | Can you understand the requirement without guessing? | [x] |
| Actor defined | Does it say who performs the action? | [x] |
| Action defined | Does it say exactly what must happen? | [x] |
| Bounded | Does it avoid hidden extra features? | [x] |
| Testable | Can you prove whether it works? | [x] |
| Traceable | Can it become a task, test, and code change later? | [x] |
| No implementation leak | Does it avoid technical decisions that belong in the technical spec? | [x] |

Testability is now ticked: Q-012 gave REQ-NF-001 and REQ-NF-004 real numbers against a real
dataset, and Q-013 gave REQ-NF-006 a standard. Every requirement here can now be proved or
disproved — which was not true when this file was written (CHG-006).

> **The safest habit:** before you send requirements to an AI agent, read each one and ask
> "could two people interpret this differently?" If yes, rewrite it.

---

## Common requirement mistakes (Ch. 5 §5.8)

| Mistake | Weak example | Better approach |
|---|---|---|
| Vague wording | "The dashboard should be nice." | State what the dashboard must show and how users will use it. |
| No actor | "Tasks can be deleted." | Say which role can delete tasks and under what condition. |
| No boundary | "Users can manage projects." | List the allowed project actions for each role. |
| No acceptance criteria | "Users can reset passwords." | Add the expected email flow, token expiry, and failure behavior. |
| Implementation hidden in requirement | "Use a modal with React state." | Describe behavior first; save implementation details for the technical spec. |

---

## Writing workflow (Ch. 5)

1. Start with the problem statement from the Engineering Intent Document.
2. List the primary user roles before listing features.
3. Write functional requirements using actor, action, object, and outcome.
4. Add non-functional requirements that define quality expectations.
5. Write business rules separately from implementation choices.
6. List constraints so the AI assistant does not invent unrealistic solutions.
7. Add acceptance criteria for every important requirement.
8. Review the document for ambiguity before moving to the PRD.

---

**Next:** [`product-spec.md`](../03-product-spec/product-spec.md)

---

> Blueprint: blueprints/01-docs/02-requirements/requirements.md
