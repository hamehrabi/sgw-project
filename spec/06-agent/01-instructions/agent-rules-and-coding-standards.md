# Agent Rules and Coding Standards

> Source: Ch. 30 §30.5 + Ch. 12 §12.4.
> AI agents need rules because they are **powerful pattern generators, not responsible
> engineers**. Your standards tell the agent how code should be structured, what it must
> not change, how errors should be handled, how tests should be written, and what must be
> explained before review.

**Version:** AGENT v1.0

---

## Standards summary (Ch. 30 §30.5)

| Standard area | Rule example | Why it matters | Review evidence |
|---|---|---|---|
| Scope control | Do not modify files outside the task scope unless asked first. | Prevents hidden unrelated changes. | File-change summary. |
| Code style | Use clear names, small functions, predictable module boundaries. | Keeps generated code maintainable. | Reviewer readability check. |
| Error handling | Return safe user messages; log technical details internally. | Protects users and helps diagnosis. | Error-path tests. |
| Security | Never hardcode secrets or bypass authorization checks. | Prevents serious production risk. | Security review checklist. |
| Testing | Every behavior change must include relevant tests. | Makes output provable. | Passing test list and coverage notes. |
| Explanation | Summarize assumptions, trade-offs, and files changed. | Makes review faster and safer. | Agent completion note. |

---

## Reusable agent rules template (Ch. 30 §30.5)

```
General behavior:
- Follow the linked requirement and technical specification.
- Ask questions before filling major gaps.
- Do not expand scope without approval.

Coding standards:
- Keep functions small and readable.
- Use clear names and simple control flow.
- Add comments only where they explain non-obvious decisions.

Security rules:
- Do not hardcode secrets.
- Do not weaken authentication or authorization.
- Validate all external input.

Testing rules:
- Add or update tests for every behavior change.
- Include success paths, failure paths, and edge cases.

Completion note:
- List files changed.
- List assumptions.
- List tests added or updated.
- List remaining risks or questions.
```

---

## Coding standards for this project (Ch. 12 §12.4)

| Standard area | Rule |
|---|---|
| Naming | Clear names that say what the thing is: `computeRiskScore`, `matchAssetsAcrossSources`, `applyForecastRevision`. No abbreviations except `id`. |
| Functions | One job per function. If it scores **and** persists, split it — the split is what FF-002 checks. |
| Validation | At the boundary, before any write. The seven defect rules run at **load** time, never at read time. |
| Errors | Safe user-facing messages that name a next action. A failure must never render as an empty screen that reads as safety. |
| Tests | Every behaviour change ships with a test named for its test id, so a CI failure names the requirement rather than a line number. |
| Structure | `views/` → `api/` → `scoring/` \| `loader/` → `store/`. A view never imports `scoring/`. A handler never contains a scoring or matching rule. |
| Logging | Every line carries a request id. Never a password, hash, session value, full asset location, household-level damage location, or file contents. |
| Comments | Explain *why*, never *what*. A comment naming the ADR or requirement a piece of code exists for is worth ten describing what the line does. |
| Constraints | If the store can refuse it, the store refuses it. A rule implemented in the service layer instead is a rule the first refactor removes with every test still green. |
| Reasons | The reasons for a risk score are produced by the computation that produces the score. Never assembled afterwards from the inputs. |

*Replace/extend with your project's real conventions. Keep it short — the goal is to
prevent avoidable inconsistency, not to write a style manual.*

**The last two rows are the ones that carry this product.** Everything above them is ordinary
good practice; those two are where a plausible implementation silently stops being correct.

---

## Layer responsibilities (Ch. 20 §20.3)

| Layer | Main responsibility | Must not do |
|---|---|---|
| Endpoint / controller | Receive input, call the service layer, return the response. | Contain deep business rules. |
| Validation layer | Reject invalid input before business logic runs. | Perform persistence. |
| Service layer | Apply business rules and coordinate the use case. | Format HTTP responses. |
| Data access layer | Read and write data through a clear boundary. | Decide user-facing business behavior. |
| Error handling layer | Turn expected failures into safe, clear responses. | Leak stack traces to users. |

### The same table, against ADR-001's five modules

| Module | Main responsibility | Must not do |
|---|---|---|
| `views/` | Render, handle the five states, offer actions. | Import `scoring/` (FF-002). Compute anything. |
| `api/` | Identity, role check, request validation, response shape. | Contain a scoring or matching rule. |
| `scoring/` | The score, the rank, and the reasons — one computation. | Read a request. Know a screen exists. Write outside its own results. |
| `loader/` | Parse, apply the seven defect rules, match assets. | Score. Resolve an unmatched record by guessing. |
| `store/` | Persistence, and the constraints enforcing BR-002, BR-003, BR-004. | Decide user-facing behaviour. |

---

## Rule versioning

Update this file when a **repeated AI mistake** or a **new coding boundary** appears
(Ch. 30 §30.3). Every update needs a reason and an example.

| Version | Date | Change | Reason | Example that triggered it |
|---|---|---|---|---|
| AGENT v1.0 | 2026-08-15 | Initial rules, written from ADR-001 to ADR-005 before any code exists. | Project start. | — |

**No version has been earned yet.** Every row after the first costs a real bug, and the value of
this table is that each row names the bug rather than the rule alone — a rule with no example
reads as a preference and gets negotiated away.

---

## The completion note the agent must produce

Every task ends with this, in this shape:

```
Files changed:
  - <path>    (why this file)
Assumptions:
  - <anything the specification did not state, FLAGGED>
Tests added or updated:
  - <test ids, and which should now pass>
Remaining risks or questions:
  - <what a human needs to decide>
Files changed outside the task plan:
  - <list, or "none">
```

**The last line is the most useful one in the report.** It makes silent scope expansion
self-declared rather than discovered three tasks later, and it is the only line whose value
comes from usually saying *none*.

---

> Blueprint: blueprints/06-agent/01-instructions/agent-rules-and-coding-standards.md
