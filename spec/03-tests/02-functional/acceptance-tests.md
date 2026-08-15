# Acceptance Tests

> Source: Ch. 4 §4.6, Ch. 3 §3.6.
> Checks whether requirements work **from the user or business view**.

Written in Given–When–Then, derived directly from the acceptance criteria in
[`../docs/requirements.md`](../../01-docs/02-requirements/requirements.md).

---

| Test ID | Requirement | AC | Scenario | Expected result | Status |
|---|---|---|---|---|---|
| ATEST-001 | REQ-F-001 | AC-001 | A prepared scenario whose asset records use different codes for the same asset is loaded | Each asset appears once; every value shows its source and age; unmatched records are flagged, not merged | Planned |
| ATEST-002 | REQ-F-001 | AC-002 | A prepared data file is missing or malformed at load | The last good picture is shown, marked stale and dated, and the failing file is named | Planned |
| ATEST-003 | REQ-F-002 | AC-003 | A signed-in operations manager opens the planning view with a scenario loaded | Every asset in the scenario appears in one list ordered by risk | Planned |
| ATEST-004 | REQ-F-003, BR-002 | AC-004 | A user looks at any risk rank on any screen | The reasons behind it are available beside it in plain words, never behind a separate request | Planned |
| ATEST-005 | REQ-F-004 | AC-005 | A forecast change inside the scenario is applied to a ranked list | The list re-ranks and the previous order stays retrievable for comparison | Planned |
| ATEST-006 | REQ-F-006, BR-001 | AC-006 | An operator accepts, changes, or rejects a recommendation | The outcome is recorded and **no crew movement is issued by the system** | Planned |
| ATEST-007 | REQ-F-007 | AC-007 | Two damage reports arrive for the same location | Both are visible and linked to one repair job, not two | Planned |
| ATEST-008 | REQ-F-009, BR-004 | AC-008 | Any recommendation or human decision occurs | A row is appended with its timestamp and acting user, and no path exists to edit or remove it | Planned |
| ATEST-009 | REQ-R-001 | AC-009 | A signed-in user who is not an admin attempts to load or replace a scenario | The action is refused and the refusal is recorded | Planned |
| ATEST-010 | REQ-NF-003 | AC-010 | The platform is running with stale data and any screen is opened | The staleness and the age are stated on the screen rather than left to be inferred | Planned |
| ATEST-011 | REQ-NF-006 | — | A ranked list is operated without a mouse, and inspected with colour removed | Every rank, its reasons and every control are reachable and operable by keyboard alone; no rank, band or state is distinguished by colour alone (WCAG 2.1 AA) | Planned |

**ATEST-011 has no `AC-###`** because REQ-NF-006 was written before it had a standard. Q-013
named WCAG 2.1 AA (CHG-006), and the test was written from the two rules
`frontend-component-spec.md` already carried rather than from an acceptance criterion that never
existed. The dash is honest; inventing an AC number would imply a criterion nobody wrote.

---

## Format

```
ATEST-001
Requirement: REQ-F-001
Acceptance criterion: AC-001

Given  [starting condition]
When   [user action or system event]
Then   [expected result]

Evidence to capture:
Status: Planned / Written / Passing / Failing / Blocked
```

---

## Examples (Ch. 5 §5.7)

| Requirement | Acceptance criteria |
|---|---|
| A team member must be able to create a task. | **Given** a signed-in team member, **when** they submit a valid task form, **then** the task is saved and shown in the task list. |
| A viewer must not edit tasks. | **Given** a signed-in viewer, **when** they open a task, **then** edit controls are hidden or disabled. |
| Task creation must handle errors. | **Given** a network failure, **when** the user submits the form, **then** the system shows an error and keeps the typed values. |

---

## Rule

Every **Must** requirement needs at least one acceptance test. An acceptance test that
cannot fail is not a test — state the exact observable result, not "it works."

---

## Written out — the four that decide whether version one is worth anything

```
ATEST-004
Requirement: REQ-F-003, BR-002
Acceptance criterion: AC-004

Given  a loaded scenario with a computed ranking
When   a signed-in user looks at any ranked asset on any screen
Then   at least one plain-words reason for that rank is reachable beside it
And    reaching it requires no second request that could fail separately
And    an asset whose reasons cannot be produced does not appear as a rank at all —
       it appears as UNSCORED, with why

Evidence to capture: the ranking response body showing a non-empty `reasons` array on
every item; a screenshot of one row with its reasons open
Failure meaning: assumption A3 is untested. A rank nobody can interrogate is the exact
thing operators were predicted not to act on, and the product's whole trust argument
rests on this being true rather than usually true.
Status: Planned
```

```
ATEST-006
Requirement: REQ-F-006, BR-001
Acceptance criterion: AC-006

Given  a recommendation shown to a signed-in operator
When   they accept it, change it, or reject it
Then   exactly one row is appended to the decision record with the outcome, the timestamp,
       and the acting user
And    no crew movement, job assignment, or outbound message is produced by the system
And    a change or a reject without a note is refused

Evidence to capture: the decision record row; the absence of any outbound side effect
Failure meaning: the product has changed category — from decision support to automation,
with a different regulator and a different liability. This is the single test that proves
the claim the whole platform is sold on.
Status: Planned
```

```
ATEST-002
Requirement: REQ-F-001
Acceptance criterion: AC-002

Given  a scenario that loaded successfully and is in use
When   one of its prepared data files becomes missing or unreadable
Then   every screen still renders the last good picture
And    each one states that it is stale and how old it is
And    the failing file is named
And    no screen is blank, and no screen shows an error page

Evidence to capture: screenshots of all four screens with the staleness banner; the log
event naming the file
Failure meaning: the platform stops working during the event it exists to serve. REQ-NF-003
is the requirement that says it must survive the storm it describes.
Status: Planned
```

```
ATEST-009
Requirement: REQ-R-001
Acceptance criterion: AC-009

Given  a signed-in user holding the `user` role
When   they attempt to upload, replace, or delete a scenario — through the interface or by
       calling the endpoint directly
Then   the request is refused with 403
And    no file is written and no scenario row is created
And    the refusal is appended to the decision record

Evidence to capture: the 403 response; an empty scenarios table diff; the refusal row
Failure meaning: any user can replace the storm every other user is deciding against.
Hiding the upload control in the interface does not make this pass — the test calls the
endpoint directly for exactly that reason.
Status: Planned
```

---

> Blueprint: blueprints/03-tests/02-functional/acceptance-tests.md
