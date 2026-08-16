# fitness-functions.md — Automated Architecture Governance

> **Purpose:** stop your architecture decisions from decaying silently.
> **When you use it:** one per driving characteristic, wired into the CI gate.
> **Source:** Richards & Ford, *Fundamentals of Software Architecture*, Ch. 6.

> A fitness function is **any mechanism that objectively assesses an architectural
> characteristic**: a test, a metric, a monitor, a CI script, a chaos experiment.
>
> **"High performance" is not a fitness function. A measurable threshold is.**

A test proves the feature does what was asked. A fitness function proves the **system
still has the shape you decided on**. They are different jobs; you need both.

---

## The register

| ID | Guards | Type | Check | Threshold | Runs | On failure |
|---|---|---|---|---|---|---|
| FF-001 | Simplicity / feasibility | Structural | No import cycle between the scoring module, the API layer, and the data layer | 0 cycles | **`ci/fitness.py`** | Block merge |
| FF-002 | Simplicity / feasibility | Structural | **(a)** `scoring` is imported by `api` and by nothing else — not by `store`, not by `loader`. **(b)** No scoring constant appears anywhere in `frontend/`: ADR-007's four weights, its band boundaries, and its reason-strength thresholds (REQ-NF-005) | 0 imports outside `api`; 0 scoring constants in the frontend | **`ci/fitness.py`** | Block merge |
| FF-003 | Reliability / graceful failure | Operational | Remove or corrupt each prepared data file in turn, then open every screen. **(a)** every screen renders and states its data's age; **(b)** the loss is named to an admin; **(c)** no view reads a source file at render time (CHG-013) | 0 empty screens; 0 error pages; 1 named integrity notice per removed file; 0 file reads on a render path | **`ci/fitness.py`** | Block merge |
| FF-004 | Auditability | Security | Both the `BEFORE UPDATE` and `BEFORE DELETE` triggers exist on `decision_records`, **and** an `UPDATE` issued against that table is refused by the database (ADR-004) | 2 triggers present; 0 statements accepted | **`ci/fitness.py`** | Block merge |
| FF-005 | Auditability | Structural | Every delivered ranking has a matching `decision_records` row of kind `recommendation` | 0 rankings without a row | **`ci/fitness.py`** | Block merge |
| FF-006 | Reliability / graceful failure | Operational | Each of the seven known data defects in `data-and-integration-spec.md` §4 is caught by its own check, run against a fixture that deliberately contains all seven | 7 of 7 caught | **`ci/fitness.py`** | Block merge |
| FF-007 | Auditability | Security | No model-phrased reason reaches a screen naming a factor absent from the computed input, or asserting a strength the arithmetic did not produce (ADR-009 rule 3) | 0 displayed outputs unmatched to their input | **`ci/fitness.py`** | Block merge |

**All seven now run.** `ci/fitness.py` is the gate, written during TASK-002 (CHG-010). It was
mutation-checked before this table was edited — hiding defect 4 from the fixture drove FF-006 to
`caught 6 of 7`, and a scoring constant pasted into a view drove FF-002(b) to fail — because a
gate nobody has watched fail is the same decoration as a gate nobody has built. **Every row was
mutation-checked before its `Runs` cell was edited** — FF-004 by renaming a trigger away
(`trigger decision_records_no_update is absent`), FF-005 by skipping the recommendation append
(`0 recommendation rows for one delivered ranking`), and FF-003 clause by clause (**CHG-038**).

The original wording of this paragraph is worth keeping, because the rule it states does not
stop applying once the last row is wired: writing `CI` and `Block merge` for a check nobody has
built asserts enforcement nobody earned, which is exactly the decay this file exists to catch,
committed by the file itself. **The same sentence read backwards is why this row moved:**
`Not wired yet` beside a check that now blocks a merge is the same file being wrong in the other
direction.

**FF-007 was wired by TASK-003, before the model it was written for exists.** ADR-009's rule 3
is *validate the output against its input before display*, and the phrasing layer is blocked on
Q-029 and Q-030 — so the check guards the computed text today and guards the model unchanged on
the day it arrives. Wiring the validation before there is anything untrusted to validate is the
cheap direction: the alternative is writing the guard and its first real subject in the same
change, with nothing to tell you the guard works. It was mutation-checked first — a reason
claiming an unearned strength drives it to `contributed 3% and claims Strong, not Slight`.

**Two of the seven are wired by TASK-002 rather than by TASK-010** (decided at the TASK-001
review). FF-001 needs enough modules for a cycle to be possible and FF-006 needs the seven-defect
fixture; TASK-002 is the task that first creates both. Wiring them there is cheaper than
retrofitting a gate across four tasks of drift. **The same principle then consumed TASK-010
entirely:** FF-007 was wired by TASK-003 when the scorer existed, and FF-004 and FF-005 by
TASK-004 when `decision_records` and its triggers did. Each was wired by the task that created
the thing it inspects, which is the only moment the check can be seen to fail. What was left of
TASK-010 was FF-003 alone, and TASK-010 wired it — after the views, the dispatch board and the
storm switcher existed, which is the same principle again: it is the moment there were screens
to open and a render path that could plausibly have opened a file.

