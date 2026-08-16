# TASK-008: Dismiss a false alarm in one action

> Written from the template in `TASK-001.md` when the task was picked up, and shaped like
> `TASK-004.md`.

---

**Task ID:** TASK-008
**Task title:** Dismiss a false alarm in one action
**Priority:** P1
**Status:** In review — built 2026-08-16, **blocked twice on the same day and remediated the same
day**. Five change entries raised and left **proposed**: CHG-033, CHG-034, CHG-035, and — from the
remediation — **CHG-036** and **CHG-037**.
**Assigned to:** AI agent

---

## Source requirement or spec section

REQ-F-008 · REQ-F-009 · AC-008 · US-010 · SEC-Z-001 · CON-003 · ADR-002 · ADR-004 · BR-001

| Row read before this file was written | Says |
|---|---|
| `requirements.md` REQ-F-008 | *The dispatcher must be able to dismiss a false alarm in one action, so that alarms which are cheap by design do not slow real work.* **Should.** |
| `requirements.md` AC-008 (REQ-F-009) | *Given **any** recommendation or human decision, when it occurs, a row is appended carrying the timestamp and the acting user, and no path exists to edit or remove it.* |
| `product-spec.md` US-010 | *As a dispatcher, I want to dismiss a false alarm in one action, so that alarms which are cheap by design stay cheap to clear.* |
| `frontend-component-spec.md` `DismissAlarmControl` | Purpose *clear a false alarm in one action*; data *the report*; states *idle, saving, error*; rule **One action, but never anonymous — it captures who dismissed it and why (REQ-F-008).** |
| `api-specification.md` endpoint index | `POST /api/v1/damage-reports/{report_id}/dismiss` — *Dismiss a false alarm in one action* — REQ-F-008 — **Signed in.** The index carries the row; §*Endpoint template* says the remaining ten endpoints are *"specified when their task is written"*, so the request and response below are this file's to fix. |
| `technical-spec.md` §7.2 / `security-specification.md` §RBAC | *Dismiss a false alarm — Admin **yes**, User **yes**.* Not privileged: the dispatcher holds `user`. |
| `database-design.md` §1 (Damage report) | *A dismissed report carries who dismissed it and why (REQ-F-008).* |
| `database-design.md` §3 (`damage_reports`) | `dismissed_by` optional → `users.id`; `dismissed_reason` optional; `check (status <> 'dismissed' or (dismissed_by is not null and dismissed_reason is not null))`. |
| `database-design.md` §3 (`decision_records`) | `kind` … `check in ('recommendation','accept','change','reject','**dismiss**','placement')`. |
| `unit-tests.md` UTEST-011 | Rule *a dismissal is one action but never anonymous*; normal *dismissal with actor and reason succeeds*; edge *a one-character reason is accepted — brevity is not the rule*; failure *a dismissal with no actor or no reason → refused by the store*. |
| `edge-cases-and-failures.md` UTEST-011 | Edge *a dismissal with no reason given*; risk *an anonymous dismissal — control made cheap and untraceable*. |

## Business reason

**A cheap control that is untraceable is not a control.** REQ-F-008 exists because storm alarms
are cheap by design: a dispatcher who cannot clear a false one in one action will stop clearing
them, and the board stops being the shared picture REQ-F-007 built. The whole risk of making the
action cheap is that it also becomes anonymous — a report vanishing from a shared board with
nobody's name on it, during the hour when somebody else is ringing back about the same street.

**So the two halves pull against each other and both are the requirement.** One action, and never
anonymous. `frontend-component-spec.md` writes them in one sentence for that reason, and this task
is where the second half becomes something the database refuses rather than something the screen
remembers to ask for.

## What "never anonymous" turned out to mean, and why it needed three decisions

`database-design.md` §3 already carries the constraint REQ-F-008 is traced to, and it is not
sufficient on its own. Three things were found while preparing this task, each raised as a change
entry rather than guessed silently, each following a precedent this repository has already set:

