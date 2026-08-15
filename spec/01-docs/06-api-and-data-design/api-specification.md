# API Specification

> Source: Ch. 7 §7.7, Ch. 9 §9.4–9.8, Appendix D.
> An API contract stops the agent from inventing endpoint names, request formats,
> response formats, or ownership behavior while coding.

**Base path:** `/api/v1`
**Auth model:** Email and password, with a server-side session checked on every request (ADR-003). Session lifetime is not yet set — see Q-021.
**Version:** API v1.0

---

## Endpoint index

| Method | Path | Purpose | Requirement | Permission |
|---|---|---|---|---|
| POST | `/api/v1/auth/session` | Sign in. | REQ-NF-002 | Public |
| DELETE | `/api/v1/auth/session` | Sign out. | REQ-NF-002 | Signed in |
| POST | `/api/v1/scenarios` | Load a prepared storm scenario. | REQ-F-010 | Admin only |
| GET | `/api/v1/scenarios/{scenario_id}` | Read the loaded scenario and its current forecast revision. | REQ-F-010 | Signed in |
| GET | `/api/v1/scenarios/{scenario_id}/assets` | The joined asset view — one record per asset, each value with its source and age. | REQ-F-001 | Signed in |
| GET | `/api/v1/scenarios/{scenario_id}/risks` | Assets ranked by risk, each rank carrying its reasons. **The core subdomain's endpoint.** | REQ-F-002, REQ-F-003 | Signed in |
| POST | `/api/v1/scenarios/{scenario_id}/forecast-revisions` | Apply the scenario's next forecast change and re-rank. | REQ-F-004 | Signed in |
| POST | `/api/v1/scenarios/{scenario_id}/placements` | Record a crew placement against the ranked list. | REQ-F-005 | Signed in |
| POST | `/api/v1/recommendations/{recommendation_id}/decision` | Accept, change, or reject a recommendation. | REQ-F-006 | Signed in |
| GET | `/api/v1/scenarios/{scenario_id}/jobs` | The shared damage and repair board. | REQ-F-007 | Signed in |
| POST | `/api/v1/damage-reports/{report_id}/dismiss` | Dismiss a false alarm in one action. | REQ-F-008 | Signed in |
| GET | `/api/v1/scenarios/{scenario_id}/decisions` | Read the decision record. | REQ-F-009 | Admin only |

**No endpoint writes to anything outside this platform.** There is no path, at any version, by
which a request here becomes a command to a system that controls the grid or the water network
(REQ-R-003, BR-005). That is a property of the endpoint list itself, not a rule applied on top
of it.

---

## Endpoint template (Appendix D)

Copy this block for **every** endpoint before implementation begins.

```
Endpoint name:        [e.g. Create Task]
Method and path:      POST /api/v1/projects/{project_id}/tasks
Purpose:              [what it does and why it exists]
Requirement:          REQ-F-###
Authentication:       [login / token / none]
Authorization rules:  [who can access, under what conditions]

Request body:
{
  "field": "type — required/optional — validation rule"
}

Success response:     201 Created
{
  "field": "type"
}

Error responses:
  400 — validation error
  401 — not authenticated
  403 — authenticated but not allowed
  404 — resource not found
  409 — conflict / duplicate
  500 — unexpected server failure

Business rules:       [rules enforced beyond basic validation]
Side effects:         [database writes, emails, jobs, audit events]
Tests required:       TEST-### (unit, integration, edge cases)
```

**Two of the twelve are written out below, and ten are not.**
[`subdomain-map.md`](../01-intent/subdomain-map.md) gives the ranked risk list Full spec depth
and everything else Light, so the core endpoint and the endpoint that enforces BR-001 are
specified here and the remaining ten are specified when their task is written (Round 7). That
is a deliberate allocation of depth, not an unfinished section.

```
Endpoint name:        Ranked risk list
Method and path:      GET /api/v1/scenarios/{scenario_id}/risks
Purpose:              Return every asset in the scenario ordered by risk, each rank
                      carrying the plain-words reasons behind it. This is the thing
                      the product competes on.
Requirement:          REQ-F-002, REQ-F-003
Authentication:       Signed in
Authorization rules:  Any signed-in user. No per-record rules — a single organisation,
                      and every role sees the same ranking.

Query parameters:
{
  "forecast_revision": "integer — optional — defaults to the scenario's current revision;
                        an earlier value returns that earlier ranking unchanged (AC-005)",
  "limit":             "integer — optional — 1..500, default 100",
  "cursor":            "string — optional — opaque"
}

Success response:     200 OK
{
  "scenario_id":       "string",
  "forecast_revision": "integer",
  "computed_at":       "timestamp",
  "items": [
    {
      "asset_id":   "string",
      "rank":       "integer",
      "score":      "number",
      "confidence": "string — nullable",
      "reasons":    "array of strings — ALWAYS at least one (BR-002)",
      "values": [
        {
          "name":        "string   — e.g. condition",
          "value":       "string",
          "source":      "string   — which prepared file it came from (BR-003)",
          "observed_at": "date     — how old it is (BR-003)",
          "estimated":   "boolean  — true renders visually distinct from measured (BR-003)"
        }
      ]
    }
  ],
  "next_cursor": "string — nullable"
}

Error responses:
  400 — forecast_revision is not an integer, or limit is out of range
  401 — not signed in
  404 — no such scenario, or no such forecast revision
  500 — unexpected server failure

Business rules:       BR-002 — `reasons` is never empty and never omitted. An item that
                      cannot produce a reason is not returned at all; it is surfaced as a
                      scoring failure, because a rank without a reason is the exact thing
                      operators were predicted not to act on.
                      BR-003 — every entry in `values` carries source, age, and whether it
                      is estimated. There is no shape of this response without them.
Side effects:         One `decision_records` row of kind `recommendation` per delivered
                      ranking, so what was shown can be reconstructed later (REQ-F-009).
Tests required:       Unit — reasons never empty, ordering is total and stable.
                      Integration — an earlier forecast_revision returns the earlier order.
                      Edge — a scenario with zero assets returns an empty list, not a 404.
```

