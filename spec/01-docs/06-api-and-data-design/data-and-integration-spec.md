# Data, API, and Integration Specification

> Source: Ch. 9 §9.7–9.9 — "Technical Specification Template: Data, API, and Integration".
> Use this when a feature crosses the boundary into an external service.

**Feature name:** The prepared-data boundary — loading a storm scenario

**Requirement:** REQ-F-010, REQ-F-001

This file was filled rather than skipped. Version one has no external *service*
(CON-005, CON-006), but it does have a data boundary: the prepared files stand in for four
systems that are not connected yet, and everything that arrives across that boundary is
untrusted in exactly the way an external response is. Skipping it would leave the seven
measured data defects in §4 written down nowhere.

---

## 1. Entities

Defined in [`database-design.md`](database-design.md) §1 and cited here — one definition, one
place.

- **Scenario** — the prepared storm everything else is scoped to.
  - Key fields: → `database-design.md` §1
  - Relationships: has many assets, risk scores, damage reports, repair jobs, decision records
- **Asset** — one joined record per substation, line, plant or pump.
  - Key fields: → `database-design.md` §1
  - Relationships: belongs to one scenario; has many risk scores and damage reports

### What arrives across the boundary — the prepared scenario (Q-017)

**One folder or zip. A manifest and four CSVs. Nothing else.** Every column below traces to the
source PRD §7 dataset table; none is invented.

```
manifest.json    scenario_id, storm_name, forecast_issued_at, file list, row counts
assets.csv       asset_id, name, type, lat, lon, install_year, flood_zone,
                 condition_rating, condition_source, condition_date
maintenance.csv  asset_id, inspection_date, condition_rating, notes
weather.csv      grid_cell_id, asset_id, valid_time, wind_gust_mph, rainfall_in
outages.csv      asset_id, failure_time, storm_id      (historical, replay only)
```

| Item | Demo scale |
|---|---|
| Assets | 220 |
| Maintenance rows | ~2,000 |
| Forecast rows | ~5,000 |
| Historical outage rows | ~300 |
| **Total** | **under 5 MB** |

The upload limits in `.env.example` sit at roughly double that — 8 MB per file, 10 MB per
scenario — so a legitimate dataset never trips them and an unbounded upload cannot pass.

**`manifest.json` carries row counts on purpose.** A CSV that parses and is half the length it
claims is the failure mode a size limit does not catch, and a count that disagrees with the file
is a load failure rather than a warning.

**These four files map exactly onto the four scoring factors** in
[ADR-007](../05-architecture/architecture-decisions/ADR-007-scoring-factors-and-weights.md):
gust from `weather.csv`, flood zone and install year from `assets.csv`, condition and its
staleness from `assets.csv` and `maintenance.csv`. `outages.csv` feeds nothing at run time — it
exists so a replayed storm can be scored against what actually failed, which is what
`ai-evals.md`'s quality floor measures.

**The shipped fixture carries all seven §7 defects on purpose**, listed in §4 below: unmatched
IDs, stale inspection dates, 97% missing gusts, zero customer totals, cross-county contamination,
routine work orders mixed into failures, and county-level-only outage rows.

## 2. Database rules

- Primary keys: `id` on every table (`database-design.md` §3)
- Foreign keys: everything scoped by `scenario_id`; `damage_reports.repair_job_id` is the single
  nullable link that makes AC-007 structural
- Unique constraints: `users.email`; `(scenario_id, asset_id, forecast_revision)` on `risk_scores`
- Required indexes: `assets(scenario_id, match_status)`, `risk_scores(scenario_id, forecast_revision, rank)`,
  `damage_reports(scenario_id, status, repair_job_id)`
- Deletion behavior: hard delete cascading from the scenario, never reaching `decision_records` (BR-004)

## 3. API endpoints

- Method and path: `POST /api/v1/scenarios`
- Purpose: load a prepared storm scenario — the only endpoint that crosses this boundary
- Permission: admin only (REQ-R-001)
- Request body: a multipart upload carrying the scenario's name, its `source_note`, and the
  prepared files themselves (CHG-001)
- Success response: `201 Created` with the scenario id and `forecast_revision: 0`. Content
  identical to an already-loaded scenario returns `200 OK` with that scenario's existing id,
  because an identical re-load replaces in place rather than creating a rival ranking.
- Error responses: `400` malformed or unreadable file; `401` not signed in; `403` not an admin;
  `413` over the size limit (Q-017); `415` a type outside the allow-list; `422` the files parsed
  but failed §4

## 4. Validation rules

- Required fields: every asset record must carry an identifier from at least one source system,
  a type, and a location. A record missing all three is rejected, not guessed at.
- Allowed values: `type` in substation, line, plant, pump. `status` in the enumerations fixed in
  `database-design.md` §3.
- Relationship checks: a damage report referencing an unknown asset loads with a null `asset_id`
  and is flagged, rather than being dropped — a report with no matching asset is still a report.
- Permission checks: only an admin reaches this endpoint at all (REQ-R-001), and the refusal is
  recorded (AC-009).

