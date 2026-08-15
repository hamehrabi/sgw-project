# Integration Test Plan

> Source: Ch. 4 §4.6, Ch. 17 §17.3, Ch. 18 §18.6.
> Integration tests check whether **separate parts of the system work together** — when a
> requirement depends on more than one component: an API endpoint, a database table, and
> an authentication rule.

Creating a task is not just a database operation. The API must accept the request,
validate the fields, check the user, save the task, and return the correct response.
That is integration behavior.

---

| Test ID | Requirement | Integration point | Scenario | Expected result | Side effect to verify | Status |
|---|---|---|---|---|---|---|
| ITEST-001 | REQ-F-001, REQ-F-002 | API + job + database | Upload a fixture carrying all seven defects, parse it, and rank it | 201 on upload; the scenario becomes rankable; every ranked item carries reasons | One scenario row; assets present with `match_status`; risk scores at revision 0; **no second scenario** | Planned |
| ITEST-002 | REQ-F-006, BR-004 | API + database | Post a second decision on a recommendation that already has one | 409, and the response names the existing decision | **The first `decision_records` row is byte-identical afterwards**, and no second row exists | Planned |
| ITEST-003 | REQ-F-007 | API + database | Two damage reports arrive for one location | 200; the board shows both, attached to one job | Exactly one `repair_jobs` row; both reports carry the same `repair_job_id` | Planned |
| ITEST-004 | REQ-F-004 | API + database | Request `forecast_revision=0` after revision 1 has been written | 200, returning the revision-0 order unchanged | No write of any kind; revision 1 still current | Planned |
| ITEST-005 | REQ-F-010 | API + database | Two scenarios loaded; request the ranking for one | 200, containing only that scenario's assets | **Zero rows from the other scenario in the response**, at any page | Planned |

---

## Integration points to cover (Ch. 17 §17.3)

| Integration point | What you should verify |
|---|---|
| API + database | A valid request creates the right record and returns the correct response. |
| Authentication + API | Only an authenticated user can perform the action. |
| Authorization + API | Only a permitted role can perform the action. |
| Validation + response handling | Invalid input returns a clear error **without creating bad data**. |
| Service + external dependency | The system handles dependency success, failure, and timeout cases. |
| Job + queue | A queued job runs, retries, and records its final status. |

**The *service + external dependency* row has nothing to cover**, and that is a result rather
than a gap: version one depends on no external service (Round 6, CON-005, CON-006). The
*job + queue* row covers exactly one job — the scenario parse — and its retry rule is *never*,
which is itself the thing to assert.

---

## API contract tests (Ch. 18 §18.6)

A strong API test does not only ask whether the endpoint responds. It checks the method,
URL, request body, status code, response body, validation rules, **and side effects**.

| Test name | Request input | Expected status | Expected response body | Side effect to verify |
|---|---|---|---|---|
| Valid credentials create session | `{email, correct password}` | 200 | Session token exists | Session record created |
| Wrong password is rejected | `{email, wrong password}` | 401 | Authentication error | No session created |
| Missing email is rejected | `{password only}` | 400 | Email required error | No session created |
| Missing password is rejected | `{email only}` | 400 | Password required error | No session created |
| Unknown email is rejected | `{unknown email, password}` | 401 | Authentication error | No session created |

**What one row becomes (Ch. 18 §18.6).** Specify each row as three assertions and nothing
else: the status code, the field of the response body that carries the answer, and the side
effect that must **not** have happened. "Missing password is rejected" is therefore *400, the
error names the password field, and no session row exists afterwards* — three statements a
test can be written from without a decision being made in the test file. The side-effect
assertion is the one that catches a handler which returns the right status after it has
already written. The worked example at the end of this file shows the pair written out.

### `POST /api/v1/scenarios` — the endpoint that accepts untrusted input

| Test name | Request input | Expected status | Expected response body | Side effect to verify |
|---|---|---|---|---|
| Admin uploads a valid scenario | admin session + valid files | 201 | scenario id, `forecast_revision: 0` | One scenario row; files stored under a generated identifier |
| Identical content re-uploaded | admin session + byte-identical files | 200 | the **existing** scenario id | **No second scenario row** |
| User role is refused | user session + valid files | 403 | generic access-denied | No scenario row; **no file written to disk**; one refusal row in the decision record |
| Signed-out is refused | no session + valid files | 401 | generic | No scenario row; no file written |
| Oversize file | admin session + file over the limit | 413 | names the file | No file written; **refused before parsing** |
| Right extension, wrong content | admin session + disguised file | 415 | names the file | No file written; content inspection, not extension, made the call |
| Parses but fails a defect rule | admin session + file failing one of the seven | 422 | names the file and the rule | **No scenario row**, and every previously loaded scenario still ranks |

### `POST /api/v1/recommendations/{id}/decision` — the endpoint BR-001 lives on

| Test name | Request input | Expected status | Expected response body | Side effect to verify |
|---|---|---|---|---|
| Accept is recorded | valid session + `{decision: accept}` | 201 | decision record id, actor, timestamp | One appended row; **no crew movement, job assignment, or outbound call of any kind** |
| Change without a note | `{decision: change}` with no note | 400 | names the note field | No row written; the typed note, if any, is returned to the caller |
| Second decision | a recommendation that already has one | 409 | names the existing decision | First row unchanged; no second row |
| Unknown recommendation | a nonexistent id | 404 | safe message | No row written |

---

Executable tests live in [`../tests/integration/`](../05-executable/integration).

---

## The two side-effect assertions that matter most

**ITEST-002's is the whole point of BR-004.** A handler that returns 409 *after* updating the
row would pass a status-code test and would have destroyed the audit trail. The assertion is
that the first row is unchanged, compared field by field — not that a 409 came back.

**The upload row's `no file written to disk` is the one an agent will omit.** Refusing with 403
and then storing the file anyway leaves an unreferenced file containing critical-infrastructure
data on the host, with nothing pointing at it and nothing cleaning it up. The status code is
right and the outcome is a leak.

---

> Blueprint: blueprints/03-tests/02-functional/integration-tests.md
