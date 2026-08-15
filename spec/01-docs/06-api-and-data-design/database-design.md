# Database Design

> Source: Ch. 7 §7.6, Ch. 9 §9.2–9.3, Appendix E.
> **Beginner rule:** a schema should make invalid data *harder to store*. Do not rely
> only on code to protect important rules.

---

## 1. Entity model (meaning before storage)

Identify what the system must remember, before you design tables.

| Entity | Purpose | Key fields | Relationships | Rule that must always be true |
|---|---|---|---|---|
| Asset | One substation, line, plant or pump, joined from the prepared files into a single record. | id, external_ids, type, location, connections, condition, condition_source, condition_observed_at, match_status | Belongs to one scenario. Has many risk scores and many damage reports. | A condition value never exists without its source and its age (BR-003). |
| Risk score | One asset's risk for one forecast revision, together with the reasons behind it. | id, asset_id, scenario_id, forecast_revision, score, rank, confidence, reasons, computed_at | Belongs to one asset and one scenario. | A rank cannot exist without at least one reason (BR-002). |
| Damage report | One observed damage during the storm, from the prepared scenario. | id, scenario_id, asset_id, repair_job_id, location, reported_at, reported_by, status, dismissed_by, dismissed_reason | Belongs to one scenario, optionally to one asset, and to at most one repair job. | A dismissed report carries who dismissed it and why (REQ-F-008). |
| Repair job | The work that answers one or more damage reports. | id, scenario_id, status, priority_rank, assigned_to, created_at, updated_at | Belongs to one scenario. Has one or more damage reports. | Two reports for the same location resolve to one job, never two (AC-007). |
| Decision record | Every recommendation the system made and every accept, change or reject a person made. | id, scenario_id, occurred_at, actor_user_id, kind, subject_type, subject_id, payload | Belongs to one scenario. References any other entity by type and id. | Append-only. No update and no delete path exists, for any role (BR-004). |
| User | A person using the platform, in one of exactly two roles. | id, name, email, password_hash, role, created_at | Acts on many decision records. | Email is unique; role is `admin` or `user` and nothing else. |
| Session | One signed-in period for one user, created at sign-in and ended server-side at sign-out or expiry. | id, token_hash, user_id, created_at, last_seen_at, ended_at | Belongs to one user. Scoped to no scenario — it is what permits reading any of them. | The session value itself is never stored, only its hash (Q-007). A session the server has ended or expired never authenticates again, whatever the browser still holds (SEC-A-002). |
| Scenario | One prepared storm, loaded by an admin, that everything else is scoped to. | id, name, source_note, loaded_by, loaded_at, forecast_revision, forecast_issued_at | Has many assets, risk scores, damage reports, repair jobs and decision records. | Everything read together belongs to one scenario; two scenarios never blend into one ranking. |
| Scenario upload | One attempt to load a prepared storm, from accepted files through to a scenario or a named failure. | id, status, uploaded_by, uploaded_at, storage_path, scenario_id, failed_file, failed_reason | Belongs to one user. Points at the scenario it produced, if it produced one. | A ready upload names its scenario; a failed one names the file that failed. Neither is ever both, and a scenario is referenced only once the parse has wholly succeeded. |

**User** and **Scenario** were derived, not named in Round 3. A permission model with two roles
requires a user record, and CON-005 with REQ-F-010 requires something that identifies which
prepared storm is loaded. Both are stated here so they can be corrected rather than discovered.

**Scenario upload was added by CHG-012, during TASK-002, for the same reason as Session.**
`technical-spec.md` §9.5 already specified the job in full — a stored upload identifier, the
states *uploading → parsing → ready* or *failed*, and a failure that names the file — and §9.1
requires that a parse failing partway creates **no scenario at all**. Those two together leave
the job's own state with nowhere to live: it cannot hang off a scenario row that deliberately
does not exist yet. The admin watching the panel, and the same admin after a page reload, are
both reading this table.

