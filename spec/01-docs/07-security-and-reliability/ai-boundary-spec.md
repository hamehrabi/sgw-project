# ai-boundary-spec.md — The AI Boundary

> **Purpose:** make the model replaceable, its behaviour measurable, its output governable,
> and responsibility explicit.
> **When you use it:** any feature that calls a model. Skip this file if you have none.
> **Sources:** Richards & Ford Ch. 26 (AI position) · Hohpe Ch. 9 (options) ·
> Ousterhout Ch. 8 (configuration knobs).

> **Model capability, pricing, and vendor viability are more volatile than almost anything
> else in your system.** Option value rises with volatility — so a replaceable model
> boundary is worth more here than the same abstraction would be anywhere else.

**This file was filled, not skipped.** The kit permits skipping it when the product neither
calls nor is driven by a model, and it was tempting here: two of the source PRD's three AI
abilities — the water early-warning and the summary writer — are deferred. But the third one,
the per-asset risk forecast, **is** the ranked risk list, and that is the core subdomain of
version one.

**Version one contains no model** (ADR-005, CHG-005): the score comes from a deterministic
weighted rule. This file still applies in full, and that is the point of it — the boundary is
what makes the rule replaceable by a trained model at a cost of one module, and the guardrails
in §4 are needed by a rule exactly as much as by a model. A confidently wrong rule produces
confidently wrong reasons, which is more persuasive than a wrong model, not less.

---

## 1. The one budget that structures the system

Pick **one**. Let it shape the architecture; keep everything else simple.

| Constraint | Target | Why this one |
|---|---|---|
| **Quality floor** | The assets that actually failed in a prepared storm appear in the top decile of that storm's ranking | Cost is zero — no provider is called, so there is no per-request price to structure around. Latency is already bounded by REQ-NF-001 and is not what makes this product succeed or fail. The whole value rests on the ranking being *right*, and the source PRD prices the two mistakes at roughly a thousand to one: a missed failure against a wasted trip. A quality floor is the only one of the three that can fail silently. |

**The ratio is the reason the floor is stated as recall rather than accuracy.** Failures are
rare, so a scorer that ranks everything safe would be right almost always and would miss every
failure. Accuracy would report that as excellent.

## 2. Model boundary

| Item | Decision |
|---|---|
| Provider(s) | **One: a hosted OpenAI model** (ADR-009), used to phrase reasons the scorer already computed. It never scores, ranks, or bands. **Scoring itself remains fully in-process and deterministic.** |
| Abstraction | The **scoring module** (ADR-001). It is the only module that produces a score, a rank, or a reason, and no view imports it (FF-002). |
| What is exposed | The score, the rank, the confidence, and **the reasons**. Reasons are exposed deliberately and permanently — they are not diagnostics, they are the product (BR-002). |
| What is hidden | How the score is computed. Callers must not be able to tell a rule-based score from a trained one — that is what lets ADR-005's successor arrive without the API contract moving. |
| Swap cost | **One module.** Replacing the deterministic scorer with a trained model, or one model family with another, must change nothing outside it — not the API contract, not the store, not a view. If it takes more than one module, the boundary is in the wrong place. |
| Pinned version | **`OPENAI_MODEL` is pinned, never "latest"** — a silent model change is a silent behaviour change, and `ai-evals.md` re-runs on any change to it. The scoring rule is separately versioned and recorded on every ranking, because a ranking that cannot say what scored it cannot be audited. |

> **The trap is false abstraction.** Hiding token counts or streaming semantics behind a
> uniform façade when callers demonstrably need them produces obscurity, not abstraction.
> If people read your adapter source to find out what really happens, expose it.

The false abstraction to avoid here is the opposite of the usual one: hiding the **reasons**.
Reasons look like an implementation detail of the scorer and are the one thing the caller
genuinely needs, which is why BR-002 puts them in the contract rather than behind it.

## 3. Derived, not configured

For each knob ask: **can the caller determine a better value than I can here?** If no,
compute it.

| Knob | Configured or derived? | Why |
|---|---|---|
| Temperature | **Not applicable** | No language model is called at any point in version one. |
| Retrieval count (k) | **Not applicable** | Nothing is retrieved; the scorer reads the whole loaded scenario. |
| Similarity threshold | **Not applicable** | No embedding or similarity search exists. |
| Max tokens | **Not applicable** | No tokens. |
| Reasons shown per rank | **Derived** | Every contributing factor is shown, labelled by its share of the score: **>= 25% Strong, 10-25% Moderate, < 10% Slight** (ADR-007). A fixed *top 3* would silently truncate the fourth reason in exactly the unusual storm where it mattered. |
| Rank tie-break | **Derived** | When scores are equal, order by the asset with the older condition observation first — the one the system knows least about. Nobody calling the endpoint can choose this better than the scorer can. |
| The score-to-action threshold | **Neither — it does not exist** | The product ranks; it never decides what is "high enough to act on". That is the operator's judgement, and a threshold here would be BR-001 violated by a configuration value. |

**The last row is the most important one in this table.** A threshold that turned a rank into a
recommendation-to-act would move a decision from a person into a config file, which is exactly
the boundary the whole product is built around.

## 4. Guardrails

