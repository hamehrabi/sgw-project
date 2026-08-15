# Test Plan

> Source: Ch. 4 §4.6, Ch. 17.
> **Beginner rule:** do not ask an AI agent to build a feature until you can write at
> least three checks for it — one normal case, one edge case, one failure case.

**Feature / release:** SGW Resilience Platform — version one

**Requirements covered:** REQ-F-001 to REQ-F-010 · REQ-NF-001 to REQ-NF-007 ·
REQ-R-001 to REQ-R-003 · BR-001 to BR-005 · SEC-A-001 to SEC-A-006 · SEC-Z-001 to SEC-Z-006

**Version:** TEST v1.0

**Depth: standard** — acceptance, unit, integration, failure, and key security, as chosen in
Round 7. Performance is planned as two named checks rather than a suite, because performance was
offered as a driving characteristic in Round 4 and declined; and negative RBAC is covered for
every *No* in the role matrix rather than exhaustively per endpoint.

**Identifier convention.** One prefix per level, and each id is defined in exactly one file:
`ATEST-` acceptance · `UTEST-` unit · `ITEST-` integration · `E2E-` end-to-end ·
`STEST-` security · `PTEST-` performance · `FTEST-` failure · `EVAL-` scoring evaluation.

---

## Why tests come first (Ch. 17 §17.1)

| Without test planning | With test planning |
|---|---|
| The agent decides what "done" means. | You define what "done" means before implementation. |
| Bugs are found late, often during manual review. | Expected behavior is checked early and repeatedly. |
| The code may satisfy the prompt but not the requirement. | The code must satisfy visible acceptance criteria. |
| You approve features based on appearance. | You approve features based on **evidence**. |

---

## Test strategy by level

| Level | What it checks | Where it lives | File |
|---|---|---|---|
| Unit | A small piece of logic behaves correctly. | `../tests/unit/` | [unit-tests.md](../02-functional/unit-tests.md) |
| Integration | Two or more parts work together. | `../tests/integration/` | [integration-tests.md](../02-functional/integration-tests.md) |
| End-to-end | A complete user flow works. | `../tests/end-to-end/` | [end-to-end-tests.md](../02-functional/end-to-end-tests.md) |
| Acceptance | The requirement works from the user/business view. | — | [acceptance-tests.md](../02-functional/acceptance-tests.md) |
| Security | Rules cannot be bypassed. | `../tests/integration/` | [security-tests.md](../03-non-functional/security-tests.md) |
| Performance | The system responds under expected load. | — | [performance-tests.md](../03-non-functional/performance-tests.md) |
| Failure / edge | Errors are handled safely. | — | [edge-cases-and-failures.md](../04-failure/edge-cases-and-failures.md) |
| Regression | A fixed bug does not return. | matching level | tracked in `../review/debugging-specification.md` |

---

## Coverage matrix

| Requirement | Acceptance test | Unit | Integration | E2E | Security | Performance | Failure |
|---|---|---|---|---|---|---|---|
| REQ-F-001 | ATEST-001, ATEST-002 | UTEST-002…008 | ITEST-001 | E2E-002 | STEST-005 | — | FTEST-001, FTEST-002 |
| REQ-F-002 | ATEST-003 | UTEST-010 | ITEST-001 | E2E-001 | — | PTEST-001 | FTEST-004 |
| REQ-F-003 | ATEST-004 | UTEST-009 | — | E2E-001 | — | — | FTEST-004 |
| REQ-F-004 | ATEST-005 | — | ITEST-004 | — | — | PTEST-001 | — |
| REQ-F-005 | — | — | — | E2E-001 | — | — | FTEST-005 |
| REQ-F-006 | ATEST-006 | — | ITEST-002 | E2E-001 | STEST-008 | — | FTEST-005 |
| REQ-F-007 | ATEST-007 | — | ITEST-003 | — | — | PTEST-002 | — |
| REQ-F-008 | — | UTEST-011 | — | — | — | — | — |
| REQ-F-009 | ATEST-008 | — | ITEST-002 | — | STEST-008 | — | — |
| REQ-F-010 | ATEST-009 | — | ITEST-005 | E2E-002 | STEST-005, STEST-006 | — | FTEST-001 |
| REQ-NF-001 | — | — | — | — | — | PTEST-001, PTEST-002 | — |
| REQ-NF-002 | — | UTEST-001 | — | — | STEST-001…004 | — | — |
| REQ-NF-003 | ATEST-010 | — | — | — | — | — | FTEST-002, FTEST-003 |
| REQ-NF-004 | — | — | — | E2E-001 | — | — | — |
| REQ-NF-005 | — | — | — | — | — | — | — (guarded by FF-002) |
| REQ-NF-006 | ATEST-011 | — | — | — | — | — | — |
| REQ-NF-007 | — | UTEST-012 | — | — | STEST-009 | — | — |
| REQ-R-001 | ATEST-009 | — | — | — | STEST-005 | — | — |
| REQ-R-002 | — | — | — | — | STEST-008 | — | — |
| REQ-R-003 | — | — | — | — | STEST-010 | — | — |
| BR-001 | ATEST-006 | — | ITEST-002 | — | — | — | — |
| BR-002 | ATEST-004 | UTEST-009 | — | — | — | — | FTEST-004 |
| BR-003 | ATEST-001 | UTEST-004 | — | — | — | — | — |
| BR-004 | ATEST-008 | — | ITEST-002 | — | STEST-008 | — | — |
| BR-005 | — | — | — | — | STEST-010 | — | — |

**One row is honestly empty and it is not an oversight.** REQ-NF-005 (the scoring module is
separable) is a structural property guarded by FF-002 rather than by a test — a test cannot
observe an import boundary usefully. **REQ-NF-006 gained ATEST-011 when Q-013 named WCAG 2.1 AA**
(CHG-006); before that it was a requirement with no standard to test against, which is the one
state worse than having no requirement at all.

---

## Quality gate before implementation (Ch. 16 §16.6)

> Before you implement a task, confirm the test plan answers this question:
> **How will I know this task works without trusting the AI agent blindly?**

- [x] Every Must requirement has at least one acceptance test.
- [x] Every business rule has a test.
- [x] Every role/permission boundary has a negative test.
- [x] Every validation rule has an invalid-input test.
- [x] Every failure state in the reliability spec has a test.
- [x] Every API contract has a request/response shape test.
- [x] Tests are written from **requirements**, not from existing code.

The last box is trivially true today and will not stay that way. Every test in this plan was
written from an acceptance criterion or a business rule, before a line of code exists — which is
the only moment at which it is easy.

---

## Practical rules

- **End-to-end scope (Ch. 17 §17.4):** if a user would complain loudly when a flow breaks,
  that flow deserves an end-to-end test plan. Do not cover every tiny rule with E2E tests.
- **Security bias (Ch. 17 §17.5):** an agent may implement the happy path and forget the
  denial path. For every feature ask: who is allowed, who is not allowed, what input must
  be rejected, what must never be exposed?
- **Quality rule (Ch. 3 §3.6):** if you cannot describe how to test a requirement, you do
  not understand the requirement well enough yet.

**A fourth rule is specific to this product: test that emptiness is not reassuring.** The
ordinary bias in a test suite is to check that correct data appears. Here the expensive failure
is the opposite — a ranking that could not be computed, a board that could not load, an asset
that could not be scored — each of which renders as a calm empty screen and reads as *nothing is
wrong*. FTEST-002, FTEST-003 and FTEST-004 exist for that, and they are the tests most likely to
be quietly weakened into checking that no error was thrown.

---

> Blueprint: blueprints/03-tests/01-plan/test-plan.md