1. **`dismissed_reason is not null` is satisfied by a reason that is not one.** A direct insert of
   `''`, `'   '` or `char(9) || char(10)` was **accepted** — the same non-place-wearing-different-
   whitespace hole CHG-023 found in `damage_reports.location`, on the column beside it. → **CHG-033**.
2. **A dismissal could be rewritten.** Nothing stopped `update damage_reports set dismissed_by = …,
   dismissed_reason = 'never mind'` on an already-dismissed report, so *who dismissed it and why*
   meant *whoever wrote it last*. CHG-026's argument, one table over. → **CHG-034**.
3. **`decision_records.kind` has permitted `'dismiss'` since migration 006 with no writer, no reader
   and no decided shape**, while AC-008 requires **any** human decision to be appended with its
   timestamp and acting user. Third instance of the shape CHG-021 and CHG-029 named. → **CHG-035**.

## Goal

A dispatcher clears a false alarm with one action. The report leaves the working list carrying who
cleared it and why; a row is appended to the append-only record saying the same thing; and neither
can afterwards be made anonymous or be rewritten — **because the database refuses the statement**,
not because the code declines to issue one.

## Expected files or components

**Backend:** migration **014** (`damage_reports` rebuilt with a named dismissal check;
`damage_reports_dismissal_is_final`; `decision_records_dismiss_shape`) with an up and a down.
`store/dispatch.py` — `dismissal_reason()`, `dismiss_report()`. `store/decisions.py` —
`append_dismissal()`, and `_append` gains the ability to write inside a caller's transaction.
`api/dismissals.py` — `POST /api/v1/damage-reports/{report_id}/dismiss`. `api/views.py` —
`dismissal_item`. `main.py` — the router.
**Frontend:** `views/DismissAlarmControl.tsx`; `DispatchBoard` renders one per open report;
`lib/api.ts` gains `dispatch.dismiss`.
**Tests:** `unit/test_UTEST-011_dismissal_never_anonymous.py`,
`integration/test_TASK-008-AC9_migration_014_up_and_down.py`, `e2e/TASK-008.spec.ts`.

**The migration is 014 and the brief reserved 011.** 010 and 011 went to TASK-006, 012 to TASK-007
and 013 to TASK-009, so the reserved number had drifted for the fourth time; the register records
the same drift for the three tasks before this one.

## Step-by-step instructions

1. Read REQ-F-008, AC-008, US-010, the `DismissAlarmControl` row and the two `database-design.md`
   §3 blocks **before** writing anything, and check that every state they describe has somewhere
   to live (`AGENT.md`, third lessons row).
2. Write UTEST-011 first, from `unit-tests.md`'s three columns, and run it. Confirm each case fails
   because the feature is missing.
3. Migration 014: rebuild `damage_reports` so the dismissal check is **named** and refuses a reason
   that is only whitespace, is untrimmed, or is over the bound. Add the two triggers. Re-assert both
   `decision_records` triggers. Ship the down migration and prove the round trip.
4. `dismiss_report`: one transaction — the `update` and the `decision_records` insert together, so a
   dismissal that is not recorded cannot exist and a record of a dismissal that did not happen
   cannot either.
5. The endpoint: `reason` required, trimmed, 1..2000; `409` on a second dismissal naming the first;
   `404` for an unknown report; `400` for everything the store would refuse, so the caller never
   sees a `500` for a mistake they made.
6. `DismissAlarmControl`: one press, no confirmation dialog, the typed reason survives a failed
   write, and the board reflects the dismissal without losing the job it was filed against.
7. Mutation-check every case. Run the whole gate.

## Constraints / Boundaries

- **Never write `UPDATE` or `DELETE` against `decision_records`.** The dismissal appends a row; a
  correction would be another row, and nothing here issues one.
- **Never drop, disable or recreate either append-only trigger.** 014 re-asserts both and its down
  migration removes only what it added.
