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
| FF-001 | Simplicity / feasibility | Structural | No import cycle between the scoring module, the API layer, and the data layer | 0 cycles | **Not wired yet** | Block merge, once wired |
| FF-002 | Simplicity / feasibility | Structural | No view module imports the scoring module directly; a view reaches it through the API layer only (REQ-NF-005) | 0 direct imports | **Not wired yet** | Block merge, once wired |
| FF-003 | Reliability / graceful failure | Operational | Remove or corrupt each prepared data file in turn, then open every screen | 0 empty screens and 0 error pages; every stale render states its age | **Not wired yet** | Block merge, once wired |
| FF-004 | Auditability | Security | Both the `BEFORE UPDATE` and `BEFORE DELETE` triggers exist on `decision_records`, **and** an `UPDATE` issued against that table is refused by the database (ADR-004) | 2 triggers present; 0 statements accepted | **Not wired yet** | Block merge, once wired |
| FF-005 | Auditability | Structural | Every delivered ranking has a matching `decision_records` row of kind `recommendation` | 0 rankings without a row | **Not wired yet** | Block merge, once wired |
| FF-006 | Reliability / graceful failure | Operational | Each of the seven known data defects in `data-and-integration-spec.md` §4 is caught by its own check, run against a fixture that deliberately contains all seven | 7 of 7 caught | **Not wired yet** | Block merge, once wired |
| FF-007 | Auditability | Security | No model-phrased reason reaches a screen naming a factor absent from the computed input, or asserting a strength the arithmetic did not produce (ADR-009 rule 3) | 0 displayed outputs unmatched to their input | **Not wired yet** | Block merge, once wired |

**Every row says `Not wired yet`, and that is the truthful state.** No pipeline exists on this
project — Round 7 writes the task that builds one and wires these seven into it. Writing `CI` and
`Block merge` today would assert enforcement nobody has built, which is exactly the decay this
file exists to catch, committed by the file itself.

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