**Session was added by CHG-008, during TASK-001 rather than during the interview.** ADR-003
required a session created, checked, and ended server-side; ADR-006 twice described "a session
lookup per request against a local store"; ADR-002 held that nothing which matters lives in
process memory. Three accepted decisions therefore required a durable table that this section
did not define — the gap was found by the first task that had to build against it, which is
where §8 of `spec-change-log.md` says such gaps are expected to surface.

| Question | Your answer |
|---|---|
| What objects must the system remember? | The asset, the risk score with its reasons, the damage report, the repair job, and the decision record — the five named in Round 3 — plus the user and the scenario, both derived above. |
| What details describe each object? | The key fields in the table above, expanded field by field in §3. |
| How do objects relate? | Everything hangs off the scenario. Assets carry risk scores and damage reports; damage reports group into repair jobs; the decision record points at any of them by type and id rather than by foreign key, so an audit row survives the thing it describes. |
| What rule must always be true? | A rank is never stored without its reasons (BR-002), a condition never without its age (BR-003), and a decision record is never changed once written (BR-004). |

---

## 2. Entity definition template (Appendix E)

Copy per table.

```
Table: [name]
Purpose: [what real-world object or concept it stores]

Fields:
- id:          UUID, required, primary key
- owner_id:    UUID, required, foreign key -> users.id
- title:       string, required, max 120 chars
- description: text, optional
- status:      enum(todo, doing, done), required, default 'todo'
- due_date:    date, optional
- created_at:  timestamp, required
- updated_at:  timestamp, required

Primary key:      id
Relationships:    [one-to-one / one-to-many / many-to-many links]
Indexes:          owner_id, status, due_date
Constraints:      [uniqueness, foreign keys, required fields, allowed values]
Sensitive data:   [personal, confidential, or security-sensitive fields]
Migration notes:  [how schema changes will be applied safely]
Retention rules:  [how long data is kept and when it is deleted]
```

---

## 3. Schema

