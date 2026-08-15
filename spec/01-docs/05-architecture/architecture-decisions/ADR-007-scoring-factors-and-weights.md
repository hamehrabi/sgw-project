# ADR-007: The scoring factors, their weights, and keeping criticality out of risk

**ADR ID:** ADR-007
**Status:** Accepted
**Date:** 2026-08-15
**Decision owner:** The developer (sole owner for the prototype — Q-026)
**Review date:** After the first operator sessions, and whenever SGW's engineers review the weights

---

## Context

ADR-005 fixed the **kind** of scorer — a deterministic weighted rule, behind a boundary that
keeps the swap to a trained model one module wide — and explicitly left its **content** open as
Q-025. It also named the risk that content carries: a weighted rule is trivial to adjust until
the ranking looks agreeable, and a rule tuned to look right is indistinguishable on screen from
one that is right, with reasons wrong in the same confident way.

This is the core subdomain. The ranking is the thing the product competes on, and it is the
subject of both guesses that could end the project.

## Options considered

1. **Four factors with fixed weights, and reason strength derived from each factor's share of
   the score.** Every input traces to a column the prepared scenario already carries. Costs the
   thing all fixed weights cost: it encodes what people currently believe drives failure.
2. **Fold criticality into the risk score** — weight a hospital feeder or a water plant higher so
   it ranks above an ordinary asset. Intuitive, and it is the option to reject hardest. See below.
3. **Fewer factors — gust and flood zone only.** Simpler, faster to build, and it throws away
   the two inputs (age, condition) that the source PRD's §7 data work went to the most trouble
   to obtain. It would also make BR-003's whole source-and-age display pointless.

*Compared on:* which interface is simpler · which is more general · which forces callers
to do work that should be inside · which is cheaper to reverse.

## Decision

**Four factors, weighted, normalised, summed, scaled to 100.**

| Factor | Weight | Normalised as |
|---|---|---|
| Forecast gust vs asset design threshold | **0.40** | ratio, capped at 1.0 |
| Flood zone (FEMA VE = 1.0, AE = 0.7, X = 0.1) | **0.25** | lookup |
| Age vs expected service life | **0.20** | ratio, capped at 1.0 |
| Condition rating, decayed by inspection staleness | **0.15** | rating × decay |

**Score = 100 × weighted sum.** Bands: **High ≥ 60 · Medium 30–59 · Low < 30.**

**Reason strength comes out of the same arithmetic**, never from a separate step: a factor
contributing **≥ 25%** of the total renders as *Strong*, **10–25%** as *Moderate*, **under 10%**
as *Slight*.

**Criticality is kept separate from risk.** A `critical_facility` asset is not scored higher.
Risk orders the planning list; criticality badges the dispatch queue.

## Reason

The weights follow the physics of the decision the source PRD describes: what is about to hit
the asset matters most, where it stands matters next, and what condition it is in matters least —
not because condition is unimportant, but because §7 measured that condition data is between two
months and six years old, and a factor you half-trust should not carry the weight of one you
measure. The staleness decay makes that distrust arithmetic rather than a caveat.

**Reason strength is derived, not authored**, which is ADR-005's implementation rule made
concrete. A percentage-of-score threshold cannot drift away from the score, because it *is* the
score. Nothing can produce a "Strong" label for a factor that contributed 3%.

**Why criticality must stay out of the score.** A hospital feeder is not more *likely* to fail —
it is more *costly* when it does. Folding the two together produces a number that answers
neither question: the manager can no longer see which assets are most likely to break, and the
dispatcher can no longer see which breakages hurt most. Both would then be looking at one figure
whose reasons mix a wind forecast with a value judgement about hospitals, and no plain-words
explanation can make that legible. **Separating them is what keeps both explainable**, which is
BR-002's entire purpose.

## Consequences

- **Positive:** Every rank is arithmetic somebody can check by hand. Reasons cannot lie about the
  score. Both the planning view and the dispatch board get a number that answers their own
  question. The four factors map exactly onto the four CSVs in a prepared scenario, so nothing
  needs an input the fixture does not carry.
- **Trade-off or limitation:** **These weights are an assumption, not a finding.** Nobody has
  validated 0.40/0.25/0.20/0.15 against a real storm, and the band boundaries at 60 and 30 are
  round numbers rather than measured thresholds. A wrong weight produces a confidently wrong
  ranking with confidently wrong reasons — more persuasive than a wrong model, not less. **The
  operator sessions exist to challenge exactly this**, and calibration with SGW's engineers is
  owed before anyone treats the ranking as authoritative.
- **Rule the AI assistant must follow during implementation:** The weights, the band boundaries
  and the reason-strength thresholds are configuration, not constants in code. Reason strength is
  computed from each factor's share of the total — never assigned, never hard-coded per factor.
  **Never add `critical_facility` to the score.** Any weight change re-runs the full eval set
  (`ai-evals.md` §4) and is recorded as a decision, not a tweak.

> **If no trade-off is visible, keep looking.** A choice with no downside was never a
> choice — you are comparing in the abstract instead of weighted for this context.

## Compliance

| Enforced by | Where |
|---|---|
| FF-005, and the quality floor in `ai-evals.md` | [`../../04-technical-spec/fitness-functions.md`](../../04-technical-spec/fitness-functions.md) |

`ai-evals.md`'s `failure_recall_at_decile` is what judges whether these weights are any good, and
`reasons_are_faithful` — the one human-sampled scorer — is what catches a reason label that has
drifted from its arithmetic.

## Revisit when

SGW's engineers review the weights, **or** the first operator sessions produce a disagreement
about a ranking, **or** `failure_recall_at_decile` misses its floor on a replayed storm. The
first is a calibration owed; the other two are the system telling you the assumption was wrong.

## Impact

| Dimension | Impact |
|---|---|
| Security | Neutral. |
| Reliability | Positive. A pure function over four columns has no artifact to load and nothing to drift. |
| Performance | Positive. Four multiplications per asset; 220 assets is arithmetic, not a workload. |
| Cost | Zero. |
| Maintainability | Mixed — and the mixture is the point. Trivial to read and trivial to change, which is why any weight change re-runs the evals and is recorded rather than adjusted. |

## Related

- Related requirements: REQ-F-002, REQ-F-003, BR-002, BR-003
- Related technical spec sections: `ai-boundary-spec.md` §1–§4, `ai-evals.md` §1–§4
- Answers: Q-025. Depends on Q-017's `assets.csv` and `weather.csv` columns.
- Supersedes / superseded by: — (fills the content ADR-005 deferred)

---

> Blueprint: blueprints/01-docs/05-architecture/architecture-decisions/ADR-000-template.md
