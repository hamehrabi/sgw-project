# technical-spec.md — Technical Specification

> **Purpose (Ch. 4 §4.4):** Defines architecture, data, APIs, security, and errors.
> **When you use it:** Before task planning and coding.
> **Sources:** Ch. 7 (10-section template), Ch. 8 (architecture), Ch. 9 (data/API/integration),
> Ch. 21 (security), Ch. 22 (reliability), Ch. 27 §27.6 (frontend components),
> Appendices C, D, E.

A PRD says *what product you want*. This says *how the system should be structured so that
product can be built safely and consistently*.

**Version:** TECH v3.0 · **Owner:** Tech lead (not yet named) · **Date:** 2026-08-15

---

## Contents

1. [System Overview](#1-system-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Frontend Requirements](#3-frontend-requirements)
4. [Backend Requirements](#4-backend-requirements)
5. [Database Requirements](#5-database-requirements)
6. [API Requirements](#6-api-requirements)
7. [Security Requirements](#7-security-requirements)
8. [Performance Requirements](#8-performance-requirements)
9. [Error Handling & Reliability Requirements](#9-error-handling--reliability-requirements)
10. [Integration & Versioning Requirements](#10-integration--versioning-requirements)
11. [Testing Approach](#11-testing-approach)
12. [Deployment Approach](#12-deployment-approach)
13. [Open Decisions](#13-open-decisions)
14. [Guardrail Checklist & Prompts](#14-guardrail-checklist)

---

## 1. System Overview

| Field | Value |
|---|---|
| System name | SGW Resilience Platform — version one |
| Purpose | An internal web dashboard that loads prepared storm scenarios from uploaded files, joins them into one record per asset, ranks those assets by risk with stated reasons, and records every recommendation it makes and every decision a person takes. |
| Primary users | The operations manager and the dispatcher. *Admin* is a role held by one of them, not a separate user group. |
| Core capabilities | Scenario upload and switching · joined asset view · ranked risk list with reasons · planning view · dispatch board · append-only decision record |
| System boundary | This system includes **the upload and parse, the asset join, the risk scoring, the four views, and the decision record**. This system does **not** include **any connection to SGW's GIS, maintenance, weather or field-ops systems; any outbound command to any system whatsoever; the water early-warning ability; the summary writer; the crew app; and route planning**. |
| External dependencies | **One:** a hosted OpenAI model that phrases computed reasons (ADR-009). It is off the critical path — the ranking renders without it. CON-005 still removes every live source system; the only data input is a set of files an admin uploads. |
| Assumptions | That the prepared data resembles SGW's real data including its seven measured defects; that four capabilities fit in about a week (Q-008); and that the baseline these workflows must beat is roughly what the source PRD estimated, which nobody has measured (Q-018). |

> A good system overview prevents a common AI coding problem: the assistant builds more
> than you asked for because the system boundary was unclear.

---

## 2. Architecture Overview

| Item | Decision |
|---|---|
| Architecture style | **Modular monolith** — one deployable process, five named modules, a one-directional import rule between them (ADR-001). |
| Main components | Loader · Store · Scoring module · API layer · Views. One background worker, for the scenario parse only. |
| Responsibility of each component | **Loader**: validate, parse, match assets across their differing codes, apply the seven defect rules. **Store**: hold one record per asset with source and age, plus the append-only decision record. **Scoring**: produce a rank and its reasons per forecast revision, and nothing else. **API layer**: authenticate, authorise, and serve. **Views**: render, and never compute a score. |
| Data flow | Admin uploads → loader validates and parses in a background job → store holds the joined records → scoring produces ranks and reasons per revision → API layer checks identity and role, then serves → views render. Every ranking served and every decision taken appends a row to the decision record. |
| State ownership | The database owns everything durable. Nothing that matters lives in process memory, so a restart is not an incident. The **scenario** is the scoping root: every other record belongs to exactly one. |
| Trade-offs | Recorded in full in [ADR-001](../05-architecture/architecture-decisions/ADR-001-modular-monolith.md). In short: nothing at runtime enforces the module boundary — it holds because FF-001 and FF-002 fail the build, and until that gate is wired it holds only because people are careful. A simple monolith would have been faster and would have disarmed both guards on day one. |

### Choosing the style (Ch. 8 §8.3, §8.7)

| Style | Best use | Strength | Cost | Beginner warning |
|---|---|---|---|---|
| Monolith | Small tools, MVPs, internal apps. | Fast to build and easy to run. | Can become messy without internal structure. | Do not allow all logic to mix in one file or layer. |
| **Modular monolith** | Growing SaaS apps, dashboards, business systems. | Balanced structure, simple deployment. | Requires discipline around modules. | You must define modules and respect their boundaries. |
| Microservices | Large systems with independent teams and scaling needs. | Independent scaling and ownership. | More infrastructure and coordination. | Do not choose it only because it sounds advanced. |

**Decision questions (Ch. 8 §8.2)**

| Question | What you are checking |
|---|---|
| How large is the first version? | A small product usually needs a simple structure first. |
| How many people will work on it? | More developers may need clearer module boundaries. |
| Will features change often? | Frequent changes require separation between areas. |
| How much deployment complexity can you manage? | Microservices create operational responsibilities. |
| What must be protected? | Security-sensitive features need strong boundaries. |

> **Practical guidance (Ch. 8 §8.7):** for most beginner-to-intermediate projects, start
> with a **modular monolith** — structure without premature deployment complexity.

### Component boundaries (Ch. 8 §8.4)

Three questions per component: *What does it own? What does it need from others? What is it
forbidden to do?*

| Component | Owns | Must **not** do |
|---|---|---|
| User Interface | Screens, forms, display states, user actions. | Contain database queries or hidden business rules. |
| API Layer | Routes, request validation, response formatting. | Hide complex domain logic in route handlers. |
| Domain Module | Business rules and core decisions. | Depend directly on screen layout. |
| Data Layer | Database access, queries, persistence. | Decide user-facing business behavior. |

**This system's components, against that model** — the mapping FF-001 and FF-002 actually check:

| Component | Owns | Must **not** do |
|---|---|---|
| Views | Rendering, the five states, what the user is offered. | Compute a score, compute a rank, or import the scoring module (FF-002). |
| API layer | Identity, role checks, request validation, response shape. | Contain a scoring rule or a matching rule. |
| Scoring module | The risk score, the rank, and the reasons behind them. | Read a request, know about a screen, or write anywhere except its own results. |
| Loader | Parsing, the seven defect rules, matching assets across differing codes. | Score anything. A record it cannot match is flagged for a person, never resolved by a guess. |
| Store | Durable state, and the constraints that make BR-002, BR-003 and BR-004 true. | Decide user-facing behaviour. |

> **Architecture rule:** a boundary is useful only when you can tell whether a piece of
> code belongs inside or outside it.

### Text architecture diagram (Ch. 8 §8.5)

Use large labels, simple boxes, clear arrows, and short names.

```
[ Browser / Client ]
        |
        v
[ API Layer ]  --- validates request, checks auth
        |
        v
[ Domain / Service Modules ]  --- business rules
        |
        v
[ Data Layer ] ---> [ Database ]
        |
        +--------> [ External Services ]
        +--------> [ Background Jobs / Queue ]
```

| Diagram element | Use it to show |
|---|---|
| Box | A component, module, service, database, or external system. |
| Arrow | A dependency or communication path. |
| Boundary line | Where one responsibility area ends and another begins. |
| Short label | The purpose of the component, not every implementation detail. |

**One arrow in the diagram above does not exist in this system.** There is no
`[ External Services ]` edge, at any version, in either direction — CON-005, REQ-R-003 and
BR-005 remove it, and its absence is the safety property the whole design rests on. The
`[ Background Jobs ]` edge exists for exactly one job: the scenario parse.

### Architecture decisions

Record every significant choice as an ADR → [`decisions.md`](../05-architecture/decisions.md)

---

## 3. Frontend Requirements

**The interface specification is not written here.** It is written once, in
[`frontend-component-spec.md`](frontend-component-spec.md) — the component table, the
per-component template, the five states every data-bound component must handle, and the
frontend requirement areas (screens, form fields, UI states, user actions, accessibility).

The same rule as §5, §6 and §10 below. One empty component table filled twice, in the same
round, from two templates that have already drifted apart, leaves the build agent two of them
to choose between and nothing saying which one the screen was built from.

| What you need | Where it is |
|---|---|
| Every component, its purpose, the data it needs, its states and its rules | `frontend-component-spec.md` — component table |
| The full specification of one component | `frontend-component-spec.md` — per-component template |
| Loading, success, empty, error, permission-denied | `frontend-component-spec.md` — the five states |
| Screens, form fields, UI states, user actions, accessibility basics | `frontend-component-spec.md` — frontend requirement areas |

**What belongs here instead:** the interface decisions that are architectural rather than
visual — what renders on the server and what renders in the browser, where client state lives
and who owns it, what the interface is allowed to assume about the API.

| Cross-cutting interface decision | Consequence elsewhere in this document |
|---|---|
| The reasons behind a rank arrive **in the same response** as the rank, never on a second request. | It fixes the shape of `GET /risks` (§6) and bounds its page size, because a separate fetch makes "a rank on screen with no reasons" a reachable state — which is exactly what BR-002 forbids. |
| No permission is enforced in the browser alone; the interface hides controls **as well as**, never instead of, the server refusing them. | Every row of §7.2 needs a server-side deny test, not a hidden button (§11 Security). |
| The interface is a module inside one deployable process (ADR-001), not a separately deployed client. | It removes a network boundary the design would otherwise have to specify, and it is what makes FF-002 — no view imports the scoring module — checkable in one codebase rather than across two. |

> **Security rule (Ch. 27 §27.7):** hiding a button in the frontend is helpful for the user
> interface, but it is **not security by itself**. Enforce permissions on the server.

---

## 4. Backend Requirements

| Area | Decision |
|---|---|
| Business logic | The scoring module owns the rank and its reasons, and nothing else computes either. The loader owns matching and validation. A rule that lives in two places is a rule that will disagree with itself. |
| Authorization | Server-side, on every endpoint, in a fixed order: signed in → role on the action's allow-list. **There is no tenant check**, because there is one organisation — recorded here so its absence is visible rather than assumed missing. |
| Validation | At the boundary, before any write. The seven defect rules run at **load** time, not at read time — a defect caught at read is a defect already stored. |
| Service layer | Scoring is reachable only through the API layer; no view imports it (FF-002). |
| Background jobs | One: the scenario parse. Nothing else runs outside a request. |
| Integrations | None, at any version of this build. |

**Examples (Ch. 7 §7.5)**

| Backend area | Example decision |
|---|---|
| Business logic | A task cannot be marked complete if it has no title. |
| Authorization | Only workspace members can view tasks in that workspace. |
| Validation | The backend rejects invalid due dates and missing required fields. |
| Service layer | Task creation is handled by a task service, not scattered across routes. |
| Background jobs | Daily reminder jobs run separately from normal requests. |
| Integrations | Email notification service is called only after task creation succeeds. |

> **Backend discipline:** the backend must never simply accept what the frontend sends. It
> enforces the rules. Write backend rules in plain language first — each rule later becomes
> a task, a test, and then code.

---

## 5. Database Requirements

**The database design is not written here.** It is written once, in
[`../06-api-and-data-design/database-design.md`](../06-api-and-data-design/database-design.md),
a round earlier — entity model, schema, ownership and isolation rules, sensitive fields,
retention, migration, and file storage.

Do not restate any of it below, and do not summarise it here either — a summary of a schema is
still a second copy. Two copies of a schema is the drift this whole kit exists to prevent:
they disagree within a week, both look authoritative, and nothing tells the reader which one
the code was built from.

| What you need | Where it is |
|---|---|
| Entity model, and the rule that must always be true of each | `database-design.md` §1 |
| Schema, keys, constraints, indexes | `database-design.md` §3 |
| Ownership and isolation — which query is scoped by what | `database-design.md` §5 |
| Sensitive fields, storage and logging rules | `database-design.md` §6 |
| Retention and deletion | `database-design.md` §7 |
| Migration reversibility | `database-design.md` §8 |

**What belongs here instead:** anything about the database that only makes sense next to the
rest of the technical specification — a store chosen because of an architecture decision, a
constraint the schema imposes on deployment, a performance limit that comes from the data
shape rather than from the data model.

| Cross-cutting database decision | Consequence elsewhere in this document |
|---|---|
| BR-004 is enforced by **trigger**, not by column constraint or by grant: `BEFORE UPDATE` and `BEFORE DELETE` on `decision_records` abort the statement (ADR-004, CHG-002). | This reaches migrations rather than deployment. A migration that drops either trigger removes BR-004's only enforcement, and no functional test would notice. The migration checklist treats removing one as requiring a superseding ADR, and FF-004 fails the build if either is absent. |
| The store is embedded — one file, in-process, **single writer** (ADR-002). | The scenario parse and an operator's decision can contend for the write lock. At 50 users this is invisible; it is also the first assumption that stops being true, and its revisit trigger is written into ADR-002 rather than left to be discovered. |
| Everything is scoped by `scenario_id`, and several scenarios coexist. | Every read in §6 carries the scenario, and a missing scope is a correctness bug rather than a slow query — two storms blended into one ranking would look plausible. |

---

## 6. API Requirements

**The API contract is not written here.** It is written once, in
[`../06-api-and-data-design/api-specification.md`](../06-api-and-data-design/api-specification.md),
a round earlier — endpoint index, per-endpoint contracts, status code principles, contract
rules, validation rules, and versioning.

Same reason as §5. Repeating the endpoint index or the endpoint template here means filling
the same table twice, rounds apart, and leaving the build agent two of them to choose between.

| What you need | Where it is |
|---|---|
| Every endpoint, its requirement, and its permission | `api-specification.md` — endpoint index |
| The full contract for one endpoint | `api-specification.md` — endpoint template |
| Which status code means what, and what it must not reveal | `api-specification.md` — status code principles |
| Validation rules | `api-specification.md` — validation rules |
| Breaking-change policy | `api-specification.md` — versioning and compatibility |

**What belongs here instead:** the API decisions that are architectural rather than
contractual — where the boundary sits, what is synchronous and what is not, what the API
promises about consistency.

| Cross-cutting API decision | Consequence elsewhere in this document |
|---|---|
| The upload is **asynchronous**: the request returns once the files are accepted, and parsing happens in the background job. | §9.5 owns the job's states, and the interface needs an *uploading → parsing → ready or failed* progression rather than one spinner. |
| Every read is served from stored results, never computed inside the request. | A re-rank is a write that produces a new forecast revision; reads then serve it. This is what makes REQ-NF-001's two limits separable — one bounds the re-rank, one bounds the read. |
| No endpoint is idempotent by accident: the decision endpoint returns `409` on a second attempt rather than overwriting. | BR-004 holds at the API boundary as well as in the store, so a retrying client cannot quietly rewrite an audit row. |

---


## 7. Security Requirements

> **Beginner rule (Ch. 21):** do not write "make it secure." Write the exact security
> behavior you expect. A clear rule can be reviewed, tested, and implemented. A vague
> security wish cannot.
>
> **You decide the security policy in the specification. The agent does not.**

### 7.1 Authentication (*who are you?*)

| Area | Requirement |
|---|---|
| Account access | **Email and password, with a server-side session** (ADR-003). No external identity provider, no OAuth, no magic link. |
| Session lifetime | **240 minutes idle, 12 hours absolute** (ADR-006), both checked server-side on every request. Chosen for 12-hour control-room shifts: an operator logged out mid-storm is a safety problem, and the platform is read-only toward the grid, so a stale session's blast radius is a view. **Admin actions re-authenticate regardless of session age.** |
| Password handling | Never stored or logged in plain text; hashed only. |
| Account recovery | **An admin resets the password by hand**, setting a temporary one the user must change at next sign-in. No email is sent. Round 6 confirmed no external services, which removes email delivery and with it the reset-link flow this row previously specified (CHG-004, Q-024). |
| Logout | Access ends server-side, not only in the browser. A logout the server does not know about is a session still open. |
| Multi-factor (if any) | **None in version one** — no external service is permitted (CON-006). Recorded as **P1: TOTP, never SMS**. The exposure is accepted knowingly and bounded by ADR-006's re-authentication on admin actions. |

> **`SEC-` identifiers are DEFINED in
> [`security-specification.md`](../07-security-and-reliability/security-specification.md), and
> only there.** This section decides the authentication *model*; the numbered controls that
> enforce it have one home, and this is not it.
>
> This blueprint used to mint `SEC-A-001` in a table of its own — the same row
> `security-specification.md` opens with — so **every workspace this kit produced defined that
> identifier twice**, and the day one copy was edited the two disagreed about what the control
> was. Cite the id here; do not restate the row.

### 7.2 Authorization / RBAC (*what are you allowed to do?*)

| Action | Admin | User |
|---|---|---|
| Upload a prepared scenario | Yes | No |
| Delete or replace a scenario | Yes | No |
| Switch between loaded scenarios | Yes | Yes |
| View the joined asset view | Yes | Yes |
| View the ranked risk list and its reasons | Yes | Yes |
| Apply a forecast revision and re-rank | Yes | Yes |
| Record a crew placement | Yes | Yes |
| Accept, change, or reject a recommendation | Yes | Yes |
| Dismiss a false alarm | Yes | Yes |
| Read the decision record | Yes | No |
| Reset another user's password | Yes | No |
| Edit or delete a decision record | **No** | **No** |
| Send any command to a grid or water control system | **No** | **No** |

The last two rows are the point of the table rather than an afterthought. They are the only two
where the answer is *no* for every role including admin, and each is enforced structurally: the
first by a database grant the application does not hold (§5), the second by there being no
outbound path to build against (§2).

> A role table gives the agent a precise boundary. It does not need to guess whether a
> Member can invite users — the table already says no.

**Defensive authorization pattern (Ch. 21 §21.3)** — specify the *order* of the checks, not
the code that runs them. State, per protected action: deny when there is no signed-in user;
deny when the resource belongs to a tenant the user is not in; allow only when the user's role
is on an explicit allow-list. Written that way the rule is testable before any code exists —
one test per denial, one for the allow. The worked example at the end of this file shows the
same three checks as a filled specification.

**The middle check is absent here, deliberately.** There is one organisation, so there is no
tenant to compare — the order is *signed in → role on the allow-list*, two checks rather than
three. It is written down because a missing check and a check nobody wrote look identical in
code, and the day multi-tenancy arrives this line is what says where it goes.

### 7.3 Input validation

Validation happens at **system boundaries**. Do not rely only on the frontend — API
requests can come from outside the visible interface.

| Input | Validation rule | Error behavior |
|---|---|---|
| Uploaded scenario files | Within the size limit (Q-017); type on the allow-list, verified by content inspection rather than extension; parses; passes the seven defect rules in `data-and-integration-spec.md` §4. | Refuse before parsing where possible, naming the file and the reason. Every already-loaded scenario is left untouched. |
| Decision note | Required when the decision is *change* or *reject*; trimmed; up to 2000 characters. | Validation error naming the field, with the typed note kept on screen. |
| `forecast_revision` parameter | Integer; must exist for that scenario. | `400` for a non-integer, `404` for an unknown revision. **Never a silent fallback to the current revision** — that shows one ranking to a reader who believes they are looking at another. |

### 7.4 Data protection

| Area | Question | Rule |
|---|---|---|
| Data minimization | Do you need this data? | Do not collect personal data not needed for the feature. |
| Storage | How should data be stored? | Sensitive account data must use approved storage mechanisms. |
| Transport | How does data move? | Private user data only through protected channels. |
| Logging | What must **not** be logged? | Never log passwords, tokens, reset links, or full secret values. |
| Retention | How long is data kept? | Follow the retention rule in the product specification. |

For this system specifically: the data named in CON-003 must not be stored at all — which data
that is remains open (Q-007) — asset locations and connections are logged as identifiers only,
damage locations are aggregated to neighbourhood level in any log or export (REQ-NF-007), and
the retention period for the decision record is still unset (Q-015).

### 7.5 Secrets management

- Never hardcode a secret into source code, templates, screenshots, logs, or examples.
- Use placeholders in documentation → [`../.env.example`](../../.)
- Document where each real value is configured → [`../ops/deployment-checklist.md`](../../07-ops/01-deployment/deployment-checklist.md)

| Secret | Where configured | Must never appear in | Code reference |
|---|---|---|---|
| Session signing key | environment variable | source, logs, error messages, client responses | by configuration name only |
| Password hashing parameters | environment variable | source, logs, error messages, client responses | by configuration name only |
| Path to the database file | environment variable | logs, error messages, client responses | by configuration name only |

**The two separate database credentials specified here before Round 5 are gone** (CHG-002). An
embedded store has no roles to separate, so there is no application credential and no migration
credential — the database is a file, and access to it is filesystem access. That is a real loss:
the earlier design separated *who may change the rule* from *who may change the data*, and this
one does not. ADR-004 keeps the rule itself in the store with triggers, and names that residual
weakness rather than papering over it.

The database file is never committed to version control, and its path is configuration rather
than a constant.

### 7.6 Secure error handling

| Problem | Unsafe response | Safer response |
|---|---|---|
| Login failed | Detailed account or password reason. | "The email or password is incorrect." |
| Access denied | Internal permission rule details. | "You do not have permission to perform this action." |
| Server failure | Stack trace or database error. | "Something went wrong. Please try again later." |
| Validation failure | Raw parser or framework error. | "The submitted value does not match the required format." |

### 7.7 Per-feature security specification

```
Feature:        [name]
Requirement ID: SEC-###

Authentication:  [who must be signed in]
Authorization:   [which roles may perform this]
Role assignment: [what roles can be granted, by whom]
Validation:      [required fields, formats, duplicate rules]
Data protection: [what must not be exposed or logged]
Secure errors:   [what unauthorized users receive]
Testing:         [allowed actor, disallowed actor, invalid input, duplicate, safe error]

Acceptance criteria:
1.
2.
```

The filled blocks for this system are written in
[`security-specification.md`](../07-security-and-reliability/security-specification.md) in
Round 6, because that is where `SEC-` identifiers are defined. Filling them here would mint the
same ids in two files.

### 7.8 Security review checklist (Ch. 21 §21.8)

- [x] Every protected feature has an authentication requirement.
- [x] Every sensitive action has an authorization rule.
- [x] Role permissions are documented in a table.
- [x] User input rules are specific and testable.
- [x] Backend validation is required, not only frontend validation.
- [x] Sensitive data is not logged or returned unnecessarily.
- [x] Secrets are not stored in source code or examples.
- [x] Error messages are safe for users and useful enough for recovery.
- [ ] Security requirements are linked to tests.
- [ ] The AI agent has clear instructions not to add unapproved access paths.

The two unticked boxes are unreached rather than unmet: tests are written in Round 7 and the
agent instructions in Round 8. Ticking either now would claim work nobody has done.

Full review pass → [`../review/security-review.md`](../../05-review/02-checklists/security-review.md)

---

## 8. Performance Requirements

Measurable only. Avoid "the app should be fast."

| Workflow | Metric | Target | Expected data size |
|---|---|---|---|
| Re-rank after a forecast change | Time from applying the change to the updated ranking on screen | **Under 5 s for 220 assets** | The fixture: 220 assets, ~5,000 forecast rows |
| Page load | Time to first usable screen | **Under 2 s** | As above |
| Reason panel open | Time from click to reasons visible | **Under 300 ms** | As above |
| Any critical action under storm conditions | Number of actions to complete it | Two or fewer | — |

| Weak statement | Stronger requirement |
|---|---|
| "The dashboard should load fast." | "The task dashboard should load within 2 seconds for a workspace with up to 1,000 tasks." |
| "Search should be quick." | "Task search should return results within 1 second for common filters." |
| "The app should support many users." | "The first version should support 50 active users in one workspace without visible slowdown." |

> **Performance tip:** set realistic targets for the version you are building now.
> Overengineering performance too early makes the system harder to finish.

**Performance risks to check in review (Ch. 20 §20.5)**

| Risk | What to check |
|---|---|
| Repeated queries | Does the code query the database inside a loop? |
| Overfetching | Does it load fields or records that are not needed? |
| Slow external calls | Does one request depend on many network calls? |
| Missing limits | Can a user request unlimited records? |
| Blocking work | Should heavy work move to a background job? |

Performance was offered as a driving characteristic in Round 4 and **not chosen**, so these are
requirements to pass rather than a shape to build around. No fitness function guards them, and
[`fitness-functions.md`](fitness-functions.md) says so explicitly.

---

## 9. Error Handling & Reliability Requirements

> Reliable software is not software that never fails. It fails in **controlled,
> understandable, and recoverable** ways.
>
> **Spec rule (Ch. 22):** write reliability as a specific rule: *"If X fails, the system
> must do Y, record Z, and show message M."*

### 9.1 Error handling table (Ch. 7 §7.10)

| Error situation | Expected behavior |
|---|---|
| Missing required field | Reject, explain the missing field, keep user input on screen. |
| Not signed in | Return 401 and ask the user to sign in. |
| No permission | Return 403 and explain the user cannot access the resource. |
| Resource not found | Return 404 with a safe message. |
| External service failure | Retry if safe, otherwise show a temporary failure message. |
| Unexpected server error | Return a general error message and log details internally. |
| A prepared file is missing or malformed | Show the last good picture, marked stale and dated, and name the failing file. Never an empty screen and never a bare error page — the storm does not pause for a broken load (REQ-NF-003, AC-002). |
| A scenario parse fails partway | Create no scenario at all and leave every loaded scenario untouched. A half-loaded storm is worse than a refused one, because it looks complete. |
| A second decision on the same recommendation | Return 409 and show the decision that already exists. Never overwrite (BR-004). |
| An asset cannot be matched across source systems | Load it flagged `needs review` and show it to a person. Never merge on a guess, and never drop it silently. |

### 9.2 Failure sources (Ch. 22 §22.2)

| Failure source | Question to ask | Example recovery rule |
|---|---|---|
| User input | Missing, invalid, or unexpected data? | Reject with field-level validation messages. |
| Database | Write fails or takes too long? | Do not show success. Return a retry-safe error and log the failure. |
| Network | Request times out? | Apply a timeout rule and let the user retry safely. |
| External service | Third-party API unavailable? | Queue the action for later or mark it pending. |
| Background job | Job fails after the user left the page? | Store job status, retry if safe, expose the final result. |

The *external service* row does not apply to this system at any version — there is none (§1).

### 9.3 Failure states

```
- Failure state: [name]
  - Trigger:        [what causes it]
  - Recovery path:  [what the system does next]
  - User message:   [plain language, safe, with a next action]
  - Log event:      [EVENT_NAME with safe context fields]
  - Test case:      TEST-###
```

| Error state | Recovery path | What to test |
|---|---|---|
| Uploaded file over the size limit or off the allow-list | Refuse before parsing, naming the file. | An over-size file is refused and no scenario row is created. |
| Scenario parse fails partway | Abandon the whole load; leave loaded scenarios untouched; report the failing file. | A file that is valid for three of five inputs creates no scenario, and the previously loaded storm still ranks. |
| A prepared data file goes missing after load | Serve the last good picture with the staleness banner and its age. | Removing a file leaves every screen readable, dated, and non-empty. |
| Wrong credentials | Safe message that does not reveal which field was wrong. | A wrong email and a wrong password produce the same message. |
| Expired session | Return to sign-in, preserving the intended destination. | A protected route redirects rather than erroring. |
| Database write fails on a decision | No success is shown; the operator's note is kept on screen; the failure is logged. | A simulated write failure never shows a recorded decision, and the note survives. |

### 9.4 Timeout and retry rules (Ch. 22 §22.5)

| Decision | Rule |
|---|---|
| Timeout | Set a maximum wait so the system never hangs forever. |
| Retry count | Limit retries. Do not retry endlessly. |
| Retry delay | Wait briefly before retrying instead of hammering the service. |
| Idempotency | Only retry operations that will not create duplicate harmful effects. |
| Stop condition | Define when the system gives up and reports a controlled failure. |

| Operation | Safe to retry? | Max retries | Delay | On give-up |
|---|---|---|---|---|
| Scenario upload, by the person | Yes | manual | — | No scenario is created and nothing partial remains |
| Scenario parse, automatically | **No** | 0 | — | Load fails whole, names the file, loaded scenarios untouched |
| Decision write | **No** | 0 | — | Error shown, note kept, no row written; a retry that succeeded twice would be two audit rows for one decision |
| Read endpoints | Yes | 1, client-side | 1 s | Show the last good picture with the staleness banner |

> Uncontrolled retry logic creates new problems: duplicate records, hidden failures, and
> hammered dependencies.

### 9.5 Background jobs and queues (Ch. 22 §22.6)

| Requirement | Definition |
|---|---|
| Job name | Parse prepared scenario |
| Trigger | An upload that has been accepted — size and type already checked |
| Input data | The stored upload identifier and the scenario metadata. **Never the file contents in the job payload.** |
| Retry rule | None. A malformed file is a fact about the file, not a transient error. |
| Failure state | `failed`, with the failing file named. No scenario is created. |
| User visibility | The admin sees *uploading → parsing → ready* or *failed*, with the reason. A single undifferentiated spinner would hide which stage broke. |

### 9.6 Logging requirements (Ch. 22 §22.4)

| Log requirement | Good practice |
|---|---|
| Event name | Clear names such as `AUTH_LOGIN_FAILED`, `JOB_RETRY_SCHEDULED`. |
| Severity | Use `info`, `warning`, `error`, `critical` consistently. |
| Request / correlation ID | Attach a request ID so related events can be traced. |
| Safe context | User ID, role, action — never secrets or raw credentials. |
| Failure reason | Error type or safe error code, not a sensitive dump. |
| Outcome | Whether the system recovered, retried, queued, or stopped safely. |

**Must never be logged:** passwords · tokens · reset links · full secret values · raw
payment data.

For this system, three more join that list: full asset locations and connections (log the
`asset_id` instead), household-level damage locations (aggregate to neighbourhood), and the
contents of an uploaded file. See `database-design.md` §6.

**Structured log example**
```json
{
  "level": "error",
  "event": "report_export_failed",
  "request_id": "REQ-20491",
  "user_id": "USER-118",
  "project_id": "PROJ-42",
  "reason": "database_timeout",
  "duration_ms": 12000,
  "recovery_action": "user_can_retry"
}
```

### 9.7 User-facing error messages (Ch. 22 §22.7)

| Weak message | Better message | Why it is better |
|---|---|---|
| `DatabaseError: connection refused` | "We could not save your changes right now. Please try again." | Understandable; reveals no internals. |
| `Invalid request` | "Please enter a project name before saving." | Tells the user exactly what to fix. |
| `Unauthorized` | "You do not have permission to edit this project." | Explains without exposing security details. |
| `Job failed` | "Your report could not be generated. You can try again or contact support." | Gives a next action. |

### 9.8 Reliability definition of done (Ch. 22 §22.8)

- [x] All expected failure states are handled.
- [x] Logs are safe and useful.
- [x] User-facing errors are clear.
- [ ] Tests cover normal behavior **and** failure behavior.

Tests are written in Round 7. The box stays unticked until they exist.

---

## 10. Integration & Versioning Requirements

**The integration rules are not written here.** They are written once, in
[`../06-api-and-data-design/data-and-integration-spec.md`](../06-api-and-data-design/data-and-integration-spec.md)
§5 and §6 — provider, data in and out, timeout, retry rule, idempotency, failure behaviour,
secrets, rate limits, and the breaking-change policy.

The same rule as §5 and §6. An integration table restated here would let one outbound call
carry one timeout in this document and a different one three files away.

| What you need | Where it is |
|---|---|
| Provider, purpose, data sent and received, what is stored | `data-and-integration-spec.md` §5 |
| Timeout, retry rule, idempotency, failure behaviour | `data-and-integration-spec.md` §5 |
| Secrets handling and known rate limits | `data-and-integration-spec.md` §5 |
| Current version, breaking-change policy, compatibility notes | `data-and-integration-spec.md` §6 |

**What belongs here instead:** what an outside dependency does to *this* system's shape — a
service whose failure takes a whole capability with it, a call on a path the user waits on, a
provider whose rate limit becomes a design constraint rather than a configuration value.

| Dependency | What its failure costs, and what that forces here |
|---|---|

**This table is empty, and that is the finding.** Version one depends on no outside service, so
nothing outside it can take a capability down. That is worth stating rather than leaving blank:
it is the reason `data-and-integration-spec.md` describes a file boundary rather than a network
one, and it is the property that disappears the day the first live connection is made.

---


## 11. Testing Approach

| Level | Strategy |
|---|---|
| Unit | Scoring: a rank is never produced without at least one reason; ordering is total and stable across equal scores. Loader: one test per defect rule in `data-and-integration-spec.md` §4. |
| Integration | Upload → parse → join → rank, against a fixture carrying all seven defects on purpose. An earlier `forecast_revision` returns the earlier order unchanged. |
| End-to-end | The two flows in `product-spec.md` §10, each including its failure path — not only the happy one. |
| Security | One deny test per *No* in §7.2, plus the allow. The database refuses an `UPDATE` on `decision_records` issued as the application role (FF-004) — asserted against the database, not the service layer. |
| Performance | REQ-NF-001's two limits, once Q-012 gives a real number and Q-017 gives a real dataset size to run against. |
| Regression | The five fitness functions, once a pipeline exists to run them (Round 7). |

→ [`../tests/test-plan.md`](../../03-tests/01-plan/test-plan.md)

---

## 12. Deployment Approach

| Area | Summary |
|---|---|
| Environments | Round 8 decides. |
| Configuration | Environment variables only. No secret in source, at any point, including examples (§7.5). |
| Migrations | Up and down for every change; schema deployed before the code that depends on it (`database-design.md` §8). |
| Rollback | Round 8 decides. |
| Monitoring | Round 8 decides. |

**Two requirements are already fixed and do not wait for Round 8** (CHG-002). First: every
deployment must verify that both `decision_records` triggers are present after migrations run —
BR-004's only enforcement now lives there, and a migration that drops one removes it silently
(ADR-004). Second: a backup is a copy of one database file plus the uploaded scenario files,
which is what makes ADR-002's operational simplicity real rather than claimed — Round 8's
recovery plan is written against that shape.

→ [`../ops/deployment-checklist.md`](../../07-ops/01-deployment/deployment-checklist.md) ·
[`../ops/maintenance-notes.md`](../../07-ops/03-maintenance/maintenance-notes.md)

---

## 13. Open Decisions

*Unresolved choices that must **not** be guessed by the AI agent.*

→ [`open-questions.md`](../01-intent/open-questions.md)

> **`Q-` rows are DEFINED in `open-questions.md`, and only there.** This table CITES the
> questions that block parts of this specification — the id and the section it blocks, never
> the question restated with its own owner and status. A second home for a question row is a
> second thing to keep correct, and the day the register closes one, a copy here would still
> say open.

| Question ID | Spec section IDs it blocks |
|---|---|
| Q-007 | §7.4 |
| Q-008 | §1 assumptions |
| Q-012 | §8 |
| Q-013 | §3, and the accessibility notes in `frontend-component-spec.md` |
| Q-015 | §7.4 |
| Q-017 | §7.3, §8, §9.4 |
| Q-019 | `runtime-and-scale.md` §4 |
| Q-021 | §7.1 session lifetime |
| Q-022 | §7.1 second factor |

---

## 14. Guardrail Checklist

**Before generating code, verify (Appendix C):**

- [x] Requirements are mapped to modules.
- [x] Data models are named.
- [x] API contracts are defined.
- [x] Error states are documented.
- [ ] Tests exist before implementation.
- [x] Security rules are explicit.
- [x] Open questions are not treated as assumptions.

**Chapter checklist (Ch. 7)**

- [x] You can explain the difference between a PRD and a Technical Specification.
- [x] You can write a simple system overview with boundaries and assumptions.
- [x] You can describe the architecture at the component level without overcomplicating it.
- [x] You can define frontend, backend, database, and API requirements clearly.
- [x] You can document security, performance, and error-handling expectations before coding.

**Architecture checklist (Ch. 8)**

- [x] Have you chosen an architecture style based on real project needs?
- [x] Have you defined the main components of the system?
- [x] Have you described what each component owns?
- [x] Have you identified what each component must not do?
- [x] Have you compared architecture trade-offs before deciding?
- [x] Have you written at least one ADR for the main architecture decision?
- [x] Have you created rules that an AI assistant can follow during implementation?

**Data & API checklist (Ch. 9)**

- [x] Core entities the system must remember are identified.
- [x] Relationships between entities are clear.
- [x] Database fields, keys, constraints, and indexes are planned.
- [x] Endpoint specs are written before implementation.
- [x] Request and response contracts are defined.
- [x] Validation rules are written before code is generated.
- [x] External integration behavior and failure handling are documented.
- [x] Versioning is considered before changing API contracts.

Every unticked box above is the same box: tests do not exist yet, and Round 7 writes them.
Nothing else in this document is unresolved for want of a decision.

---

**Next:** [`traceability.md`](../08-traceability/traceability.md) · [`decisions.md`](../05-architecture/decisions.md) ·
[`../tasks/task-index.md`](../../02-tasks/01-planning/task-index.md)

---

> Blueprint: blueprints/01-docs/04-technical-spec/technical-spec.md