```
users
- id: string, primary key
- name: string, required
- email: string, required, unique              -- one account per address
- password_hash: string, required              -- never plain text (see §6)
- role: string, required, check in ('admin','user')
                                               -- REQ-R-001: exactly two roles. A third cannot
                                               --   arrive by accident, only by a migration
- created_at: datetime, required

sessions
- id: string, primary key
- token_hash: string, required, unique         -- CHG-008. The session VALUE is never stored, only a
                                               --   hash of it — the same rule as password_hash, and
                                               --   what keeps Q-007's "no session values in the
                                               --   database" true of a durable session table
- user_id: string, required, foreign key -> users.id
- created_at: datetime, required               -- ADR-006: the 12-hour absolute cap is measured here
- last_seen_at: datetime, required             -- ADR-006: the 240-minute idle limit is measured here
- ended_at: datetime, optional                 -- ADR-003: sign-out ends the session in the STORE. A
                                               --   logout the server does not know about is a
                                               --   session still open
  index: user_id

scenarios
- id: string, primary key
- name: string, required
- source_note: string, required                -- which prepared dataset this is, and where it came from
- loaded_by: string, required, foreign key -> users.id
- loaded_at: datetime, required
- forecast_revision: integer, required, default 0
                                               -- REQ-F-004: a forecast change increments this rather
                                               --   than overwriting what was ranked before
- forecast_issued_at: datetime, optional       -- CHG-013. From the manifest. REQ-NF-003(a)
                                               --   measures the data's age from here, so without
                                               --   it every screen's staleness claim has no
                                               --   origin. Nullable per §8: added, then backfilled,
                                               --   never required in one step. A scenario without
                                               --   one reports an unknown age, never a fresh one

scenario_uploads
- id: string, primary key                      -- CHG-012. §9.5's "stored upload identifier"
- status: string, required,
          check in ('uploading','parsing','ready','failed')
- uploaded_by: string, required, foreign key -> users.id
- uploaded_at: datetime, required
- name: string, required                       -- the scenario name the admin supplied
- source_note: string, required
- storage_path: string, required               -- a GENERATED identifier. Never any part of a
                                               --   supplied filename (security-spec §7)
- scenario_id: string, optional, foreign key -> scenarios.id
- failed_file: string, optional                -- REQ-NF-003: the failure names the file
- failed_reason: string, optional
- finished_at: datetime, optional
  check (status <> 'ready' or scenario_id is not null)
                                               -- a ready upload without a scenario is a
                                               --   success nobody can open
  check (status <> 'failed' or failed_file is not null)
                                               -- REQ-NF-003 again: a failure that does not
                                               --   name the file is an error page with extra
                                               --   steps
  index: uploaded_by, status

assets
- id: string, primary key
- scenario_id: string, required, foreign key -> scenarios.id
- external_ids: json, required                 -- the code each source system uses for this asset
- type: string, required, check in ('substation','line','plant','pump')
- location: json, required
- connections: json, optional
- condition: string, optional
- condition_source: string, optional
- condition_observed_at: date, optional
- match_status: string, required, check in ('matched','needs_review')
                                               -- AC-001: records the join could not resolve go to a
                                               --   person, never to a guess
- created_at: datetime, required
  check (condition is null
         or (condition_source is not null and condition_observed_at is not null))
                                               -- BR-003: a condition value may not be stored without
                                               --   its source and its age
  index: scenario_id, match_status

risk_scores
- id: string, primary key
- scenario_id: string, required, foreign key -> scenarios.id
- asset_id: string, required, foreign key -> assets.id
- forecast_revision: integer, required
- score: decimal, required
- rank: integer, required
- confidence: string, optional
- reasons: json, required
- computed_at: datetime, required
  check (json_array_length(reasons) >= 1)
                                               -- BR-002, the core subdomain's rule: the store refuses
                                               --   a rank that carries no reasons
  unique (scenario_id, asset_id, forecast_revision)
                                               -- REQ-F-004 / AC-005: re-ranking writes a new revision
                                               --   and the previous order stays retrievable
  index: scenario_id, forecast_revision, rank

repair_jobs
- id: string, primary key
- scenario_id: string, required, foreign key -> scenarios.id
- status: string, required, check in ('pending','in_progress','done')
- priority_rank: integer, optional
- assigned_to: string, optional
- created_at: datetime, required
- updated_at: datetime, required
  index: scenario_id, status

damage_reports
- id: string, primary key
- scenario_id: string, required, foreign key -> scenarios.id
- asset_id: string, optional, foreign key -> assets.id
- repair_job_id: string, optional, foreign key -> repair_jobs.id
                                               -- AC-007: one nullable foreign key IS the rule. A report
                                               --   cannot belong to two jobs, so no crew is sent twice
- location: json, required
- reported_at: datetime, required
- reported_by: string, required
- status: string, required, check in ('open','duplicate','dismissed')
- dismissed_by: string, optional, foreign key -> users.id
- dismissed_reason: string, optional
  check (status <> 'dismissed'
         or (dismissed_by is not null and dismissed_reason is not null))
                                               -- REQ-F-008: dismissal stays one action, but never
                                               --   becomes anonymous
  index: scenario_id, status, repair_job_id

decision_records
- id: string, primary key
- scenario_id: string, required, foreign key -> scenarios.id
- occurred_at: datetime, required
- actor_user_id: string, optional, foreign key -> users.id
                                               -- null when the actor is the system making a
                                               --   recommendation rather than a person deciding
- kind: string, required,
        check in ('recommendation','accept','change','reject','dismiss','placement')
- subject_type: string, required
- subject_id: string, required
- payload: json, required
  index: scenario_id, occurred_at, actor_user_id
                                               -- BR-004 is NOT a column constraint. See below.

  trigger decision_records_no_update
    BEFORE UPDATE ON decision_records -> ABORT   -- BR-004, ADR-004
  trigger decision_records_no_delete
    BEFORE DELETE ON decision_records -> ABORT   -- BR-004, ADR-004
```

