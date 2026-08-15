# ADR-005: A deterministic scoring rule for version one, behind a model-shaped boundary

**ADR ID:** ADR-005
**Status:** Accepted
**Date:** 2026-08-15
**Decision owner:** Tech lead (not yet named)
**Review date:** When SGW supplies validated per-asset failure history

---

## Context

The ranked risk list is the core subdomain — the one thing this product competes on, and the
subject of both guesses that could end the project (A2: does a combined ranked view change the
crew decision; A3: will operators act on a computer's ranking).

The source PRD (§5) specifies **decision-tree models** for this ability, citing the NeurIPS 2022
comparison showing tree ensembles beat deep learning on tabular asset data, and noting that they
can show their reasons — which the trust requirement needs.

Four facts constrain the choice here, and none of them were true when that PRD was written:

- **There is no training data.** Per-asset failure history is the one thing only SGW can
  supply (assumption A7), and version one does not have it. `product-spec.md` §4 already refuses
  *seven in ten failures flagged* as a version-one metric for exactly this reason.
- **About one week** (CON-002), against four capabilities.
- **BR-002 makes explainability a contract, not a preference.** A rank without reasons cannot
  be stored — the database refuses it.
- **Auditability is a driving characteristic.** Whatever produces a rank must be reconstructable
  afterwards.

## Options considered

1. **Deterministic weighted rule** — combine asset age and type, flood exposure, and forecast
   wind into a score. Transparent, needs no training data, and the reasons fall out of the
   computation itself rather than being narrated over it. Costs the thing learning is for: it
   encodes what people currently believe drives failure, and cannot discover a pattern nobody
   proposed.
2. **Trained decision-tree ensemble** (gradient-boosted trees, random forest) — the source
   PRD's choice, genuinely strong on tabular data, and able to produce feature attributions.
   Costs labelled failure history that does not exist, a held-out evaluation set, a model
   registry and version pinning, and a validation cycle that does not fit a week. Building it
   on synthetic labels would produce a model that has learned the fixture.
3. **Deep learning on tabular data** — rejected on the evidence the source PRD itself cites:
   tree ensembles outperform it on exactly this data shape, and it is the hardest of the three
   to explain. Under BR-002, hard to explain is a disqualifier rather than an inconvenience.

*Compared on:* which interface is simpler · which is more general · which forces callers
to do work that should be inside · which is cheaper to reverse.

## Decision

Two parts, and the second is what makes the first safe.

1. **Version one uses a deterministic weighted scoring rule**, implemented inside the scoring
   module and behind the boundary specified in
   [`ai-boundary-spec.md`](../../07-security-and-reliability/ai-boundary-spec.md) §2. It is a
   pure function of the loaded scenario: no training step, no model artifact, no learned
   parameter.
2. **When a trained model replaces it, it will be from the decision-tree ensemble family.**
   Deep learning is rejected for this scorer now and permanently, on explainability — a
   ranking nobody can interrogate fails A3, which is the guess the product exists to test.

## Reason

The boundary is what makes this a sequencing decision rather than a compromise.
`ai-boundary-spec.md` already fixes the swap cost at one module and hides *how* a score is
computed from every caller, so shipping a rule now costs nothing in the direction of a model
later — the API contract, the store, and every view stay identical across the swap.

Choosing the model now would mean training on data that does not exist. That does not produce a
worse model; it produces a model with no honest claim attached to it, which is worse than a rule
that is visibly a rule.

Deep learning was rejected on the source PRD's own cited evidence rather than on taste, which is
why it is recorded as rejected rather than simply unchosen.

## Consequences

- **Positive:** Version one can be built and argued with immediately. Every rank is explainable
  by construction, which is what A3 needs tested. Nothing about the swap to a model is
  foreclosed — `ai-evals.md`'s quality floor is written to judge either.
- **Trade-off or limitation:** A rule encodes today's beliefs. If the real driver of failure is
  something nobody put in the rule, the ranking will be confidently wrong and the reasons will
  be confidently wrong in the same way — which is *more* persuasive than a wrong model, not
  less. That is the reason `ai-evals.md` exists at all for a system with no model in it, and it
  is why the quality floor is measured against what actually failed rather than against the
  rule's own logic.
- **Rule the AI assistant must follow during implementation:** Never introduce a training step,
  a model file, or a learned parameter into version one. The scorer is a pure function of the
  loaded scenario. **The reasons must be produced by the same computation that produces the
  score** — never generated separately or narrated afterwards, because a reason decoupled from
  the score is a plausible sentence that explains nothing.

> **If no trade-off is visible, keep looking.** A choice with no downside was never a
> choice — you are comparing in the abstract instead of weighted for this context.

## Compliance

| Enforced by | Where |
|---|---|
| FF-005, and the quality floor recorded in `ai-evals.md` | [`../../04-technical-spec/fitness-functions.md`](../../04-technical-spec/fitness-functions.md) |

FF-005 guards that every delivered ranking is recorded. The quality floor — the assets that
actually failed appearing in the top decile — is what judges whether the rule is any good, and
it is deliberately the same measure a trained model would be judged by. That is what makes the
swap comparable rather than a leap of faith.

## Revisit when

SGW supplies validated per-asset failure history (assumption A7), **or** the deterministic rule
misses the quality floor on a replayed storm. Either makes the model worth its cost; neither has
happened, and until one does, training would be ceremony.

## Impact

| Dimension | Impact |
|---|---|
| Security | Neutral. No model artifact to poison, no external inference call, no training pipeline to secure. |
| Reliability | Positive. A pure function has no cold start, no artifact to fail to load, and no drift. |
| Performance | Positive. Scoring is arithmetic over a loaded scenario, comfortably inside REQ-NF-001. |
| Cost | Zero, which CON-006 requires. A trained model would add nothing at inference either, but a training and evaluation cycle is real cost. |
| Maintainability | Mixed. The rule is trivial to read and change — and that is also its risk: it is easy to adjust a weight until the ranking looks agreeable, which is why Q-025 asks who signs off that it is sane. |

## Related

- Related requirements: REQ-F-002, REQ-F-003, BR-002, BR-003
- Related technical spec sections: §2 Architecture Overview, `ai-boundary-spec.md` §1–§4
- Open question this raises: Q-025 (which factors and weights, and who validates the ranking)
- Supersedes / superseded by: —

---

> Blueprint: blueprints/01-docs/05-architecture/architecture-decisions/ADR-000-template.md
