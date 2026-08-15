# Test Specification

> Source: Ch. 17 §17.8 + Appendix G.
> Explains **how a requirement will be verified**, clearly enough that you, another
> developer, or an AI agent can later create the actual tests from it.

---

## Per-test fields (Appendix G)

| Field | What to write |
|---|---|
| Test ID | Unique identifier such as `TEST-001`. |
| Related requirement | Requirement ID this test verifies. |
| Test level | Unit, integration, end-to-end, security, performance, or regression. |
| Scenario | Plain-language behavior being tested. |
| Preconditions | Setup required before the test runs. |
| Input data | Valid, invalid, boundary, or malicious inputs. |
| Expected result | Observable outcome. |
| Failure meaning | What it means if this test fails. |
| Automation status | Manual, planned, automated, or blocked. |
| Owner | Person or role responsible for maintaining the test. |

## Test case template (Ch. 27 §27.8)

```
Test ID:
Requirement covered:
Test level:
Role:
Preconditions:
Input or user action:
Expected result:
Permission expectation:
Error or empty-state expectation:
Evidence to capture:
Failure meaning:
Automation status:   Manual / Planned / Automated / Blocked
Owner:
Status:              Not run / Pass / Fail / Needs review
```

---

## Test specification matrix

**This matrix is an INDEX, not a second copy of the tests.** One row per test, naming where it
is specified and what it covers — the scenario, the expected result and the preconditions live
in the file that owns the test.

| Test ID | Requirement ID | Level | Specified in | Risk covered | Status |
|---|---|---|---|---|---|
| ATEST-001 | REQ-F-001 | Acceptance | `../02-functional/acceptance-tests.md` | Assets duplicated across source systems; a value shown without its age | Planned |
| ATEST-002 | REQ-F-001 | Acceptance | `../02-functional/acceptance-tests.md` | A broken file blanking the screen mid-storm | Planned |
| ATEST-003 | REQ-F-002 | Acceptance | `../02-functional/acceptance-tests.md` | An asset missing from the ranking | Planned |
| ATEST-004 | REQ-F-003, BR-002 | Acceptance | `../02-functional/acceptance-tests.md` | A rank nobody can interrogate — assumption A3 | Planned |
| ATEST-005 | REQ-F-004 | Acceptance | `../02-functional/acceptance-tests.md` | A re-rank destroying the order a decision was made against | Planned |
| ATEST-006 | REQ-F-006, BR-001 | Acceptance | `../02-functional/acceptance-tests.md` | The system acting rather than advising | Planned |
| ATEST-007 | REQ-F-007 | Acceptance | `../02-functional/acceptance-tests.md` | Two crews sent to one location | Planned |
| ATEST-008 | REQ-F-009, BR-004 | Acceptance | `../02-functional/acceptance-tests.md` | An audit trail its subjects can rewrite | Planned |
| ATEST-009 | REQ-R-001, REQ-F-010 | Acceptance | `../02-functional/acceptance-tests.md` | A non-admin replacing the loaded storm | Planned |
| ATEST-010 | REQ-NF-003 | Acceptance | `../02-functional/acceptance-tests.md` | Stale data read as current | Planned |
| UTEST-001 | REQ-NF-002 | Unit | `../02-functional/unit-tests.md` | A credential reaching a log | Planned |
| UTEST-002…008 | REQ-F-001 | Unit | `../02-functional/unit-tests.md` | Each of the seven measured data defects | Planned |
| UTEST-009 | BR-002 | Unit | `../02-functional/unit-tests.md` | A score produced without reasons | Planned |
| UTEST-010 | REQ-F-002 | Unit | `../02-functional/unit-tests.md` | An unstable order changing between reads | Planned |
| UTEST-011 | REQ-F-008 | Unit | `../02-functional/unit-tests.md` | An anonymous dismissal | Planned |
| UTEST-012 | REQ-NF-007 | Unit | `../02-functional/unit-tests.md` | A household-level location in a log or export | Planned |
| ITEST-001 | REQ-F-001, REQ-F-002 | Integration | `../02-functional/integration-tests.md` | The whole load-to-rank path against dirty data | Planned |
| ITEST-002 | REQ-F-006, BR-004 | Integration | `../02-functional/integration-tests.md` | A retry rewriting an audit row | Planned |
| ITEST-003 | REQ-F-007 | Integration | `../02-functional/integration-tests.md` | Reports and jobs disagreeing | Planned |
| ITEST-004 | REQ-F-004 | Integration | `../02-functional/integration-tests.md` | A silent fallback to the current revision | Planned |
| ITEST-005 | REQ-F-010 | Integration | `../02-functional/integration-tests.md` | Two storms blending into one ranking | Planned |
| E2E-001 | REQ-F-002…006 | End-to-end | `../02-functional/end-to-end-tests.md` | The planning flow, including its failure path | Planned |
| E2E-002 | REQ-F-001, REQ-F-010 | End-to-end | `../02-functional/end-to-end-tests.md` | The load flow, including its failure path | Planned |
| STEST-001…004 | SEC-A-001…005 | Security | `../03-non-functional/security-tests.md` | Sign-in bypass, session reuse, account enumeration, brute force | Planned |
| STEST-005…007 | SEC-Z-002 | Security | `../03-non-functional/security-tests.md` | A non-admin loading data; a disguised file type | Planned |
| STEST-008 | SEC-Z-004, BR-004 | Security | `../03-non-functional/security-tests.md` | The audit trail being editable | Planned |
| STEST-009 | REQ-NF-007 | Security | `../03-non-functional/security-tests.md` | Household-level detail leaving the system | Planned |
| STEST-010 | SEC-Z-005, BR-005 | Security | `../03-non-functional/security-tests.md` | Any outbound path to a control system existing at all | Planned |
| PTEST-001 | REQ-NF-001 | Performance | `../03-non-functional/performance-tests.md` | A re-rank too slow to use during a storm | Planned |
| PTEST-002 | REQ-NF-001 | Performance | `../03-non-functional/performance-tests.md` | Page load, and reasons that take too long to open | Planned |
| FTEST-001 | REQ-F-010 | Failure | `../04-failure/failure-tests.md` | A half-loaded storm | Planned |
| FTEST-002 | REQ-NF-003 | Failure | `../04-failure/failure-tests.md` | A blank screen where the last good picture should be | Planned |
| FTEST-003 | REQ-NF-003 | Failure | `../04-failure/failure-tests.md` | Staleness that is not stated | Planned |
| FTEST-004 | BR-002 | Failure | `../04-failure/failure-tests.md` | An unscorable asset rendered as safe | Planned |
| FTEST-005 | REQ-F-005, REQ-F-006 | Failure | `../04-failure/failure-tests.md` | A decision or placement lost on a failed write | Planned |
| EVAL-001 | REQ-F-002 | Evaluation | `../03-non-functional/ai-evals.md` | A ranking that ranks the wrong things | Planned |
| ATEST-011 | REQ-NF-006 | Acceptance | `../02-functional/acceptance-tests.md` | WCAG 2.1 AA: keyboard-only operation of the ranking, and no rank distinguished by colour alone | Planned |

