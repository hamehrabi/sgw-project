# risk-storming.md — Make Uncertainty Visible

> **Purpose:** find the risks *before* they become incidents.
> **When you use it:** before build, before a major feature, before release.
> **Source:** Richards & Ford, *Fundamentals of Software Architecture*, Ch. 22.

> Copy this file to `risk-storming-<date>.md` and fill it in, once per session. **The scoring
> cells stay blank in this copy** — a risk nobody has scored yet has no numbers, and writing
> plausible ones is worse than leaving them empty.

> **Risk = impact × likelihood**, each scored 1–3.
> `1–2` low · `3–4` medium · `6–9` high. **Unproven technology starts at 9.**
> Assess impact first. If likelihood is unknown, keep it high until proven otherwise.

---

## The three steps — the order is the point

| Step | How | Why this order |
|---|---|---|
| **1. Identify alone** | Each person marks impact and likelihood **independently**, on the current diagram. No discussion. | Prevents group influence and reveals who knows what. This is the step people skip, and skipping it defeats the exercise. |
| **2. Reach consensus** | Explain disagreements. Single-observer risks matter most — one person saw something nobody else did. Revise to a shared rating. | Disagreement *is* the signal. |
| **3. Mitigate together** | Redesign, or let an empowered stakeholder compare mitigation cost against accepting the risk. | Accepting a risk knowingly is a valid outcome. Accepting it unknowingly is not. |

**Step 1 has a problem on this project worth naming before the first session:** there is
currently one participant, and Q-026 records that no decision owner has a name. Individual
scoring with one person is not risk storming — it is a list. **Do not run this until at least
two people can score independently**, and prefer three: the operations manager who knows what a
storm actually looks like, the tech lead, and whoever owns the budget.

## The grid

Rows are your **driving characteristics**. Columns are meaningful areas of the system.
Service-level scope is usually too narrow to be useful.

| | Loader + prepared data | Scoring + reasons | The four screens | Store + decision record | Total |
|---|---|---|---|---|---|
| *Simplicity / feasibility* | | | | | |
| *Reliability / graceful failure* | | | | | |
| *Auditability* | | | | | |

The rows are this project's three driving characteristics, and the columns are the four areas
that can fail independently. Every cell is blank because no session has happened.

## The register

| ID | Risk | Impact | Likelihood | Score | Trend | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|---|
| RISK-001 | | 1–3 | 1–3 | | ↑ ↓ → | | | Open |

> Track the **trend**, not just the snapshot. A medium risk getting worse deserves more
> attention than a high one already being mitigated.

## Rules

- Run it **individually first**. Always.
- Repeat across the lifecycle — a risk assessment is not a one-time gate.
- A risk with no owner is not managed.
- Unknown technology scores **9** until you have evidence.

---

## The candidate risks, unscored

These come from decisions already recorded, and are listed so the first session starts from
evidence rather than a blank page. **They are deliberately unscored** — scoring them here would
skip step 1, which is the step that does the work.

| Candidate risk | Where it comes from | What already mitigates it, if anything |
|---|---|---|
| A combined ranked view does not change the crew decision | Assumption A2 — the guess the whole product rests on | Nothing mitigates it. Version one exists to find out, which is the correct response to a risk you cannot design away. |
| Operators do not act on a computer's ranking | Assumption A3 | Reasons beside every rank (BR-002), and success metric 3 counts whether they are read |
| An unscorable asset renders as a safe asset | `ai-boundary-spec.md` §4 names this the most dangerous failure in the product | FTEST-004; the UNSCORED rule; a standing block condition in the review log |
| Four capabilities do not fit one week | CON-002 against Q-008 | Priorities in `product-spec.md` §11 name what drops first |
| The scoring rule is tuned until the ranking looks agreeable | ADR-005's stated trade-off, and Q-025 | `ai-evals.md` re-runs the full set on any weight change. **Nothing else** — this is the weakest link in the workspace |
| An uploaded file is malicious | The only untrusted-input surface | Admin-only, allow-list by content inspection, never executed, never served back. **No scanner** (CON-006), accepted with a revisit trigger |
| Single-writer contention under ADR-002 | The trade-off ADR-002 wrote down | FTEST-009. Invisible at 50 users; the first assumption to stop being true |
| A migration drops an append-only trigger | ADR-004's named residual weakness | FF-004 fails the build; the migration checklist treats it as needing a superseding ADR |
| The prepared data does not resemble SGW's real data | The probe proves nothing if the fixture is wrong | The seven measured defects are injected on purpose; FF-006 |
| One person holds the whole project | Q-026 — no named owners at all | Nothing. The specification itself is the only mitigation, which is what it was for |

**Two of these have no mitigation and that is the finding.** A2 cannot be mitigated — it can
only be tested, which is what version one is. The scoring-weights risk *can* be mitigated and
currently is not, beyond a re-run rule: nobody is named to say whether a ranking is sane
(Q-025), and a rule tuned to look right is indistinguishable on screen from one that is right.

---

> Blueprint source: this file is new to the template — added from the architecture review.

---

> Blueprint: blueprints/05-review/02-checklists/risk-storming.md