- **The response is a record, never an action** (BR-001). Dismissing an alarm cancels no work,
  closes no repair job, and sends nothing anywhere. A job whose reports were all dismissed stays on
  the board reading *explained*, because removing work from a shared board is not this endpoint's
  decision to take (CHG-020 said so before this task existed).
- **A location is a neighbourhood and never finer** (CON-003, REQ-NF-007). The dismissal payload may
  carry the report's own neighbourhood and nothing else about where it was.
- **Not privileged.** Both roles dismiss; the deny path is *signed out* and nothing else (STEST-001).
- Do not build bulk dismissal (`agent-task-list.md` A-013 names it out of scope), an un-dismiss
  path, a `duplicate` writer (CHG-021 declined one), or a dismissed-report list on the board.

## Acceptance check / Done criteria

1. One signed-in request dismisses a report: `201`, the report leaves the board's working list, and
   the job it was filed against keeps its location and gains a dismissed count (CHG-020).
2. The stored report carries the acting user and the reason; the reason is stored **trimmed**.
3. A dismissal with **no actor**, issued **directly against the database**, is refused by the store,
   and the refusal names `damage_reports_dismissal_is_attributed`.
4. A dismissal with **no reason** — null, `''`, `'   '`, `char(9)||char(10)` — is refused the same
   way, with an accepted control beside each that differs in exactly one field (CHG-033).
5. **A one-character reason is accepted.** Brevity is not the rule; presence is.
6. A dismissal, once recorded, cannot be rewritten or undone by a direct `UPDATE` (CHG-034) — and a
   report that is not dismissed can still change status, so the trigger refuses a thing rather than
   everything.
7. Exactly one `decision_records` row of kind `dismiss` is appended, naming the report, the actor and
   the reason; the store refuses one that disagrees with the report it names (CHG-035).
8. A second dismissal returns **409**, names the first, and leaves the first byte-identical.
9. Migration 014 has an up and a down, both run, both `decision_records` triggers still **refusing**
   afterwards (a real `UPDATE`, not two names read out of `sqlite_master`).
10. The dismissal and its record survive a restart, and a second dismissal is still refused after one.
11. `DismissAlarmControl` is proven by a browser case: one press dismisses, an empty reason is
    refused, and a failed write keeps what was typed.
12. Nothing is dispatched, cancelled or sent (BR-001), and the log line says so.

## Tests to run or create

| Test ID | Defined in |
|---|---|
| **UTEST-011** | `03-tests/02-functional/unit-tests.md` · `03-tests/04-failure/edge-cases-and-failures.md` |
| TASK-008-AC9 (migration round trip) | This file, criterion 9 — the shape `test_TASK-006-AC13`, `test_TASK-007-AC10` and `test_TASK-009-AC10` established |
| TASK-008 browser case | This file, criterion 11 — `frontend-component-spec.md`'s `DismissAlarmControl` row |
| ATEST-007, ITEST-003, UTEST-012 (re-run) | The board this task writes to — CHG-020, CHG-021 and CHG-022 all name a dismissed report |
| STEST-001 (re-run) | Its `DATA_ROUTES` already lists this endpoint; the deny path must hold once it exists |

## Out of scope

Bulk dismissal (A-013) · un-dismissing · a writer for `status = 'duplicate'` (CHG-021 declined one) ·
a dismissed-report list or filter on the board · deleting a repair job whose reports were all
dismissed · `GET /api/v1/damage-reports/{id}` · re-ranking (TASK-006) · placements (TASK-007).

## Stop condition

**Stop and ask** if dismissing appears to require editing an existing `decision_records` row, if a
migration appears to need either append-only trigger dropped, if anything suggests a dismissal
should cancel work or notify a system outside the platform, or if the reason field appears to need
to hold anything finer than a neighbourhood.

---

## What was built, and the mutation that makes each claim red

**Twenty mutations.** Each was applied, the named part of the gate run, and reverted;
`git status --short` showed no unexpected change after every one. The counts are what was
observed, not what was expected.