**Where BR-004 is actually enforced.** Append-only cannot be expressed as a check constraint,
so it is enforced by the store refusing the statement: `BEFORE UPDATE` and `BEFORE DELETE`
triggers on `decision_records`, each aborting (ADR-004, CHG-002). The test that fails if this
stops working issues an `UPDATE` against `decision_records` and asserts the **database** refuses
it — not the application. A rule enforced only in the service layer is a rule the first refactor
removes while every functional test still passes.

This was originally specified as a role grant — the application role holding `INSERT` and
`SELECT` and neither `UPDATE` nor `DELETE`. ADR-002 chose an embedded store, which has no role
system, so the mechanism changed. **One property did not survive the change and is recorded
rather than glossed:** a grant separates the power to change the rule from the power to change
the data; a trigger does not, because anyone who can run a migration can drop it. The migration
checklist therefore treats removing either trigger as a change requiring a superseding ADR, and
FF-004 fails the build if either is missing.

**Where session expiry is enforced, since no constraint can express it** (CHG-008). Both of
ADR-006's limits are relative to the current time, so neither is a check constraint: a row valid
when written expires without being touched. They are enforced in **the single session check in
the API layer** — the one every route passes through — which refuses a session whose `ended_at`
is set, whose `last_seen_at` is older than `SESSION_IDLE_TIMEOUT_MINUTES`, or whose `created_at`
is older than `SESSION_ABSOLUTE_MAX_HOURS`, and refreshes `last_seen_at` otherwise. **STEST-002
is the test that fails if this stops working**, and it presents both an expired session and a
signed-out one because the two reach the check by different fields.

> ### The core subdomain's rule belongs HERE, not only in prose
>
> [`subdomain-map.md`](../01-intent/subdomain-map.md) names exactly one **core** subdomain — the
> one thing the product competes on. Whatever makes that thing correct is the rule most worth
> enforcing in the store, and the one a reader is most likely to assume is already handled.
>
> **Go through §1's "Rule that must always be true" column and, for each rule, write the
> constraint that enforces it above — naming the rule in a trailing comment.** A uniqueness
> constraint, a foreign key, a check constraint, a `not null`.
>
> The question to ask each rule is **"what would the store refuse?"** *A customer may hold only
> one active subscription* is a uniqueness constraint over the customer and that status. *A
> booking cannot end before it starts* is a check constraint. If the honest answer is "nothing
> would be refused", then the rule is not enforced, whatever the prose says.
>
> **If a rule cannot be expressed as a constraint, say where it IS enforced** — a service-layer
> check, a background job — and name the test that would fail if it stopped working. What is
> not allowed is a rule stated in §1 and enforced nowhere: a rule that lives only in a sentence
> is a rule the first refactor removes, and every functional test still passes without it.
>
> This section shipped with primary and foreign keys only, and every generated workspace
> inherited that shape — so a run could name what its product competes on and enforce it
> nowhere, with nothing to notice.

---

## 4. Schema concepts (Ch. 9 §9.3)

| Item | Meaning | Example |
|---|---|---|
| Primary key | Unique identifier for one row. | `users.id` |
| Foreign key | Field pointing to another table. | `tasks.project_id` |
| Unique constraint | Prevents duplicates. | `users.email` must be unique |
| Index | Makes common lookups faster. | index `tasks` by `project_id` |
| Status field | Controlled value showing state. | `todo`, `doing`, `done` |

---

## 5. Ownership and isolation rules

Every query must be scoped correctly. State the rule explicitly so the agent cannot
"forget" it.

