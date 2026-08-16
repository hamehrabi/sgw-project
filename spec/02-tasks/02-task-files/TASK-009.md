# TASK-009: Switch between several loaded storms

> Written from the template in `TASK-001.md` when the task was picked up.

---

**Task ID:** TASK-009
**Task title:** Switch between several loaded storms
**Priority:** P2
**Status:** In review — built 2026-08-16. Suite **450 + 1 skipped over three runs**, `ruff`,
`ci/fitness.py` (6 of 7 wired), `ci/evals.py`, `tsc`, `lint`, `build` and all **32** Playwright
specs pass. Three change entries raised and left **proposed**:
**CHG-030** (nothing lists the loaded storms, so the component whose whole purpose is choosing
among them had nothing to choose from), **CHG-031** (`scenarios.source_note` was holding a
SHA-256 digest, because the content key §5's idempotency rule turns on had no column of its
own — and the rule lived in one service-layer lookup that a direct insert walked past), and
**CHG-032** (`scenarios` had no total order, so a list of storms loaded in the same clock tick
came back in coin-flip order — CHG-018's decision, on the fourth table read as a list).
**It is not Done until somebody who did not write it says so** — three of four directed checks
failed at each of the last two reviews on this project, and a green gate is where a review
starts.
**Assigned to:** AI agent

---

## Source requirement or spec section

REQ-F-010 · US-002 · CHG-001 · CON-005 · ADR-002 · REQ-R-001 ·
`requirements.md` REQ-F-010 — *"An admin must be able to load a prepared storm scenario, so
that version one can be exercised end to end without any live connection"* ·
`product-spec.md` §7 (capability table) — *"several storms can be loaded at once and switched
between"*, US-002 — *"I want to keep several storms loaded and switch between them, so that I
can compare or re-run **without destroying the one I have**"*, and the load flow's success
path — *"The scenario appears **in the list** alongside any others already loaded, and becomes
**selectable**"* ·
`technical-spec.md` §7.2 — *Switch between loaded scenarios: Admin yes, User yes* ·
`database-design.md` §5 — *"Asset, risk score, damage report, repair job: every read and write
is scoped by `scenario_id`. **Two scenarios must never blend into one ranking**"*, and
*"Scenario: written only by an admin (REQ-R-001). **Readable by every signed-in user**"* ·
`database-design.md` §3 — `scenarios.source_note`, *"which prepared dataset this is, and where
it came from"* ·
`data-and-integration-spec.md` §3 — the multipart body carries *"the scenario's name, its
`source_note`, and the prepared files themselves"*; §5 — *"Loading a scenario whose content is
identical to one already loaded replaces that one in place; different content is a new
scenario, and **several scenarios coexist**"* ·
`api-specification.md` — the `GET /risks` endpoint template, whose query parameters include
`cursor` and whose response carries `next_cursor`, neither of which was ever built ·
`frontend-component-spec.md` — `ScenarioSwitcher` (*"Choose among the loaded storms. Data
needed: loaded scenarios: name, source note, loaded date. States: loading, success, empty,
error. The empty state reads 'no storm loaded yet' and points an admin at the upload panel. It
must never render as a scenario with no risk"*) and `AppShell` (*"The scenario selector is
always present, because everything below it is scoped to one scenario"*) ·
`integration-tests.md` — **ITEST-005**, written out as a row.

## Business reason

**One storm is enough to test the idea; several are what make it usable.**
`product-spec.md` §12 puts switching in *Could-have* with exactly that sentence, and US-002 says
what the operator is actually protecting: *comparing or re-running **without destroying the one
I have***. A platform that holds one storm at a time makes every new load a decision to throw
the last one away, in the middle of the week the storm is happening.

**The risk this task carries is not the feature; it is the blend.** CLAUDE.md and
`database-design.md` §5 both name it, and `security-review.md` §4 says it plainly: *a missing
scope here is a correctness bug — two storms blended into one ranking would look entirely
plausible*. Nothing on screen would look wrong. An operator would place crews against a list
that mixed two storms' assets and would have no way to tell. **This task is the first one in
which more than one storm is reachable from a person's fingers**, which is what turns a scoping
rule that has been true by construction into a rule that can be broken.

## What was missing, and why it needed deciding

Three things stood between `ScenarioSwitcher` and its own specification. Each is raised as a
change entry rather than guessed, and each is left `proposed`.

- **Nothing lists the loaded storms (CHG-030).** The component's *Data needed* column is
  *loaded scenarios: name, source note, loaded date*, `product-spec.md` §9 promises the loaded
  storm *"appears in the list alongside any others"*, and the endpoint index carries
  `POST /scenarios` and `GET /scenarios/{id}` and no collection read. This is CHG-009's shape
  exactly — *a component required to know something, and no endpoint that returns it* — and it
  is the sixth instance of `AGENT.md`'s third lessons row.
- **`source_note` was holding a SHA-256 digest (CHG-031).** §5's *identical content replaces in
  place* needs somewhere to keep what "identical" is keyed on. No column existed, so
  `api/scenarios.py` wrote the digest into `source_note` — the one column §3 defines as *which
  prepared dataset this is, and where it came from* — and threw the admin's typed note away.
  The switcher's third field was a 64-character hex string. Worse for this task: the rule that
  two loads of one storm are one storm was a `find_by_content_key` lookup **in front of** the
  insert, which is ADR-002's exact prohibition, and a direct insert produced two rows for one
  upload — two entries in the switcher for the same storm.
- **`scenarios` had no total order (CHG-032).** CHG-018 gave `repair_jobs`, `damage_reports` and
  `decision_records` a monotonic `seq` because `datetime.now(UTC).isoformat()` resolves to about
  15.6 ms here and a random UUID is not a tiebreak. `scenarios` was not in that list, because
  nothing read it as a list. This task is what reads it as a list.

**A fourth gap needed no entry, because the specification already decided it.** ITEST-005's side
effect is *zero rows from the other scenario in the response, **at any page***, and
`GET /risks` had `limit` and no way to ask for a second page — so the clause could not be
exercised at all. `api-specification.md` writes the endpoint out in full with a `cursor` query
parameter and a `next_cursor` in the response; both were owed from TASK-003 and are built here.
That is implementing the contract, not changing it.

## Goal

An operator signs in, sees every storm that is loaded — by name, by where it came from, and by
when it was loaded — chooses one, and reads it. Choosing a second storm replaces the whole
screen with the second storm's data. **At no moment does one storm's row appear under another
storm's name**, on any page of any read, including while a slower response for the storm they
just left is still in flight.

## Expected files or components

**Backend:** migration **013** — `scenarios.seq`, `scenarios.content_key`,
`scenario_uploads.content_key`, two unique indexes and two triggers
(`scenarios_identity_shape`, `scenarios_identity_is_fixed`); both `decision_records` triggers
re-asserted, neither dropped. `store/scenarios.py` — `all_loaded`, `NAME_MAX`,
`SOURCE_NOTE_MAX`, `content_key` written to its own column. `store/rankings.py` — `read_ranking`
gains the paging the endpoint now passes. `api/scenarios.py` — `GET /api/v1/scenarios`, and
`cursor` / `next_cursor` on `GET /scenarios/{id}/risks`. `api/views.py` —
`loaded_scenario_item`.
**Frontend:** `views/ScenarioSwitcher.tsx` (replacing `views/ScenarioSelector.tsx`, which
carried only the empty state and said in its own header that the other three arrive with this
task); `views/AppShell.tsx` hands the chosen storm down the way it already hands the identity
down; `views/ScenarioView.tsx` clears on a switch and ignores a superseded read;
`views/ScenarioUploadPanel.tsx` gains the source-note field the API has always required;
`lib/api.ts`.
**Gate:** no new fitness function. FF-004 proves the append-only triggers survive migration 013.

## Step-by-step instructions

1. Write `TASK-009.md` (this file), having read REQ-F-010, US-002, `database-design.md` §3 and
   §5, `frontend-component-spec.md`'s `ScenarioSwitcher` and `AppShell` rows, and ITEST-005 as
   written out in `integration-tests.md`.
2. Write **ITEST-005** first, in
   `03-tests/05-executable/integration/test_ITEST-005_scenarios_never_blend.py` — the name
   `executable-tests.md` reserved for it. Run it; confirm each case fails because the feature is
   missing rather than because of a typo. Add the store-level file the done criteria name, the
   migration round-trip file, and the browser case for criterion 11.
3. Migration **013**. Ship an up and a down. **The task brief reserved 010 and 010 was already
   taken** — TASK-006 used 010 and 011, and TASK-007 used 012. 013 is the next free number;
   nothing else about the instruction changes. This is the third time the reserved number had
   drifted, which TASK-006 and TASK-007 both recorded before this.
   `scenarios` is **not rebuilt**: six tables reference it with `on delete cascade`, so
   `drop table scenarios` inside a rebuild deletes every asset, ranking, report, job and
   decision record in the database. The rules therefore go in `alter table … add column`, two
   unique indexes, and two triggers — CHG-026, CHG-028(b) and CHG-029's argument reused: *a rule
   the schema cannot express without destroying something else is a trigger, and it says the
   true and narrower thing — what may be written.*
4. `store/scenarios.py` writes `content_key` to its own column and the admin's note to
   `source_note`; `all_loaded` reads the list `order by seq desc` — newest first, by a key that
   is total.
5. `GET /api/v1/scenarios`: signed in, both roles (§7.2). Every storm, each with its name, its
   source note, its loaded date, its current revision, its age, whether it is stale, how many
   assets it holds and whether that revision has an order behind it.
6. `GET /risks` gains `cursor` and `next_cursor`, as `api-specification.md` writes them.
7. `ScenarioSwitcher`: loading, success, empty and error. The empty state reads *no storm loaded
   yet* and points an admin at the upload panel. Choosing a storm re-reads everything below.
8. Mutation-check every test written. Run the whole gate.

## Constraints / Boundaries

- **Every read is scoped by `scenario_id`, and the scope is in the store** (ADR-002,
  `database-design.md` §5). A filter a route handler remembers to apply is the finding CHG-019
  and CHG-023 were both raised for, and `review-log.md` carries it as a standing **Block**
  condition. The question to ask of every column is *what can a direct insert put in it*.
- **A switch is a read, and it writes nothing** — no scenario is deleted, replaced, archived or
  marked current. Nothing about a storm changes because somebody looked at a different one;
  §7.2's *delete or replace a scenario* is a separate admin action and is not built here.
- **`decision_records` is untouched.** Migration 013 adds nothing to it, drops neither trigger,
  and re-asserts both (ADR-004, BR-004).
- **The model scores, ranks and bands nothing** (ADR-009). This task adds no prompt, and no
  asset name, identifier, coordinate or note enters one.
- **Nothing leaves the platform** (BR-001, BR-005, REQ-R-003). A list of storms is a read of
  this database and of nothing else.
- **No location finer than the store already holds** (CON-003, REQ-NF-007). The list endpoint
  carries no asset, no coordinate and no neighbourhood — a count and nothing more.
- **The two storms are never compared side by side.** `agent-task-list.md` A-014 puts that out
  of scope explicitly, and one screen showing two storms' numbers is the blend this task exists
  to prevent, wearing a feature's clothes.
- Nothing under `01-docs/` is edited. CHG-030, CHG-031 and CHG-032 are entries in the change
  log, **proposed**.
- Do not build dismissal (TASK-008) or the fitness-function gate (TASK-010).

## Acceptance check / Done criteria

1. `GET /api/v1/scenarios` returns every loaded storm with its name, its **source note as the
   admin typed it**, and its loaded date; both roles may read it, and a signed-out caller may
   not (SEC-Z-001, STEST-001).
2. **The ranking for one storm contains zero rows from the other, at every page** — asserted by
   paging the whole ranking with a limit smaller than the storm, not by reading the first page
   (ITEST-005).
3. **Every scenario-scoped read is scoped**: the asset view, the ranking, the board, the
   decision record and the forecast-revision list each answer with one storm's rows and none of
   the other's, with two storms loaded and both non-empty.
4. **A storm's own identifiers do not work against another storm.** Asking for storm A's asset
   through storm B, placing a crew at it, or filing a report against it is refused — and the
   refusal is read out of the message, because `404` and `400` each have more than one cause in
   this API.
5. **The store refuses a second scenario row for one upload**, issued **directly against the
   database** and not through the endpoint (§5's idempotency, in the schema rather than in
   `find_by_content_key`).
6. **The store refuses a scenario that cannot be identified or shown**: a null, short, long, or
   non-hexadecimal content key; a blank, whitespace-only or over-long source note; a blank,
   whitespace-only or over-long name. Each refusal is read out of the message so it cannot pass
   for another clause's reason, and a well-formed direct insert is accepted first so the
   negatives mean something.
7. **One bound governs each text column**: the trigger's numbers and
   `scenarios.NAME_MAX` / `scenarios.SOURCE_NOTE_MAX` are the same numbers, and a test fails
   when they disagree — otherwise the specified `400 validation_error` silently becomes a `500`
   (CHG-023's lesson, applied before it bites).
8. **The list has a total order.** Two storms loaded inside one clock tick come back in the
   order they were loaded, every time; `seq` is unique, and the ordering is asserted against
   rows whose `loaded_at` strings are **identical**.
9. **The list, the notes and the sequence survive a restart** — a second application over the
   same database file reads the same storms, in the same order, with the same source notes
   (ADR-002; `AGENT.md`'s standing rule that a task introducing durable state owns its restart
   test).
10. Migration 013 has an up **and** a down, both were run, and **both `decision_records`
    triggers are present and still refusing at every point of the round trip** — asserted by
    issuing a real `UPDATE`, not by reading two names out of `sqlite_master`.
11. **A person switches between two loaded storms in a real browser**, the switcher shows all
    four of its states, and no row of the storm they left is on screen after the switch —
    including the ranking, the asset table and the board.
12. **No switch writes anything.** Asserted as a dump of every row of every table before and
    after, with a positive case beside it proving the dump can see a write.

## Tests to run or create

| Test ID | Defined in |
|---|---|
| ITEST-005 (`integration/test_ITEST-005_scenarios_never_blend.py`) | `03-tests/02-functional/integration-tests.md` |
| TASK-009 done criteria 5, 6, 7 and 8 (`unit/test_TASK-009-AC5_store_refuses_a_second_row_for_one_storm.py`) | this file — the same way TASK-006 and TASK-007 each wrote a file for a criterion no plan row owned |
| TASK-009 done criterion 10 (`integration/test_TASK-009-AC10_migration_013_up_and_down.py`) | this file |
| TASK-009 done criterion 11 (`frontend/e2e/TASK-009.spec.ts`) | this file. *A person switches between storms* is a claim about somebody at a screen, and `AGENT.md`'s standing rule is that such a claim needs a browser case — it is the fourth time a criterion about a screen would otherwise have been satisfied by reading source |
| STEST-001 (it now has a collection endpoint to refuse) | `03-tests/03-non-functional/security-tests.md` |

## What the mutation check found

**Every case written for this task was mutation-checked — 40 mutations.** Each breaks one claim,
was applied, was run against the part of the gate that claims to cover it, and was reverted; the
tree was restored from the original bytes after every one. The counts are what actually turned
red, not what was expected to.

| Mutation | What turned red |
|---|---|
| The list is served oldest first | **3** |
| The list is ordered by the clock and a random id, as it was before CHG-032 | **1** — the three storms with byte-identical timestamps |
| Reading the list becomes admin-only | **1** — the allow path, which is the half `AGENT.md` predicts will be missed |
| The list carries the storm's asset ids | **1** (CON-003) |
| The list reports the content digest as the source note — the defect CHG-031 names | **2** |
| The whole identity trigger neutered (`when 0`) | **23** |
| The trigger **present and wrong**, conditioned on another table | **31 failed, 20 errors** |
| Clause (a) removed — the content key need not be a digest | **7** |
| Clause (b) removed — a storm needs no name | **9** |
| Clause (c) removed — a storm needs no source note | **9** |
| The whitespace enumeration goes back to SQLite's spaces-only `trim()` | **5** — one per whitespace character CHG-023 found it cannot see |
| `unique (content_key)` removed — §5 goes back to the service layer | **2** |
| `unique (seq)` removed — two storms may claim one place in the order | **1** |
| The update guard removed — a loaded storm's identity can be rewritten | **1** |
| The update guard **present and neutered** (`when 0 and …`) | **1** |
| The store's bound raised to 5000 with the service constant left at 200 | **2** |
| The service constant raised to 5000 with the store bound left at 200 | **2** |
| The up migration writes the placeholder instead of recovering the typed note | **1** |
| The down migration does not put the digest back in `source_note` | **3** |
| The down migration removes the append-only re-assertion | **1** — and **0** before the mutation was corrected. See below |
| The down migration leaves this migration's triggers behind | **5** |
| `next_cursor` is always null — the ranking is never pageable | **4** |
| A cursor issued for another storm is applied instead of refused | **1** |
| A cursor issued for another revision is applied instead of refused | **1** |
| An unreadable cursor silently becomes the first page | **1** — and **0** before the mutation was corrected |
| The page order loses its `asset_id` tiebreak | **1** — and **0** before the test was fixed. See below |
| The recommendation records the page instead of the whole ranking | **1** |
| The asset view stops scoping by storm | **20 errors** — the fixture's own premise fails |
| The endpoint stops refusing an over-long name, leaving the trigger to answer 500 | **1** |
| The endpoint stops refusing a blank source note | **1** |
| The endpoint goes back to storing the digest as the source note | **1** |
| The parse stores the digest in `source_note`, as it did before CHG-031 | **2** |
| `find_by_content_key` reads the note column again | **2** |
| `ranked` is derived from the pointer instead of the stored rankings | **1** |
| The list reports every storm as ranked | **1** — and **0** before the test was fixed |
| The asset count is the whole database's assets | **1** — and **0** before the test was fixed |
| `ScenarioView` does not clear when the storm changes | **1** browser case — and **0** before it was fixed |
| A superseded read is rendered instead of discarded | **1** browser case |
| The switcher's error state borrows the empty state's words | **1** browser case |
| The switcher's option drops the source note | **2** browser cases |
| The switcher's loading state renders as the empty one | **1** browser case |
| A non-admin is pointed at the upload panel | **1** browser case |
| Choosing a storm does nothing | **4** browser cases |
| The panel discards the typed source note | **1** browser case |
| The shell does not re-read the list after a storm is loaded | **1** browser case |
| The switcher stops saying whether a storm has an order behind it | **1** browser case — and **0** before it was written |
| The switcher reports every storm as ranked | **1** browser case |

**Five assertions could not have failed, and the mutations are what said so.**

**The ranking's page order was the worst of them, and it is `AGENT.md`'s row about resolution
wearing different clothes.** `order by rank is null, rank` leaves the whole UNSCORED group in an
order SQLite does not define, and an undefined order under `limit`/`offset` serves a row twice on
one page and never on another — on a 220-asset storm with a handful of unscorable assets, which is
exactly what FTEST-004 exists for, that is an asset silently missing from a ranking. Removing the
`asset_id` tiebreak left all 21 cases green, because **each of the three shipped fixtures has
exactly one unscored asset**, so the coarse key is already total for every fixture in the
repository. The case that sees it writes several unscored rows directly, at a revision the storm
carries and has not ranked, deliberately in an order that is not their asset-id order.

**`asset_count` was asserted as `> 0`**, so a count with no `where scenario_id = ?` passed. It now
names all three answers — 7 for one storm, 5 for the other, 12 in the database — which is the
same lesson one column over.

**`ranked` was asserted only where it was true**, in both halves of the gate. The API case now
moves a storm's pointer directly to a revision nothing ranked and requires the list to say so
while the other storm still says the opposite; the browser case serves one ranked and one unranked
storm and requires the two rows to read differently.

**`ScenarioView`'s clearing-on-switch was covered by an assertion the loading state satisfied on
its own.** Both tables set their own loading state before their request goes out, so the old rows
vanish whether or not the state is cleared — and the panels that genuinely fail to clear are the
ones drawn from `scenario`: `ForecastRevisionControl` and `StalenessBanner`. Without the reset, a
storm carrying three forecasts leaves its revision list above a storm that carries one. The case
now holds **every** scenario-scoped read and requires both panels to be absent mid-switch.

**And one mutation did not mutate, which is the fifth time this repository has recorded that
trap.** Adding `drop trigger decision_records_no_update` to 013's down migration is a no-op,
because the same file re-asserts both triggers at the end; the real mutation is to remove the
re-assertion. The same shape caught the cursor mutation: an `if False:` branch inserted *above* an
untouched check changes nothing. A mutation that does not mutate reports a clean bill.

## Out of scope

Comparing two storms side by side (`agent-task-list.md` A-014 names it) · deleting or replacing
a scenario (`technical-spec.md` §7.2 — a separate admin action, and the only path that would
exercise CHG-024's cascade) · dismissing a false alarm (TASK-008) · the fitness-function gate
(TASK-010) · **paging the asset view and the board**: `GET /risks` is the endpoint
`api-specification.md` writes out with a cursor and the endpoint ITEST-005 names, and giving the
other two a paging contract nothing specifies would be inventing an API · **a "current storm"
stored per user**: nothing asks for it, and a durable pointer to what somebody was last looking
at is a new column and a new decision · no phrasing model (Q-029, Q-030) · no new fitness
function.

## Stop condition

**Stop and ask** if switching appears to require deleting, replacing or archiving a storm; if it
appears to require a write of any kind; if a scope can only be enforced in a route handler; if a
migration appears to need either `decision_records` trigger dropped — including for a table
rebuild, which is why the rules in 013 are triggers; or if anything suggests two storms should
be rendered in one list.

---

> Written from: blueprints/02-tasks/02-task-files/TASK-001.md