> **Two ID columns, on purpose.** `Test ID` and `Requirement ID` name the two things this row
> MAPS BETWEEN, and that is what makes it a mapping table rather than a definition of either.
> The validation reads a table with two `ID` headers as citations — so keep both words, and do
> not shorten `Requirement ID` to `Req`. It was `Req` once, and every row in this matrix was
> then reported as a second definition of the test it indexes: seventeen duplicates from one
> file, on every workspace this kit produced.
>
> **The Test ID column CITES; it does not mint.** A test is defined once, in the file for its
> level — `unit-tests.md`, `integration-tests.md`, `acceptance-tests.md`, `security-tests.md`,
> `failure-tests.md`. Write that id here once it exists. Until it does, leave the sanctioned
> marker naming the question — the same `[TODO: ...]` form every other unknown uses.
>
> This matrix used to carry `Scenario`, `Preconditions`, `Input` and `Expected result` columns —
> the whole test, restated. A run filled both, in different words, and the two agreed on the day
> they were written with nothing keeping them equal afterwards. **An index that repeats what it
> indexes is a second source of truth wearing a table header.**

**Status values:** Planned · Written · Passing · Failing · Blocked

---

## Test levels (Appendix G)

| Test type | Question it answers | Example |
|---|---|---|
| Unit | Does one small function behave correctly? | Title validation rejects an empty task title. |
| Integration | Do connected parts work together? | API creates a task and stores it in the database. |
| End-to-end | Can a user complete the workflow? | User signs in, creates a task, marks it done. |
| Security | Can rules be bypassed? | User cannot access another user's task. |
| Performance | Does the system respond under expected load? | Task list loads within the target response time. |

---

## Reviewing AI-generated tests (Ch. 18 §18.2)

Never accept generated tests just because they look professional. A test can be
well-formatted and still be weak.

| Review area | Question to ask | How to fix weakness |
|---|---|---|
| Requirement link | Does this test prove a specific requirement or acceptance criterion? | Add the requirement ID beside the test. |
| Clear assertion | Does the test check a real expected result? | Replace vague checks with exact status codes, messages, values, or state changes. |
| Failure path | Does it cover what happens when something goes wrong? | Add invalid input, missing data, permission failure, timeout cases. |
| No invented behavior | Did the AI add behavior not in the spec? | Remove it — or update the spec first. |
| Stable data | Can the test run repeatedly with predictable results? | Use controlled test data and reset state when needed. |

**Shallow vs. useful:** a shallow test gives you confidence without proof. Ask *what exact
promise does this feature make, and how can a test prove that promise?*

**The three weakenings to watch for on this project**, each of which leaves a test that passes
and proves nothing:

| Weakened into | Instead of |
|---|---|
| "The ranking endpoint returns 200" | Every returned item carries at least one reason (UTEST-009 asserts the store refuses otherwise) |
| "No error is thrown when a data file is missing" | The last good picture is served, marked stale, with the failing file named (FTEST-002) |
| "The application refuses to update a decision record" | The **database** refuses it, asserted against the database rather than through the service layer (STEST-008) |

---

> Blueprint: blueprints/03-tests/01-plan/test-specification.md