```
Endpoint name:        Decide on a recommendation
Method and path:      POST /api/v1/recommendations/{recommendation_id}/decision
Purpose:              Record that a person accepted, changed, or rejected a
                      recommendation. This endpoint is where BR-001 is enforced.
Requirement:          REQ-F-006
Authentication:       Signed in
Authorization rules:  Any signed-in user, admin or user alike. Deciding is the whole
                      point of the product and is not a privileged action.

Request body:
{
  "decision": "enum(accept, change, reject) — required",
  "note":     "string — required when decision is change or reject, max 2000 chars",
  "change":   "object — required when decision is change — the operator's alternative"
}

Success response:     201 Created
{
  "decision_record_id": "string",
  "recommendation_id":  "string",
  "decision":           "string",
  "actor_user_id":      "string",
  "occurred_at":        "timestamp"
}

Error responses:
  400 — decision is not one of the three values, or note is missing on change/reject
  401 — not signed in
  404 — no such recommendation
  409 — this recommendation already carries a decision; corrections are new rows (BR-004)
  500 — unexpected server failure

Business rules:       BR-001 — the response is a record, never an action. No crew is moved,
                      no job is assigned, and no message leaves the platform as a result of
                      this call.
                      BR-004 — the row is appended. There is no PATCH and no DELETE for a
                      decision, which is why a second decision is a 409 rather than an
                      overwrite.
Side effects:         One `decision_records` row. Nothing else.
Tests required:       Unit — change and reject without a note are rejected.
                      Integration — a second decision on the same recommendation returns 409
                      and leaves the first row untouched.
                      Security — an UPDATE against decision_records as the application's own
                      database role is refused by the database (BR-004).
```

---

## Status code response principles (Appendix D)

| Status | Use | Response principle |
|---|---|---|
| 200 / 201 | Successful read or creation. | Return only the fields the user is allowed to see. |
| 400 | Invalid request data. | Explain the invalid field without exposing internals. |
| 401 | User is not authenticated. | Ask the user to sign in again. |
| 403 | Authenticated but not allowed. | Do not reveal protected resource details. |
| 404 | Resource not found. | Avoid confirming whether another user's resource exists. |
| 500 | Unexpected server failure. | Safe generic message; log the internal reason. |

---

## Contract rules (Ch. 9 §9.9)

| Rule | Specification |
|---|---|
| Response consistency | Every success response returns a predictable object shape. |
| Error consistency | Every error uses `code`, `message`, and optional `field`. |
| Permission check | Every endpoint checks user access before returning data. |
| Validation timing | Validation happens **before** saving data. |
| Audit trail | Important create and status-change events are recorded. |

---

## Validation rules (Ch. 9 §9.6)

| Rule type | Example |
|---|---|
| Required field | A task title is required. |
| Length rule | A task title must be 3–120 characters. |
| Allowed value | Status must be `todo`, `doing`, `blocked`, or `done`. |
| Relationship rule | The assignee must belong to the project. |
| Permission rule | Only members with write access can create tasks. |
| Date rule | Due date cannot be before the project start date. |

---

## Versioning and compatibility (Ch. 9 §9.8)

**Current version:** v1

**Breaking-change policy:** Renaming a field, removing one, or changing its type requires a new
path under `/api/v2`, never an edit in place. Version one has exactly one consumer — this
platform's own four screens — so a breaking change today is a coordinated deploy rather than a
public event. The policy is adopted now anyway, because now is the only time it costs nothing.

**Compatibility notes:** Adding an optional field or a new endpoint is safe. One field is
neither optional nor removable at any version: `reasons` on a risk item. BR-002 makes it part
of the contract rather than a convenience, so dropping it is a change of product, not a change
of API.

| Change type | Usually safe? | Example |
|---|---|---|
| Add optional field | Usually safe | Add `priority` to a task response. |
| Add new endpoint | Usually safe | Add `GET /api/v1/tasks/{id}/history`. |
| Rename field | **Breaking** | Change `due_date` to `deadline`. |
| Remove field | **Breaking** | Remove `assignee_id` from task response. |
| Change data type | **Breaking** | Return `due_date` as an object instead of a string. |

---

> Blueprint: blueprints/01-docs/06-api-and-data-design/api-specification.md