**The seven defects the incoming data is known to carry.** These are not hypotheticals: the
source PRD (§7) measured each one in real public files of the same kinds, and the prepared test
dataset injects all seven on purpose so the design is proven against dirty data rather than
clean data.

| Defect | What the loader must do |
|---|---|
| The same asset carries different codes in different systems (`SS-1042` vs `TX-4471`). | Match what can be matched; set `match_status = 'needs_review'` on the rest and surface them to a person. Never merge on a guess. |
| Condition data is old — inspections between two months and six years back. | Store `condition_observed_at` and render it beside the value (BR-003). Never present an old inspection like a current reading. |
| Weather station gust values are largely absent — 97% missing in a real file. | Do not depend on station records. Take wind from forecast grid squares, which have a value everywhere. |
| Outage records carry a broken customer total — 83% of rows zero in a real file. | Never compute a percentage from a stored total without first checking it against an independent population figure. Refuse the percentage rather than publish a wrong one. |
| One county absorbs its neighbours' outages, showing more customers out than it has. | A range check that flags any impossible figure, at load time, by name. |
| Repair records are not failure records — routine work is mixed with real failures. | Never derive the failure history from repair logs. It comes from outage records, built with SGW. |
| Public outage data is county-level and never names the failed asset. | Recorded as the known ceiling on public data. Per-asset truth can only come from SGW's own records (Q-005's second measure depends on this). |

## 5. Integration rules

An integration connects your system to something outside it: payments, email, calendars,
identity providers, storage, analytics, AI model APIs. Outside services fail, change,
rate-limit, and return the unexpected — specify that **before** implementation.

| Item | Definition |
|---|---|
| Provider | **None.** Version one's only data boundary is a set of prepared files uploaded by an admin through the application (CON-005, CON-006, CHG-001). |
| Purpose | To exercise the platform end to end — joined view, ranking, planning, dispatch — without connecting to any system SGW operates. |
| Data sent | **Nothing, ever.** The boundary is inbound only, and REQ-R-003 makes that structural rather than a policy: no outbound path exists to build against. |
| Data received | Asset records; maintenance and inspection history; weather forecasts per grid area; damage and outage records; crew and job status — the inputs the source PRD §7 names. |
| Data stored | Assets, risk scores, damage reports, repair jobs, decision records (`database-design.md` §3). Whether forecast and maintenance history persist as entities or survive only inside a risk score's reasons is undecided — see Q-011. |
| Timeout | An upload timeout is required, because Q-014 confirmed an upload path (CHG-001). Parsing has its own bound: a scenario that has not finished loading after the timeout fails as a whole and leaves no half-loaded scenario behind. The numbers wait on Q-017. |
| Retry rule | The upload may be retried by the person; **the parse is never retried automatically.** A malformed file is a fact about the file, not a transient error, and retrying one is how a bad load becomes a slow bad load. |
| Idempotency | Loading a scenario whose content is identical to one already loaded replaces that one in place; different content is a new scenario, and several scenarios coexist (CHG-001). Derived from AC-007's principle rather than stated in an answer — a second identical load must not produce a second ranking that somebody then has to reconcile. |
| Failure behavior | Show the last good picture, clearly marked stale and dated, and name the file that failed (REQ-NF-003, AC-002). Never an empty screen and never a bare error page — the storm does not pause for a broken load. |
| Security rule | The files describe critical infrastructure. Stored privately, served only through the application, admin only. No secret is involved, because there is no external service to authenticate to — CON-006 paying for itself. |
| Rate limits | None, because there is no provider to be limited by. Recorded so that adding a provider later is visibly a new decision with a new row, not a quiet extension of this one. |

> **Security reminder (Ch. 9 §9.7):** never design an integration that exposes secrets to
> the frontend or stores tokens in plain text.

## 6. Versioning rules

- Current version: prepared-data schema v1
- Breaking-change policy: the prepared files are a contract like any other. Renaming or removing
  a column, or changing its type, is a new schema version with its own loader — never a silent
  reinterpretation of the old one.
- Compatibility notes: an added optional column is safe and is ignored until something reads it.
  The seven defects in §4 are permanent expectations, not transitional ones: a future file that
  arrives clean must still load through the same checks, because the checks are what prove it
  was clean.

---

## Integration checklist

- [x] Provider, purpose, and data flow are documented in both directions.
- [ ] Timeout is set — the system never waits forever.
- [x] Retries are bounded and only applied to safe (idempotent) operations.
- [x] Failure behavior is defined, including what the user sees.
- [x] Secrets are configured through the environment, never hardcoded.
- [ ] Failure paths have tests (`../tests/edge-cases-and-failures.md`).
- [ ] Monitoring covers this integration (`../ops/monitoring-plan.md`).

Three boxes are unticked, for two different reasons, and the difference matters. **The timeout
is required but has no number yet** — Q-014 confirmed an upload path, so a bound exists to set;
Q-017 supplies the size it has to be set against. **Failure-path tests and monitoring are not
yet written** — Round 7 writes the tests and Round 8 writes the monitoring plan. The first is a
missing number; the others are unreached work.

---

> Blueprint: blueprints/01-docs/06-api-and-data-design/data-and-integration-spec.md
