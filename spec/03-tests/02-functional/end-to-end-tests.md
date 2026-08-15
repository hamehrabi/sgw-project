# End-to-End Test Plan

> Source: Front Matter workspace (`03-tests/end-to-end/`), Ch. 17 §17.4, Ch. 18 §18.7.
> E2E tests prove the system works **from the user's point of view**, not only from the
> code's point of view.

> **Practical rule (Ch. 17 §17.4):** if a user would complain loudly when a flow breaks,
> that flow deserves an end-to-end test plan.

Keep E2E tests focused. Do not try to cover every tiny rule with them — use them for the
flows that decide whether the product is usable.

---

| Test ID | Requirement | User flow | Goal | Expected result | Status |
|---|---|---|---|---|---|
| E2E-001 | REQ-F-002…006 | Place crews against the ranking | An operations manager can go from a loaded storm to a recorded crew placement without assembling anything by hand. | The placement exists, is traceable to the ranking and revision it was made against, and survives a failed save as typed values | Planned |
| E2E-002 | REQ-F-001, REQ-F-010 | Load a prepared storm | An admin can drag a storm's files in and reach a rankable scenario, or a legible refusal. | The scenario appears alongside any others; a refusal names the file and changes nothing | Planned |

**Only two flows earned an E2E test**, and the choice is the practical rule applied literally.
A manager who cannot reach a placement, or an admin who cannot load a storm, has no product —
they would complain loudly and immediately. Everything else in the suite is a unit, integration
or security test. The dispatch board did not earn one: its behaviour is covered by ITEST-003 and
ATEST-007, and an E2E test of it would be a slower version of the same assertions.

---

## Flow test template

```
Test ID:
Requirement:
Flow name:

Preconditions:      [signed-in role, seeded data]

Steps:
1.
2.
3.

Expected visible result:
Failure path tested:
Expected error result:
Evidence to capture:   [screenshot, log line, database state]
Status:
```

---

## UI test inputs (Ch. 18 §18.7)

Describe the **screen**, the **user action**, and the **visible result**. This prevents the
agent from writing tests that depend on imaginary buttons, labels, or flows.

| UI test input | Example |
|---|---|
| Screen | Login page |
| User action | Enter valid email and password, then click Sign in. |
| Expected visible result | Dashboard opens and the user name is visible. |
| Failure path | Enter wrong password. |
| Expected error result | Error message appears; password field is cleared; user stays on the login page. |

---

## Written out

```
Test ID:      E2E-001
Requirement:  REQ-F-002, REQ-F-003, REQ-F-004, REQ-F-005, REQ-F-006
Flow name:    Place crews against the ranking

Preconditions: signed in as a user; one scenario loaded at forecast revision 0; the
               scenario's fixture carries all seven data defects on purpose

Steps:
1. Open the planning view.
2. Read the ranked list. Open the reasons on the top-ranked asset.
3. Apply the scenario's forecast change.
4. Read the re-ranked list; open the previous order for comparison.
5. Accept one recommendation and reject another, giving a note on the reject.
6. Record a crew placement against the current ranking.

Expected visible result:
  - Every rank on screen has its reasons reachable beside it, at every step
  - Any asset that could not be scored appears as UNSCORED with why — not missing
  - After step 3 the order changes AND the revision-0 order is still reachable
  - The placement is saved and shows which revision it was made against

Failure path tested:
  Repeat step 6 with the store made to fail the write.

Expected error result:
  - A clear message and a retry option
  - THE TYPED PLACEMENT IS STILL ON SCREEN
  - No placement row exists

Evidence to capture: screenshots at steps 2, 4 and 6; the decision record rows from step
5; the empty placements table after the failure path
Status: Planned
```

```
Test ID:      E2E-002
Requirement:  REQ-F-001, REQ-F-010
Flow name:    Load a prepared storm

Preconditions: signed in as an admin; one scenario already loaded, so the test also proves
               a second load does not disturb the first

Steps:
1. Open the scenario screen.
2. Drag in the prepared files for a second storm, with a name and a source note.
3. Watch the upload progress through to parsing and then ready.
4. Open the joined asset view for the new storm.
5. Switch back to the first storm.

Expected visible result:
  - The progression reads uploading -> parsing -> ready, distinctly, not one spinner
  - Assets the join could not match are shown, flagged for review, and not merged
  - Every value carries its source and its age; estimated looks different from measured
  - Switching back shows the first storm's ranking, unchanged

Failure path tested:
  Repeat step 2 with a file that is valid for three of five inputs.

Expected error result:
  - The load fails as a whole, naming the file and the stage
  - NO second scenario is created
  - The first storm still ranks, unchanged

Evidence to capture: screenshots of each stage; scenario row count before and after the
failure path; the SCENARIO_PARSE_FAILED log line
Status: Planned
```

---

## Production smoke test (Ch. 28 §28.12)

The same flows, run against the deployed system after release.

1. Sign in as a test user.
2. Create the primary entity.
3. Add a child record.
4. Perform the core action.
5. Trigger the main failure path and confirm the safe message.
6. Confirm logs and audit events exist.
7. Confirm monitoring shows no critical errors.

**As it applies here:** sign in · load a small prepared storm · confirm it ranks and that every
rank carries reasons · accept one recommendation · remove one of its data files and confirm the
staleness banner appears rather than a blank screen · confirm the decision record holds the
recommendation and the acceptance · confirm no error dashboard entry. Step 5 is the one worth
running in production rather than only in a test environment: the failure it exercises is the
one that only ever happens mid-storm.

→ [`../ops/production-readiness-checklist.md`](../../07-ops/01-deployment/production-readiness-checklist.md)

Executable tests live in [`../tests/end-to-end/`](../05-executable/end-to-end).

---

> Blueprint: blueprints/03-tests/02-functional/end-to-end-tests.md
