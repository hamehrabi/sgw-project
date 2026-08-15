# Agent Task List

> Source: Front Matter workspace, Ch. 14, Ch. 25 §25.8, Ch. 30 §30.2.
> An agent-friendly task list is **not** a normal to-do list. Each entry gives the agent
> instructions in a format that reduces guessing.
>
> **The best task list is boring, specific, and controlled.**

---

## Task table

| Task ID | Agent task | Input artifacts | Acceptance check | Depends on | Out of scope |
|---|---|---|---|---|---|
| A-001 | Create the project structure with five named modules — loader, store, scoring, api, views — and configuration loading from environment variables. | ADR-001, `technical-spec.md` §2, `.env.example` | The application starts, serves an empty health check, and no module imports another against the direction in ADR-001. | — | Any business feature. Any screen with data on it. |
| A-002 | Implement sign-in with email and password, a server-side session checked on every request, and the two roles. | ADR-003, SEC-A-001…005, SEC-Z-001, `api-specification.md` auth endpoints | A signed-out request to any data route returns 401. A wrong email and a wrong password return an identical message. Six failed attempts on one account in ten minutes return 429. | A-001 | Password reset (A-003). Any second factor — Q-022 is open. |
| A-003 | Implement admin-set temporary password reset, forcing a change at next sign-in. | SEC-A-004, SEC-Z-006, CHG-004 | A user role attempting to reset another user returns 403. After a reset the target reaches only the change-password screen. The reset does not change the target's role. | A-002 | Any email sending. There is no email service (Round 6). |
| A-004 | Implement the scenario upload endpoint: accept files, check size and type by content inspection, store under a generated identifier, queue the parse. | REQ-F-010, SEC-Z-002, `database-design.md` addendum | An oversize file (>8 MB, or >10 MB total) returns 413 and writes nothing. A file whose extension is allowed but whose content is not returns 415. A non-admin returns 403 and the refusal is recorded. | A-002 | Parsing (A-005). |
| A-005 | Implement the parse job: read `manifest.json` and the four CSVs, check row counts against the manifest, apply the seven defect rules, join assets across differing codes, write one scenario in one transaction. | `data-and-integration-spec.md` §1, §4; `database-design.md` §1, §3 | A file valid for three of five inputs creates no scenario and leaves loaded scenarios rankable. A row count that disagrees with the manifest fails the load. Unmatched assets load as `needs_review` and are never merged. | A-004 | Scoring. Any screen. |
| A-006 | Build the joined asset view screen, showing the source and age of every value and flagging unmatched assets. | REQ-F-001, BR-003, `frontend-component-spec.md` `AssetTable` | Every value renders its source and observation date. An estimated value is visually distinct from a measured one. | A-005 | Ranking. Editing an asset — nothing in this product edits an asset. |
| A-007 | Implement the deterministic scoring rule and the reasons it produces, inside the scoring module only. Weights and bands from ADR-007, read from configuration. | **ADR-005, ADR-007**, BR-002, `ai-boundary-spec.md` §2, §4 | No score can be stored without at least one reason — the database refuses it. The reasons are produced by the same computation as the score, not written separately. No view imports this module. | A-005 | Any training step, model file, or learned parameter. Any threshold that turns a rank into an instruction to act. |
| A-008 | Build the ranked risk list screen with reasons visible beside each rank. | REQ-F-002, REQ-F-003, `frontend-component-spec.md` `RiskList` | Every rank shows a route to its reasons. An empty ranking reads "no ranking computed", never as no risk. An unscorable asset appears as UNSCORED with its reason. | A-007 | Re-ranking (A-010). Crew placement (A-011). |
| A-009 | Implement accept / change / reject on a recommendation, appending to the decision record, with the two append-only triggers in the migration. | REQ-F-006, REQ-F-009, BR-001, BR-004, ADR-004 | An `UPDATE` against `decision_records` is refused by the **database**. A second decision on one recommendation returns 409 and leaves the first row untouched. Change and reject without a note are rejected. | A-008 | Anything that acts on the decision. No crew is moved by software, at any version. |
| A-010 | Implement applying a forecast revision and re-ranking, writing a new revision rather than overwriting. | REQ-F-004, `database-design.md` §3 | An earlier `forecast_revision` returns the earlier order unchanged. An unknown revision returns 404, never a silent fallback to the current one. | A-008 | — |
| A-011 | Implement recording a crew placement against the ranking. | REQ-F-005 | A placement survives a failed save as typed values on screen. It is traceable to the ranking and revision it was made against. | A-008 | Routing, scheduling, or notifying anyone. |
| A-012 | Build the dispatch board — one shared list of damage reports and repair jobs. | REQ-F-007, `frontend-component-spec.md` `DispatchBoard` | Two reports at one location resolve to one job. An empty board reads "no damage reported", never "all clear". | A-005 | Dismissal (A-013). Assigning crews to jobs automatically. |
| A-013 | Implement one-action false-alarm dismissal that records who dismissed it and why. | REQ-F-008 | A dismissal without a reason or an actor is refused by the database. | A-012 | Bulk dismissal. |
| A-014 | Implement switching between several loaded storms. | REQ-F-010, CHG-001 | Two loaded storms never blend into one ranking; every read carries its `scenario_id`. | A-005 | Comparing two storms side by side. |
| A-015 | Wire the six fitness functions into a build gate that fails the build. | `fitness-functions.md` FF-001…FF-006 | Each of the six runs, and a deliberate violation of each one fails the build rather than printing a warning. | A-001 | Any new fitness function. Six are defined; adding a seventh is a decision, not a task. |

