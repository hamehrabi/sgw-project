# ADR-009: A hosted language model phrases computed reasons, and may invent nothing

**ADR ID:** ADR-009
**Status:** Accepted
**Date:** 2026-08-15
**Decision owner:** The developer (sole owner for the prototype — Q-026)
**Review date:** Before any use outside a scenario test, and at the first prompt change

---

## Context

ADR-005 and ADR-007 make the ranking deterministic: four weighted factors, a score, and reason
strength derived from each factor's share of that score. BR-002 enforces it in the store — a
score cannot be written without at least one reason.

The reasons that arithmetic produces are correct and terse. *"Gust ratio 0.82; flood zone VE;
age 41/50"* is defensible and hard to read at 3am. The proposal is to render them in plain
English with a hosted language model.

**This reverses two constraints the workspace has held since Round 2**, and they are quoted here
because a decision that overturns a constraint should carry the constraint's own words:

> **CON-006:** "No paid third-party services in version one."
> **Round 6, Q2 — external services:** "**None in version one.**"

Round 6 also declined off-site error tracking on the grounds that "it would send stack traces
containing critical-infrastructure context outside SGW." That reasoning is not withdrawn; it is
now outweighed for this one path, and the same data-egress question it raised is answered
differently here.

## Options considered

1. **The model generates the reasoning** — it looks at an asset and explains why it is at risk.
   Rejected, and this ADR exists partly to record why. ADR-005 states it: *a reason decoupled
   from the score is a plausible sentence that explains nothing, and it is indistinguishable on
   screen from one that does.* It would also make BR-002 meaningless — the store would be
   enforcing the presence of text nobody could tie to the rank.
2. **The model phrases reasons the scorer computed**, receiving only the factors and their
   contributions, permitted to change wording and nothing else. Costs an external dependency, an
   invoice, data egress, and an eval that can actually catch invention.
3. **A local or self-hosted model** — no egress, no invoice, CON-006 intact. Rejected on
   capability and on the RAM budget of a single small VM, and because a weaker model phrasing
   safety-relevant text is a worse trade than it first appears.
4. **Templated strings** — no model at all. `"{factor} is {strength}: {value}"`. Free, offline,
   and it is what the fallback path below actually does.

*Compared on:* which interface is simpler · which is more general · which forces callers
to do work that should be inside · which is cheaper to reverse.

## Decision

**A hosted OpenAI model phrases reasons that the scoring module has already computed.** It is a
presentation layer over deterministic facts, subject to four rules:

1. **The computed reasons remain the record of truth.** The scorer's factor list and
   contributions are what BR-002's constraint checks, what the decision record stores, and what
   `ai-evals.md` scores. The model's output is a rendering of them.
2. **The model receives only factors and contributions** — never a free-text asset name, never
   coordinates, never a customer-adjacent field. See *Impact* for what this does and does not
   protect.
3. **Every output is checked against its input before display.** A phrase naming a factor that
   was not in the input, or asserting a strength the arithmetic did not produce, is **discarded**
   and the computed reason is shown instead. This check is deterministic and cheap.
4. **The model is optional at runtime.** If OpenAI is slow, down, rate-limited, or over budget,
   the ranking renders its computed reasons in the templated form and **the product keeps
   working**. Nothing on the critical path waits for it.

## Reason

Rule 4 is the one that makes the rest acceptable. This platform is used during the event it
describes; REQ-NF-003 already says it must survive its own data failing. An external dependency
that could take the ranking down mid-storm would contradict that outright — so the dependency is
placed where its absence degrades prose rather than function.

Rule 3 is what makes "phrase only" a property rather than an intention. An instruction in a
prompt is a hope; a comparison against the computed factor set is a check. It is also the only
form in which the distinction survives a model upgrade.

Rules 1 and 2 keep the two things that make the ranking defensible: the audit trail records
arithmetic, and the prompt does not carry a map of the grid.

## Consequences

- **Positive:** Reasons become readable without becoming inventions. The ranking's correctness is
  unchanged and still provable. The model can be swapped, downgraded, or removed entirely without
  touching the scorer, the store, or the decision record.
- **Trade-off or limitation:** Four real costs, and none is small.
  **(a)** CON-006 is broken — there is now a metered invoice, and `runtime-and-scale.md` §1's own
  revisit trigger has fired: *"any endpoint calls a metered service — on that day an unlimited
  endpoint is an unlimited invoice."* A per-ranking cap is now mandatory, not advisory.
  **(b)** Data leaves SGW. Factor names and numbers are far less sensitive than coordinates, but
  the property *nothing about this grid goes off-site* is gone, and Round 6 declined a lesser
  egress for the same reason.
  **(c)** **Untrusted input reaches a prompt.** Asset names and free-text `notes` arrive in
  uploaded CSVs, which are attacker-controlled in any realistic threat model. Rule 2 keeps them
  out of the prompt; if that rule is ever relaxed for better prose, prompt injection arrives with
  it.
  **(d)** A phrasing layer is exactly where a "small improvement" turns into generation. The next
  person will want to let the model see the asset. Rule 3 is the thing that will be argued with.
- **Rule the AI assistant must follow during implementation:** The model never influences a
  score, a rank, or a band. Only factor names and numeric contributions go into a prompt —
  never an asset name, identifier, coordinate, condition note, or any CON-003 field. Every
  response is validated against the input factor set before it is shown, and a failed validation
  falls back to the computed text silently. The ranking must render correctly with the provider
  unreachable, and a test must prove it.

> **If no trade-off is visible, keep looking.** A choice with no downside was never a
> choice — you are comparing in the abstract instead of weighted for this context.

## Compliance

| Enforced by | Where |
|---|---|
| FF-007 (new) — no model output is displayed that names a factor absent from its input | [`../../04-technical-spec/fitness-functions.md`](../../04-technical-spec/fitness-functions.md) |
| `ai-evals.md` — `no_invented_factors`, `no_asset_identifiers_in_prompt`, `renders_without_provider` | [`../../03-tests/03-non-functional/ai-evals.md`](../../03-tests/03-non-functional/ai-evals.md) |

## Revisit when

The invention rate measured by `no_invented_factors` is non-zero on any run; **or** the cost per
ranking exceeds the ceiling; **or** anyone proposes letting the model see the asset itself, which
is the same decision again with the guardrail removed.

## Impact

| Dimension | Impact |
|---|---|
| Security | **Negative, and knowingly.** Data egress to a third party, an API key to hold and rotate, and a prompt that must be kept free of untrusted text. The one-way wall toward the grid is untouched — no command path is created — but *no data leaves* is no longer true. |
| Reliability | Neutral by construction. The provider is off the critical path; its failure costs prose. Without rule 4 this would be the worst reliability decision in the workspace. |
| Performance | Neutral for the ranking; the phrasing call is asynchronous and its absence is not blocking. |
| Cost | **Now non-zero**, which reverses Q-019's answer of zero recurring spend. A per-ranking cap and an alert are required before the first real use. |
| Maintainability | Mixed. One more system, one more failure mode, one more thing to evaluate — against reasons an operator will actually read. |

## Related

- Related requirements: REQ-F-003, BR-002, REQ-NF-003, REQ-NF-007
- Reverses: CON-006 (no paid services), Round 6 Q2 (no external services), Q-019 (zero recurring cost)
- Extends without contradicting: ADR-005, ADR-007 — the score and the reasons remain computed
- Supersedes / superseded by: —

---

> Blueprint: blueprints/01-docs/05-architecture/architecture-decisions/ADR-000-template.md
