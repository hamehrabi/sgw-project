# Unit Test Plan

> Source: Ch. 4 §4.6, Ch. 17 §17.2.
> Unit tests check **small pieces of logic** that can be tested without running the entire
> application: calculations, validators, permission checks, formatting rules, helpers.

A good unit test plan names the **rule**, the **input**, the **expected output**, and the
**reason the rule matters**. You do not need final test code here — only behavior clear
enough that code can later be generated against it.

---

| Test ID | Requirement | Rule under test | Normal case | Edge case | Failure case | Status |
|---|---|---|---|---|---|---|
| UTEST-001 | REQ-NF-002, SEC-A-003 | No credential reaches a log or a response | a successful sign-in logs `user_id` only | a failed sign-in logs the attempt with no password field | a password, hash, or session value in any log line or body → test fails | Planned |
| UTEST-002 | REQ-F-001 | Defect 1 — the same asset carries different codes in different systems | `SS-1042` and `TX-4471` matched by the join key → one asset | a near-match below the confidence bar → `needs_review`, not merged | a merge performed on a guess → test fails | Planned |
| UTEST-003 | REQ-F-001 | Defect 2 — condition data is old | an inspection dated 2 months ago carries its date | an inspection dated 6 years ago still loads, carrying its date | a condition stored with no `condition_observed_at` → refused by the store | Planned |
| UTEST-004 | REQ-F-001, BR-003 | Defect 2 (display half) — estimated vs measured | a measured value renders as measured | an estimated value renders visually distinct | an estimated value indistinguishable from measured → test fails | Planned |
| UTEST-005 | REQ-F-001 | Defect 3 — gust values are largely absent | wind taken from the forecast grid square | a station record present but null → still uses the grid | wind derived from a station column that is 97% empty → test fails | Planned |
| UTEST-006 | REQ-F-001 | Defect 4 — broken customer totals | a percentage computed against an independent population figure | total present and plausible → used | total of zero → **no percentage is published**, not a zero percentage | Planned |
| UTEST-007 | REQ-F-001 | Defect 5 — impossible outage counts | counts within the population pass | count equal to the population passes with a flag | more customers out than exist → flagged at load, by name | Planned |
| UTEST-008 | REQ-F-001 | Defects 6 and 7 — repair records are not failure records; public data is county-level | failures taken only from outage records | a routine work order present → excluded from the failure set | a failure list derived from repair logs → test fails | Planned |
| UTEST-009 | BR-002 | A score cannot exist without at least one reason | a scored asset carries ≥1 reason | an asset with exactly one reason is valid | a score with an empty `reasons` array → refused by the store, not by the caller | Planned |
| UTEST-010 | REQ-F-002 | Ranking order is total and stable | distinct scores order by score | equal scores tie-break by oldest condition observation | the same input producing two different orders across runs → test fails | Planned |
| UTEST-011 | REQ-F-008 | A dismissal is one action but never anonymous | dismissal with actor and reason succeeds | a one-character reason is accepted — brevity is not the rule | a dismissal with no actor or no reason → refused by the store | Planned |
| UTEST-012 | REQ-NF-007 | Damage locations are aggregated before they leave | a neighbourhood-level figure in a log | a single report in a sparse area still aggregates | a household-identifying location in any log or export → test fails | Planned |

---

## Examples (Ch. 17 §17.2)

| Requirement detail | Unit test idea |
|---|---|
| A password must contain at least eight characters. | Pass short passwords and confirm they are rejected. |
| A project title cannot be empty. | Pass an empty title and confirm validation fails. |
| A task status must be `todo`, `in_progress`, or `done`. | Pass an unsupported status and confirm it is rejected. |
| A due-date validator rejects dates in the past. | Pass yesterday's date and confirm rejection. |

---

## What belongs here

- Validation functions
- Business-rule predicates (`can_create_task`, `is_project_member`)
- Value formatting and parsing
- Metric/aggregation helpers
- Filter parsing
- Status transition rules

## What does **not** belong here

- Database round-trips → [`integration-tests.md`](integration-tests.md)
- Full user journeys → [`end-to-end-tests.md`](end-to-end-tests.md)
- Response contract shape → [`integration-tests.md`](integration-tests.md)

---

## Template

```
UNIT TEST PLAN: [rule name]
Requirement ID: REQ-###
Rule: [the rule in one sentence]

Normal case:  [input] -> [expected]
Edge case:    [input] -> [expected]
Failure case: [input] -> [expected, with a clear error]

Why this rule matters:
```

Executable tests live in [`../tests/unit/`](../05-executable/unit).

---

## Written out

```
UNIT TEST PLAN: A score cannot exist without its reasons
Test ID: UTEST-009
Requirement ID: BR-002 (ADR-005)
Rule: A risk score is never produced or stored without at least one plain-words reason,
      and the reasons are produced by the same computation that produced the score.

Normal case:  an asset with age, condition and forecast inputs -> score + 3 reasons
Edge case:    an asset whose score rests on one factor          -> score + 1 reason, valid
Failure case: a score with reasons = []                          -> REFUSED BY THE STORE

Why this rule matters:
  This is the core subdomain's only hard rule. The check must assert the STORE refuses the
  write, not that the caller declines to make it — a service-layer check is removed by the
  first refactor with every functional test still passing. ADR-005 adds a second half: the
  reasons must come out of the same computation as the score. A reason generated separately
  is a plausible sentence that explains nothing, and it is indistinguishable on screen from
  one that does.
```

```
UNIT TEST PLAN: The seven measured data defects
Test ID: UTEST-002 to UTEST-008
Requirement ID: REQ-F-001
Rule: Each of the seven defects in data-and-integration-spec.md §4 is caught by its own
      check at LOAD time, against a fixture that deliberately contains all seven.

Normal case:  a clean record loads
Edge case:    a record on the boundary of each rule loads with the correct flag
Failure case: each defect, injected on purpose -> caught by name, at load

Why this rule matters:
  These are not hypothetical. Every one was measured in real public files of the same kinds
  and injected into the fixture on purpose, so the design is proven against dirty data
  rather than clean data. Six of seven caught looks identical to seven of seven in any
  summary output, which is why there are seven separate ids rather than one.
  FF-006 guards the same property structurally.
```

```
UNIT TEST PLAN: Ranking order is total and stable
Test ID: UTEST-010
Requirement ID: REQ-F-002
Rule: The same scenario and forecast revision always produce the same order, and ties are
      broken by the asset whose condition observation is oldest.

Normal case:  distinct scores        -> ordered by score, descending
Edge case:    two identical scores   -> the older observation ranks first, every run
Failure case: two runs of the same input producing different orders -> FAIL

Why this rule matters:
  An operator who re-opens the ranking mid-storm and sees a different order has no way to
  tell whether the situation changed or the software did. The tie-break rule is not
  arbitrary: ranking the least-known asset higher is the conservative direction, given a
  missed failure costs roughly a thousand times a wasted trip.
```

## What belongs here vs. elsewhere

| This is a unit test | This is NOT a unit test |
|---|---|
| `can_create_task(user, project)` returns False for a Viewer. | The `POST /tasks` endpoint returns 403 for a Viewer → integration. |
| Title validator rejects 121 characters. | The form keeps typed values after a 400 → end-to-end. |
| Due-date comparator rejects yesterday. | The task row is absent after a rejected create → integration. |

---

> Blueprint: blueprints/03-tests/02-functional/unit-tests.md