| Claim | Mutation that is now red |
|---|---|
| CHG-033 — the reason must be a reason | Restoring 009's clause (`dismissed_by is not null and dismissed_reason is not null`) fails **7**: the five direct inserts `''`, `'   '`, `char(9)||char(10)`, `' \r\v\f '`, `'  padded  '`, the over-length one, and the bound tie |
| …and it is the **two-argument** `trim` that does it | `trim(dismissed_reason)` — the obvious spelling — fails exactly **1**: `char(9)||char(10)` is stored again while `'   '` is still refused. CHG-023's hole, reproduced on the new column |
| …and it refuses a **dismissal**, not every row | Dropping the `status <> 'dismissed' or` guard fails **2**, one of them filing an ordinary open report |
| …and the bound has one home | Removing the schema's `<= 2000` fails the `sqlite_master` tie |
| CHG-034 — a dismissal is never rewritten | The trigger **absent** fails **3** (and 2 migration cases). The trigger **present and wrong** — `when old.status = 'open'` — fails **27**, including the silent case that exists to catch exactly that |
| CHG-035 — the store refuses an untraceable dismissal record | The trigger absent fails **7** (and 2 migration cases); clause 1 alone fails **1**; dropping the reason from the `exists` fails **1** |
| …and each refusal is read by its own sentence | With the trigger gone, the actorless case still raises `IntegrityError` — migration 006's check catches it — and the test goes red anyway, because it names which refusal it expects |
| One action is one transaction | Removing the append fails **15**; committing the `update` before the insert fails the atomicity case alone |
| The reason is stored trimmed | `dismissal_reason` returning the raw value fails **1** |
| The 409 is decided before the write | Never taking the already-dismissed branch fails **2**, one of them the restart case |
| The 404 names which refusal | Changing its sentence to *that storm could not be found* fails **1** |
| Nothing is dispatched | `outcome="dispatched"` in the log line fails **1** |
| Clearing one call is not clearing the job | Dismissing every report at the job fails **1** in `pytest` and **1** in the browser |
| The migration round trip | The down migration not dropping `decision_records_dismiss_shape` before the rebuild fails **5**; the rebuild forgetting `damage_reports_seq` fails **1** |
| One action, in the browser | Deleting `<DismissAlarmControl>` from `Report` fails **4**; removing `!reason.trim()` from `disabled` fails **1**; clearing the field before the write succeeds fails **1** |

---

## What the two reviews found, and what was done about it

**Two reviews, both **Block**, the second on a byte-identical tree — so seven findings stood open
at once: three from the first round, four from the second, two of them the same finding re-run.**
Every fix below names the mutation that now turns it red, because that is the part a later reader
can check. **Every mutation was applied, the named stage of the gate run, and reverted, and
`git status --short` showed no unexpected file after each one.**

**One migration, 015, and it is a new file rather than an edit to 014** — 008 and 009 were
TASK-005's two remediations and 011 was TASK-006's, and a migration that has run is a fact about a
database somebody may already hold.