**A-004 and A-005 were blocked on Q-017 and are not any more** (CHG-006). A prepared scenario is
a manifest plus four CSVs under 5 MB; the allow-list is those five filenames, verified by content
inspection. Every item in this list can now be started.

---

## Breaking a feature into tasks (Ch. 14 §14.2)

Start with **one approved feature**, not the whole product. Split it into the pieces
needed to make it real.

| Feature area | Possible task | Output | Test signal |
|---|---|---|---|
| Data | Create the entity fields | Schema or model | Record can be stored |
| Rules | Define validation | Validation function | Invalid input is rejected |
| API | Create the endpoint | Endpoint contract | Correct response is returned |
| UI | Build the form | Screen or component | User can submit |
| Error handling | Map error responses | Error response rules | Failure returns a safe message |
| Tests | Cover happy + failure paths | Test suite | Suite passes |

**Guiding question:** *What is the smallest useful piece of work that can be completed,
tested, and reviewed without building the entire feature?*

**The one-outcome rule:** if one task has more than one major outcome, split it. A task
that creates a database model, endpoint, screen, **and** tests is not one task — it is a
mini-project.

**A useful task answers five questions:**
1. What should be changed?
2. Why is it needed?
3. Which spec does it come from?
4. How will you know it is done?
5. What should **not** be changed?

**Why the scoring rule is its own task (A-007), separate from its screen (A-008).** They are
one vertical slice conceptually, and splitting them is deliberate: the scoring module is the
core subdomain and the only place FF-002 has anything to check. Merging it into the screen task
is exactly how a scoring rule ends up inside a view, and no test would catch it.

---

## Avoid these task words

"handle everything" · "make it robust" · "finish the feature" · "improve the app" ·
"clean this up" · "make it better"

They sound helpful but leave too much room for interpretation.

| Weak task | Better task |
|---|---|
| Build login. | Create a `POST /auth/login` endpoint that accepts email and password, validates input, checks the password hash, and returns a session token on success. |
| Add errors. | Return a safe invalid-credentials error without revealing whether the email exists. |
| Make sessions work. | Create session expiration logic and reject expired tokens. |
| Build task assignment. | TASK-04: Add task assignment using `assignee_id`, enforce project membership, update the create/update task API, and add tests for valid and invalid assignees. |

**Three phrases are specifically banned on this project**, because each one has a plausible wrong
reading that would pass review: *"score the assets"* (which scorer? — A-007 says deterministic,
ADR-005 says why), *"handle bad data"* (the seven rules in `data-and-integration-spec.md` §4 are
named, and handling six of them looks identical to handling all seven), and *"make the ranking
explainable"* (BR-002 is a database constraint, not a presentation goal).

---

> Blueprint: blueprints/02-tasks/01-planning/agent-task-list.md
