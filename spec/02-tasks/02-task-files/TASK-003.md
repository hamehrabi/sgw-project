# TASK-003: Ranked risk list with plain-words reasons, scored by a deterministic rule

> Written from the template in `TASK-001.md` when the task was picked up.

---

**Task ID:** TASK-003
**Task title:** Ranked risk list with plain-words reasons, scored by a deterministic rule
**Priority:** P0
**Status:** Done — accepted 2026-08-15, `review-log.md`
**Assigned to:** AI agent

---

## Source requirement or spec section

REQ-F-002 · REQ-F-003 · BR-002 · ADR-005 · ADR-007 · `ai-boundary-spec.md` · `subdomain-map.md`

## Business reason

**This is the only Core row in `subdomain-map.md`** — the one thing the product competes on.
Everything before it was scaffolding for this list, and everything after it reads from it.

## Goal

Every asset in a scenario, ordered by risk, each rank carrying the plain-words reasons behind
it — computed by the same arithmetic that produced the score, never authored separately.

---

## The exit test is explainability, not correctness

**The code cannot earn trustworthiness and must not pretend to.** ADR-007's four weights are an
assumption: nobody has validated 0.40 / 0.25 / 0.20 / 0.15 against a real storm, the band
boundaries at 60 and 30 are round numbers rather than measured thresholds, and calibration with
SGW's engineers is owed before anyone treats a ranking as authoritative. No test written here
can change that, and a suite that appears to would be worse than none.

**What the code can earn is explainability.** Every rank shows the arithmetic that produced it,
so a person can disagree with a *specific factor* rather than with a number. That is a property
this task either has or does not, and it is testable.

So the done criteria below assert that **the reasons are computed and correct** — that each one
traces to a factor's actual contribution, that the strengths follow from the same percentages,
and that a rank never appears without them. **They do not assert that the ranking is right.**
That distinction is the task, not a caveat on it.

---

## Recording the weights as an assumption

The ADR is not enough: an operator reading a screen does not read ADRs, and a developer editing
arithmetic does not either. **Three places, all required:**

1. **`scoring/`'s module docstring** states that the four weights are uncalibrated, that their
   source is ADR-007's reasoning rather than SGW data, and that the exit condition is
   calibration with SGW's engineers.
2. **One named config block holds the weights, the band boundaries and the reason-strength
   thresholds.** No magic number appears in the arithmetic. Changing a weight must be a
   one-place edit — that is the entire point of expecting them to change, and a value spread
   across four expressions is a value nobody will dare adjust.
3. **Every stored ranking records the weight-set version that produced it**, so a later
   recalibration cannot silently rewrite history. A rank read next month must still say which
   numbers produced it.

And on screen: the ranking states that its weights are uncalibrated. Not a disclaimer nobody
reads — the same standing that `StalenessBanner` has, because a confidently wrong ranking is
more persuasive than a wrong model, not less.

---

## Expected files or components

**Backend:** `scoring/` filled — the weighted rule, the reasons, the ordering. `store/` gains
`risk_scores` (migration 005) with BR-002's constraint and the weight-set version. `api/` gains
`GET /api/v1/scenarios/{id}/risks`.
**Frontend:** `views/` gains `RiskList` and `ReasonPanel`.

## Step-by-step instructions

1. The config block first — weights, bands, strength thresholds, and a version identifier.
2. The scorer as a pure function of a loaded asset. **Score and reasons come out of one
   computation**, never two (ADR-005).
3. Migration 005: `risk_scores` with `check (json_array_length(reasons) >= 1)` and the unique
   `(scenario_id, asset_id, forecast_revision)`.
4. Unscorable assets: rendered **UNSCORED with the reason they could not be scored**, never
   omitted and never defaulted low (`reliability-specification.md` §3).
5. The endpoint, then `RiskList` and `ReasonPanel`.
6. Wire **FF-005** and **FF-007** into `ci/fitness.py`, mutation-checked before the register
   says they run.

## Constraints / Boundaries

- **Do not call OpenAI.** ADR-009's phrasing layer is blocked on Q-029 and Q-030 and is not
  this task. The computed reasons are the deliverable; phrasing is a rendering of them.
- **Do not fold criticality into risk** (ADR-007). A `critical_facility` asset is not scored
  higher — risk orders the planning list, criticality badges the dispatch queue.
- Do not introduce a training step, a model file, or a learned parameter (ADR-005).
- Do not create `decision_records` — TASK-004 owns it and its two triggers.
- Do not tune a weight to make a ranking look agreeable. **A rule tuned until the output looks
  right is indistinguishable on screen from one that is right**, with reasons wrong in the same
  confident way. If a ranking looks wrong, that is a finding for calibration, not a diff.

## Acceptance check / Done criteria

1. A rank never exists without at least one reason — **refused by the store**, not the caller.
2. Every reason names a factor that actually contributed, and its strength matches that
   factor's share of the score (≥ 25% Strong, 10–25% Moderate, < 10% Slight).
3. Ordering is total and stable; equal scores tie-break by oldest condition observation.
4. Changing one weight in the config block changes the ranking, and no arithmetic elsewhere
   needs editing. **Asserted with a non-default weight set**, per `AGENT.md`'s first lesson.
5. Every stored ranking carries the weight-set version that produced it.
6. An unscorable asset appears in the list, marked unscored, with a reason — never omitted,
   never low.
7. The screen states that the weights are uncalibrated.
8. **FF-007 runs**, and was seen to fail before the register said it runs. **FF-005 moves to
   TASK-004** — it asserts a `decision_records` row per delivered ranking, and that table does
   not exist until TASK-004 creates it with its two triggers. Wiring it here would mean writing
   a check with nothing to check, which is the CHG-010 failure mode by another route.

## Tests to run or create

| Test ID | Defined in |
|---|---|
| UTEST-009, UTEST-010 | `03-tests/02-functional/unit-tests.md` |
| ATEST-003, ATEST-004 | `03-tests/02-functional/acceptance-tests.md` |
| FTEST-004 | `03-tests/04-failure/failure-tests.md` |
| ITEST-001 (the ranking half, owed from TASK-002) | `03-tests/02-functional/integration-tests.md` |
| PTEST-001 | `03-tests/03-non-functional/performance-tests.md` |
| EVAL-001 | `03-tests/03-non-functional/ai-evals.md` |

## Out of scope

- ADR-009's phrasing layer (blocked on Q-029, Q-030)
- The decision record (TASK-004), re-ranking on a forecast change (TASK-006), crew placement
  (TASK-007)

## Stop condition

**Stop and ask** rather than proceeding if:

- A factor ADR-007 names cannot be computed from what the loader produces. That is a data gap,
  and CHG-011 was one already.
- PTEST-001's 5-second limit cannot be met at 220 assets. That is a design finding, not a
  reason to quietly narrow the test.
- Anything suggests letting the model see the asset, or scoring inside a request rather than
  serving a stored result.

---

> Written from: blueprints/02-tasks/02-task-files/TASK-001.md