| Layer | Rule | On violation |
|---|---|---|
| Input | Only records that passed the seven defect rules reach the scorer. An asset the loader could not match is never presented to it as a merged record. | Flagged `needs_review`, excluded from merging, shown to a person. Never merged on a guess. |
| Output | A score is never stored without at least one reason; the database refuses it (BR-002, `database-design.md` §3). | The write fails and the asset is reported as a scoring failure — visibly — rather than dropped. |
| Refusal | *Never mask a content refusal — callers must be able to build on it.* Here the analogue is a **scoring failure**: an asset the scorer cannot score. | **Surfaced as UNSCORED with its reason, always.** Never omitted from the list and never defaulted to a low score. This is the single most important guardrail in the product: an asset silently missing from a ranking reads as an asset that is safe. |
| PII | No personal data enters the scorer — it reads assets, weather and history, not people. Asset locations do enter it, and never leave the process. | A scorer input containing a personal field is a defect in the loader, not a scoring concern. |

## 5. Failure behaviour

Apply all four error techniques (Ousterhout Ch. 10):

| Failure | Technique | Behaviour |
|---|---|---|
| Malformed JSON output | **Define away** | Schema-coercing parser clamps/coerces/fills defaults |
| Rate limit, timeout | **Mask low** | Retry with backoff inside the transport layer |
| Any request-level error | **Aggregate high** | One handler at the request boundary |
| Missing API key, bad model name | **Just crash** | Fail at **startup** with a clear message |
| Content refusal, persistent outage | **Never mask** | Surface it — callers need it |

**As they apply here**, given there is no provider and no transport:

| Failure | Technique | Behaviour |
|---|---|---|
| A scorer output missing its reasons | **Define away** | The store refuses it. There is no shape of a stored score without a reason, so the defect cannot reach a screen. |
| A single asset's inputs are unusable | **Aggregate high** | One handler marks that asset unscored with a reason; the rest of the ranking completes. One bad asset never fails a whole storm. |
| The scoring module is missing, or its artifact does not load | **Just crash** | Fail at **startup**, not on the first request during a storm. A product whose core subdomain is absent must not appear to be working. |
| An asset cannot be scored | **Never mask** | Rendered as UNSCORED, in the list, with its reason. See §4. |
| Rate limit / timeout / API key | — | Do not exist. No provider is called, so the three most common AI failure modes are absent by construction, which is worth stating rather than leaving as four empty rows. |

## 6. Human in the loop

| Question | Answer |
|---|---|
| Where does the human sit? | **Approve before.** Every recommendation is accepted, changed, or rejected by a person before it becomes a decision (BR-001, REQ-F-006). No output of the scorer reaches the world through the software. |
| What happens when the model is wrong? | **Compensate**, and the compensation happens outside the software — a crew is re-dispatched, at real cost. It is not a write-off: a wrong ranking that a person acted on has already moved people. That asymmetry is the whole reason BR-001 exists, and the reason the reasons are on the screen. |
| What can the model do without approval? | Produce a ranking and display it, with its reasons. Nothing else. It cannot move a crew, assign a job, change a record, or send anything anywhere — there is no path by which it could. |
| What is logged for review? | Every ranking delivered (FF-005), every accept, change and reject, and whether the reasons were opened before the decision was taken — which is success metric 3, the measure of whether people are still thinking. |

## 7. Observability

| Signal | Captured |
|---|---|
| Prompt version, model, params | No prompt and no model in version one (ADR-005) — but **every ranking records the scoring-rule version and the factor weights in force when it was produced**. Without that, a ranking cannot be reproduced after someone adjusts a weight, and Q-025 makes adjusting weights the expected activity. |
| Tokens in/out, cost, latency | Tokens and cost do not exist. Latency is captured against REQ-NF-001's re-rank limit. |
| Refusals, guardrail trips, fallbacks | Every UNSCORED asset, with its reason, counted per storm. A rise in unscored assets is the earliest signal that the input data has changed shape. |
| **Never logged** | Prompt content with PII, API keys, raw user documents |

To that last row, three more from Round 6: full asset locations and connections, household-level
damage locations, and the contents of an uploaded file.

## 8. Prompts as artifacts

Prompts are code. One authoritative version, not four near-duplicates in three services.
Each prompt file states: **intent, the failure it was written to fix, its version, and
its eval set.** → [`../../03-tests/03-non-functional/ai-evals.md`](../../03-tests/03-non-functional/ai-evals.md)

**There are no prompts in version one**, because no language model is called. The rule is
recorded because the summary writer — the source PRD's ability 3 — is deferred rather than
rejected, and it arrives with prompts attached. `ai-evals.md` is written in Round 7 and covers
the ranking's quality floor from §1, which needs an eval set whether or not the scorer is
trained.

## 9. Tool schemas (agents only)

> A tool schema is the purest **deep module** problem you will face: the interface is
> consumed by a model that cannot read your source. Everything informal — call ordering,
> what null means, idempotency, units — **must be in the description or it does not exist.**

- [ ] Six deep tools, not forty shallow ones
- [ ] Each hides meaningful work (not a one-line forward)
- [ ] Description states units, ordering, idempotency, and null meaning
- [ ] Destructive tools require confirmation

**Not applicable — this is not an agent.** Nothing in version one calls a model that in turn
calls back into the system, so there are no tools to describe. The checklist is unticked for
that reason rather than for being unmet. *Revisit when:* any capability lets a model take an
action rather than produce a ranking — which BR-001 currently forbids outright, so reaching
this section would require superseding it.

---

> Blueprint source: this file is new to the template — added from the architecture review.

---

> Blueprint: blueprints/01-docs/07-security-and-reliability/ai-boundary-spec.md