| Finding | What was done | Mutation that is now red |
|---|---|---|
| **The Block** — *exactly one audit row* was two pieces of service code and the store said nothing (criterion 7) | **CHG-036.** A partial `unique` index, `decision_records (subject_id) where kind = 'dismiss'`. No table is created and no trigger is dropped, so ADR-004 is not approached | The two service guards removed together (`if False and report["status"] …`, `where id = ? and ? is not null`) fails **3** — the 409 case, the **new identical-retry case**, and the restart case — and the identical retry that used to be answered `201` twice with **2** rows is now a `500` with **1**. Removing the **index** alone fails **3**: the store-level case and two migration cases |
| …and the test that stood in the way of the fix | `test_the_store_accepts_a_dismissal_record_that_agrees_with_its_report` required `len(rows) == 2`. Its report is now dismissed by **direct statement**, which writes no audit row, so the permitted control is the only row and the assertion is `== 1`. What it proves is unchanged | Not a mutation: the assertion is `== 1` and the index would refuse `== 2`. The change is recorded in CHG-036 rather than left to be noticed |
| The `coalesce` clause had never been fed the state it was written for (CHG-022) | Two new cases: an **unattached report dismissed through the endpoint** — the state no test had ever produced — and the same report with a payload claiming a job it has not | Deleting both `coalesce`s fails **2** where it used to leave all 499 green |
| The `dismiss` row had a writer and no reader anyone had asked | `test_the_decision_record_reader_serves_the_dismissal` reads `GET /scenarios/{id}/decisions` as an admin and requires the row, its subject, its actor and its payload | `and kind <> 'dismiss'` in `decisions.read_all` fails **1** where it used to leave all 499 green |
| **A live hole, no mutation needed** — three definitions of whitespace and the browser's was the strictest | **CHG-037.** One alphabet in `dispatch.BLANK_CODEPOINTS`, repeated in the schema as `char(...)` and in `frontend/lib/dismissal.ts`, with a test that reads all three | The schema's alphabet back to 014's six ASCII fails **9**; the service constant narrowed fails **14**; the browser's list shortened fails the tie; `String.prototype.trim()` back in the control fails **1 browser case** |
| The same hole in `damage_reports_location_is_a_neighbourhood`, unreachable only because of a serialiser default | The same alphabet, and the five `instr` clauses become one `not glob '*[' \|\| char(…) \|\| ']*'` over the alphabet without the space | That check back to 014's form fails **5** UTEST-012 cases, four of them a whitespace-only neighbourhood written as raw UTF-8 |
| `DISMISSAL_REASON_MAX` had a third copy tied to nothing and a fourth as a literal | One definition in `frontend/lib/dismissal.ts`; `lib/api.ts` re-exports it and the browser case imports it | The browser copy set to `8` fails **1**, where it used to leave `tsc`, `lint`, `build` and all 36 specs green |
| `and r.scenario_id = new.scenario_id` was violated by no case | A dismissal record filed under a **second storm**, with that storm's record asserted empty afterwards | Deleting the clause fails **1** where it used to leave all 499 green |
| REQ-NF-007's area figure at the dismissal call site was asserted by nothing | UTEST-012's three-way shape, carried across the module boundary: after the dismissal, **4** open in the storm, **2** in the neighbourhood, **1** for the asset — the wrong two asserted **absent**, and the pre-dismissal **3** as well | Replacing the call with a whole-storm count fails **1** where it used to leave all 499 green |
| **Found while fixing, and it is not in either review** | The browser suite was **racing itself**. `fullyParallel: false` keeps one file serial; seven files still ran in seven workers against one SQLite database, and ATEST-007's *the empty board reads "no damage reported"* — whose docstring rests on *"nothing else in the suite files a damage report"* — was racing TASK-008's first case, which files one. It won for two tasks and lost the moment the timing shifted | `workers: 1`. Reverting it fails **1** (`ATEST-007`), and the untouched tree passes only by winning the race |

**What was left alone, deliberately.** `store/scenarios.py` carries its own six-ASCII whitespace
copy for `name` and `source_note` (CHG-031) and has the same hole; it belongs to TASK-009, and
widening an entry already under review is the drift the register exists to catch. `json.dumps`
keeps `ensure_ascii` at its default: the constraint is fixed first, so the tidy-up is safe when
somebody makes it.

**The two observations both reviews recorded are unchanged and still need a human.** CHG-035 says
of the report and its audit row that *"neither can move afterwards"*, and a direct `update` still
moves a dismissed report's `location` and `repair_job_id` while the record keeps the old ones;
CHG-034 says that narrowness is deliberate. **The two proposed entries contradict each other about
the same guarantee**, no code issues either statement, and whoever decides them should see both
sentences rather than only the stronger one.

---

> Written from: blueprints/02-tasks/02-task-files/TASK-001.md