| Entity | Scoping rule |
|---|---|
| Every entity | **No tenant scoping.** Round 3 confirmed a single organisation, so there is no `tenant_id` column anywhere and no query filters by one. Recorded here because adding one later reaches every read in the product — the absence is a decision, not an omission. |
| Asset, risk score, damage report, repair job | Every read and write is scoped by `scenario_id`. Two scenarios must never blend into one ranking. |
| Scenario | Written only by an admin (REQ-R-001). Readable by every signed-in user. |
| Decision record | Readable by an admin. Insert-only for every role including admin (BR-004). |
| Session | Scoped by `user_id`, never by scenario — a session grants a person access to the platform, not to one storm. Never readable through any endpoint, by any role: it is looked up by the API layer's session check and is never part of a response (CHG-008). |

---

## 6. Sensitive data

| Field | Sensitivity | Storage rule | Logging rule |
|---|---|---|---|
| `users.password_hash` | Credential | Hashed only — never plain text. | Never logged. |
| `sessions.token_hash` | Credential | Hashed only. The raw session value exists in the cookie and in the sign-in response, and **nowhere else** — not in this table, not in an error, not in a log (Q-007, CHG-008). | Never logged, in full or in part. Log `user_id`, never the session. |
| `users.email` | Personal data | Stored; unique index. | Logged only as `user_id`, never the address. |
| `assets.location`, `assets.connections` | Critical infrastructure | Stored. Reachable only by a signed-in user. | Never logged in full; logged as `asset_id` only. |
| `damage_reports.location` | Operational, and adjacent to customers | Stored at the resolution the decision needs and no finer. | Aggregated to neighbourhood level in any log or exported summary (REQ-NF-007). |
| The data enumerated in CON-003 | Personal / premise-level | **Never stored.** Customer names, addresses, account numbers, meter IDs, phone numbers, premise records, household outage status, crew personal data beyond a display name and role. `critical_facility` is a boolean on the asset and is the only premise-adjacent field permitted. | Never logged, and never rendered. |

---

## 7. Retention and deletion

| Data | Retention period | Deletion behavior (hard / soft / archive) |
|---|---|---|
| Decision record | **Indefinite.** It is regulatory evidence, and it is the one thing here that cannot be reconstructed (Q-015). | None. No deletion path exists, for any role (BR-004). |
| Risk score | Kept with its scenario, so a ranking can be replayed and argued with. | Hard delete with the scenario. |
| Damage report, repair job | Kept with their scenario. | Hard delete with the scenario. |
| Asset | Kept with its scenario. | Hard delete with the scenario. |
| Scenario | **90 days after storm close** (Q-015). | Hard delete, cascading to assets, risk scores, damage reports and repair jobs — never to decision records. |
| User | Retained while the account exists; application logs referencing it are kept 30 days (Q-015). | Soft delete. Decision records keep `actor_user_id`, because BR-004 forbids removing the row that names them. |
| Scenario upload | Kept with the scenario it produced; a failed upload is kept 30 days, with the application logs it belongs beside (Q-015). The stored files themselves go with the scenario at 90 days (CHG-012). | Hard delete. A failed upload's stored files are removed as soon as the failure is recorded — nothing partial is left on disk, which is the same rule §9.1 applies to the database. |
| Session | Deleted once it can no longer authenticate — 12 hours after `created_at` at the latest (ADR-006). Kept no longer: an ended session has no evidential value, and the decision record already holds who did what (CHG-008). | Hard delete. Cascades with the user on soft delete only in the sense that every session of a disabled account is ended immediately. |

---

## 8. Migration plan

→ [`../ops/database-migration-plan.md`](../../07-ops/01-deployment/database-migration-plan.md)

| Migration question | Answer |
|---|---|
| Is the migration reversible? | Yes. Every migration ships an up and a down. Version one holds no production data, so a down is cheap — the rule is set now precisely because it stops being cheap later. |
| Will existing data break? | No data exists yet. The standing rule: a new required field is added nullable, backfilled, then made required — never required in one step. |
| Can code and database deploy safely? | Schema first, then the code that depends on it. |
| Is downtime required? | No. Under 50 users and a scenario-sized dataset; no table here is large enough for a lock to be noticed. |

