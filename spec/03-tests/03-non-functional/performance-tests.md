# Performance Test Plan

> Source: Ch. 17 §17.6, Ch. 7 §7.9, Ch. 24 §24.5.
> You do not need enterprise load testing in every project, but you should define simple
> performance expectations **before** code generation.

A useful performance plan starts with a plain-language target: how fast should the key
action feel, how many records should the page handle, and what should happen when the
system becomes slow?

**Two checks, not a suite.** Performance was offered as a driving characteristic in Round 4 and
declined, so it is governed as a requirement to pass rather than a shape to build around. No
fitness function guards it, and `fitness-functions.md` says so explicitly.

---

| Test ID | Workflow | Metric | Target | Data volume | Action if exceeded | Status |
|---|---|---|---|---|---|---|
| PTEST-001 | Apply a forecast change and re-rank | Time to the updated ranking on screen | **Under 5 s** for 220 assets | The fixture: 220 assets, ~5,000 forecast rows | Profile the scoring pass first; it is the only unbounded loop in the product. Then the read. Do **not** add a cache — `runtime-and-scale.md` §2 refuses one, with reasons | Planned |
| PTEST-002 | Page load, and opening the reason panel | Time to first usable screen; time to reasons visible | **Under 2 s** and **under 300 ms** | Same fixture | Check the board query for an unindexed scan on `damage_reports(scenario_id, status)`; check the reason payload is not re-fetched | Planned |

**Both are now runnable** (CHG-006). Q-012 gave real limits and Q-017 gave a dataset to run them
against — and the pairing is what matters: *under 5 s* means nothing without *220 assets* beside
it. These are **measured on the fixture, not promised**, which is the difference between these
figures and the source PRD's, which that document labels as starting targets.

---

## Simple performance expectations (Ch. 17 §17.6)

| Feature | Simple performance expectation |
|---|---|
| Dashboard loading | Should load within two seconds for a normal account. |
| Task list | Should handle at least 100 items without freezing. |
| Search | Results should appear quickly for common queries. |
| External service call | Show a friendly message if the service times out. |

The last row does not apply: there is no external service (Round 6).

---

## Weak vs. measurable (Ch. 7 §7.9)

| Weak statement | Stronger requirement |
|---|---|
| "The dashboard should load fast." | "The task dashboard should load within 2 seconds for a workspace with up to 1,000 tasks." |
| "Search should be quick." | "Task search should return results within 1 second for common filters." |
| "The app should support many users." | "The first version should support 50 active users in one workspace without visible slowdown." |

**Both of this project's targets moved from the left column to the right when Q-017 landed.**
*Under one minute* looked measurable and was not, because the data volume was missing. *Under
5 s for 220 assets* is measurable, which is why the rows above now say Planned.

---

## Performance risks to check in review (Ch. 20 §20.5)

| Performance risk | What to check |
|---|---|
| Repeated queries | Does the code query the database inside a loop? |
| Overfetching | Does it load fields or records that are not needed? |
| Slow external calls | Does one request depend on many network calls? |
| Missing limits | Can a user request unlimited records? |
| Blocking work | Should heavy work move to a background job? |

Three of these are already answered by design and are worth checking anyway, because a design
decision is not an implementation: the ranking endpoint is bounded at 500 items per page
(`api-specification.md`), the scenario parse is a background job (`technical-spec.md` §9.5), and
there are no external calls to be slow. **The first row is the live risk here** — scoring
iterates every asset in a scenario, and a per-asset query inside that loop is the most likely
way PTEST-001 fails.

> Only refactor for performance when the change supports a clear goal: faster response,
> lower cost, fewer failures, or simpler scaling. Avoid asking the agent to "optimize
> everything" without a target.

---

## Performance tip (Ch. 7 §7.9)

Set realistic targets for the version you are building now. Overengineering performance
too early makes the system harder to finish and harder to understand.

Production performance signals → [`../ops/monitoring-plan.md`](../../07-ops/02-monitoring/monitoring-plan.md)

---

> Blueprint: blueprints/03-tests/03-non-functional/performance-tests.md