**FF-003 was restated in CHG-013, before the views were written, for the same reason as FF-002
and caught one step earlier.** Its old form assumed a render path that reads source files, which
`technical-spec.md` §6 forbids — every read is served from stored results. Against the
architecture actually built, *remove a file and open every screen* could not fail: nothing on a
render path opens a file, so no screen could break. Clause **(c)** is what gives it teeth, and
it is a guard for the future rather than for today: the first feature that reads a scenario file
at render time — a download, a replay view — is the one this catches. **Say that plainly rather
than letting (a) read as a live guard**, because a check that passes for want of anything to test
is the decoration this register exists to find.

**TASK-010 wired it, and clause (a) turned out to be failable after all — in the other
direction** (CHG-038, which also records what *reads a source file* was decided to mean, and
what *open every screen* is under ADR-008). What CHG-013 said cannot happen still cannot: no
screen breaks for want of a file. What can happen is the tidy-looking opposite — a screen made
to *depend* on the file being present. With `if not integrity["intact"]: rows = []` in the
ranking read, all 534 tests pass while a lost `outages.csv` empties the risk list, and that is
the empty screen this product must never let read as safety. So (a) is checked as the claim
CHG-013 actually made: with each file removed and again with each corrupted, every screen read
still answers, still states its data's age, and **answers the same thing it answered before**.
Clause (b) is what makes that measurable rather than vacuous — it is the assertion that the
removal happened and was noticed. All of it was mutation-checked before this row moved.

**FF-002 was restated in CHG-010, at the TASK-001 review, because ADR-008 had quietly killed
it.** Its old form — *no view module imports the scoring module directly* — described a
single-process codebase. Under ADR-008 the views are TypeScript in a different process and
**cannot** import a Python module, so the check could never fail: a gate that cannot fail
governs nothing, and this register exists to catch exactly that. ADR-008 called the split a
*stronger* version of the boundary and it is, but the strength is structural, so what was left
to check moved. The new form checks the two ways scoring can still leak: reached from the wrong
module inside the backend, or **reimplemented in the frontend for display** — which is the
failure ADR-008's own consequences predicted in writing, and which the old check would have
watched happen.

**FF-004 changed shape in Round 5 and kept its guarantee** (CHG-002). ADR-002 chose an embedded
store with no role system, so the original check — *the application role holds no `UPDATE`
grant* — became unrunnable. ADR-004 replaced the mechanism with database triggers, and FF-004
now asserts that the **database** refuses the statement. The thing being guarded is identical;
only the way to observe it moved. **FF-006 is new** (CHG-003), added because Round 5 named the
seven data defects as a release gate and nothing in the register covered them.

> **`FF-` identifiers are DEFINED here, and only here.** Downstream files cite them — a task
> names the fitness functions it must satisfy, a CI pipeline names the gates it runs — and a
> citation is the id plus, at most, the characteristic it guards. **Do not restate what the
> function checks or its threshold**; those live in this register, and a second copy is a second
> thing to keep correct.
>
> A run put `FF-001`, `FF-002` and `FF-003` into a task file's test table and into an invented
> CI gate table, each with its own wording of the same check. Nothing was wrong on the day it
> was written and nothing kept the three in step afterwards.
>
> **`Runs` and `On failure` are claims about a gate that has to EXIST.** Writing `CI` here says
> a pipeline runs this check and a merge is blocked when it fails. If there is no pipeline yet —
> and on a new project there usually is not — then write **`Not wired yet`** in `Runs` and name
> the task that will wire it.
>
> These two columns arrived pre-filled with `CI` and `Block merge`. Every workspace inherited
> them, so every register asserted enforcement that nobody had built, and the file that exists
> to stop decisions decaying silently was itself the decoration it warns about. **A fitness
> function written down but not in a gate governs nothing** — say which it is.

**Types**
| Type | Measures | Examples |
|---|---|---|
| **Structural** | Code shape | Dependency cycles, layer rules, cyclomatic complexity |
| **Operational** | Runtime behaviour | p95 latency, throughput, error rate |
| **Security** | Boundaries hold | Isolation, authorization, secret scanning |
| **Process** | Delivery health | Deploy success rate, test-suite duration |

## Rules

- **One per driving characteristic, minimum.** No driver without a fitness function is
  governed — it is only documented.
- It must **fail the build**, not print a warning. A warning is a decoration.
- **Say honestly whether it runs.** The line above describes what a wired fitness function
  does, not what an entry in this table proves. A register whose `Runs` column claims a gate
  the project has not built is a success claim nobody earned — the exact failure this file
  exists to prevent, committed by the file itself.
- Every ADR's **Compliance** field names the fitness function that enforces it.
- Measure **tail percentiles**, never averages.
- If a characteristic cannot be measured, its definition is too vague — go fix the
  definition, not the function.

**No fitness function guards performance**, and that is deliberate: Round 4 offered performance
as a driver and it was not chosen. REQ-NF-001 still carries a latency limit, and it is checked
as a requirement in the test plan. The distinction is the whole point of this file — a
requirement proves the feature behaves; a fitness function proves the structure has not moved.

---

> Blueprint source: this file is new to the template — added from the architecture review.

---

> Blueprint: blueprints/01-docs/04-technical-spec/fitness-functions.md