> **Deployment caution (Ch. 23):** never treat database changes as ordinary code changes.
> A broken file can be redeployed. A careless database change can damage production data.

---

## Checklist (Ch. 9)

- [x] Core entities the system must remember are identified.
- [x] Relationships between entities are clear.
- [x] Fields, keys, constraints, and indexes are planned.
- [x] Ownership/tenant scoping is stated for every entity.
- [ ] Sensitive fields are identified with storage and logging rules.
- [ ] Deletion and retention behavior is documented.
- [x] Migration reversibility is considered.

Two boxes are unticked and both name the same kind of gap: CON-003 records that certain data
must not be stored without saying which (Q-007), and no retention period has been set for the
decision record (Q-015). Ticking either would be claiming a decision nobody made.

---

# ADDENDUM — File and Object Storage

> Added to close the storage half of the "database and storage" layer.
> **Skip this section if the system stores no files.** If it does, files are data you are
> responsible for — but almost none of the rules above apply to them.

## Why files need their own rules

| Database rows | Files / objects |
|---|---|
| Transactional | **Not transactional** — the row and the file can disagree |
| Small, bounded | Unbounded until you bound them |
| Backed up together | Backed up **separately**, or not at all |
| Access via query | Access via **URL** — which leaks if unsigned |
| Deleting is a DELETE | Deleting leaves an orphan unless something cleans up |

## Specification

| Item | Decision |
|---|---|
| What is stored | Prepared storm-scenario data files, **uploaded through the application by an admin** (REQ-F-010). Each upload is one Scenario, and several storms may be loaded at the same time. No non-admin upload path exists, and no user-generated content is stored. |
| Where | The application's own data directory. CON-006 rules out a paid object store for version one. |
| **Max size** per file | **8 MB per file, 10 MB per scenario** — roughly double the demo scale of under 5 MB (Q-017), so a legitimate dataset never trips the limit and an unbounded upload cannot pass. |
| Allowed types | An allow-list of exactly five: `manifest.json` and the four CSVs named in `data-and-integration-spec.md` §1. Verified by content inspection, never by extension. A deny-list is never used: it is a list of the attacks somebody already thought of. |
| Type verified by | **content inspection, not the file extension** |
| Naming | A generated identifier. Any supplied filename is kept as a display field only, never as part of a path. |
| Access control | Proxied through the application, which checks the admin role first. No direct URL is issued. |
| Public or private | Private. Asset locations and connections describe critical infrastructure (§6). |
| Malware scanning | **None in version one.** CON-006 rules out a paid scanner, and the residual risk is narrow rather than absent: the upload is admin-only, the files are parsed as data and never executed, and nothing uploaded is ever served back to a browser. Round 8 records this as a security requirement with an explicit revisit trigger — **if the upload path ever opens beyond admins, or an uploaded file is ever returned to a browser, this decision stops being acceptable.** |
| Retention / cleanup | A scenario's files are removed when that scenario is deleted. Because several scenarios coexist, nothing is removed merely because another one is loaded. Decision records are never removed (BR-004). See Q-015. |
| Backed up | → [`../../07-ops/01-deployment/backup-and-recovery.md`](../../07-ops/01-deployment/backup-and-recovery.md) |

## Rules

- **Never trust the filename.** Store under a generated ID; keep the original name as a
  display field only.
- **Never serve private files from a public URL.** Use signed, expiring URLs, or proxy
  the download through an endpoint that checks authorization — the same rule as any
  other resource.
- **The row and the file are two writes with no transaction between them.** Decide the
  order: write the file first, then the row (leaves recoverable orphans), or row first
  then file (leaves broken references). **File-first is usually safer** — an orphan is
  garbage; a broken reference is a user-visible error.
- **Bound the total, not just each file.** Per-user and per-tenant quotas.
- Orphan cleanup is a **scheduled job**, not a hope.

---

> Blueprint: blueprints/01-docs/06-api-and-data-design/database-design.md
