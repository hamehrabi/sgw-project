# Scope Change Log

> Source: Ch. 14 §14.7 (Preventing Scope Creep) + Ch. 29 §29.6 (Handling Scope Changes).
> Scope changes are not automatically bad. They become dangerous when they enter the
> project **without a decision trail**.

> **Scope control rule:** a scope change is not accepted until the relevant requirement,
> design, tests, tasks, and review checklist are updated. Otherwise the change is only a
> conversation, not a controlled decision.

---

## Change requests

```
Change ID:
Date:
Requested by:
Requested change:
Reason / evidence:

Evaluation:
  Does it support the project goal?         [yes/no + why]
  Does it affect existing requirements?     [which REQ IDs]
  Does it affect architecture?              [ADR needed?]
  Does it affect release timing?            [impact]
  Does it require new tests?                [which TEST IDs]

Decision:      Accept / Reject / Defer
Decision owner:
Date decided:

Artifacts updated:
  [ ] 01-docs/constraints-and-non-goals.md
  [ ] 01-docs/requirements.md
  [ ] 01-docs/product-spec.md
  [ ] 01-docs/technical-spec.md
  [ ] 01-docs/architecture-decisions/ADR-###
  [ ] 01-docs/traceability.md
  [ ] 02-tasks/task-index.md
  [ ] 03-tests/test-specification.md
  [ ] 05-review/code-review-checklist.md
  [ ] 07-ops/deployment-plan.md
```

| Change ID | Date | Requested change | Decision | Owner | Artifacts updated |
|---|---|---|---|---|---|

**No scope change has been requested yet**, because no code exists. This table is the one that
matters most once it does: the four capabilities in
[`product-spec.md`](../../01-docs/03-product-spec/product-spec.md) §7 are the whole of version
one, and anything a fifth idea needs must arrive through here rather than through a task.

Specification changes made **during the interview** are recorded elsewhere and deliberately not
duplicated here: `01-docs/09-change-control/spec-change-log.md` holds CHG-001 to CHG-005. This
file is for scope changes to an agreed build, which is a different thing from a decision that
was still being made.

---

## Evaluation questions (Ch. 29 §29.6)

| Question | Why it matters | Decision option | Artifact to update | Risk if ignored |
|---|---|---|---|---|
| Does it support the project goal? | Prevents attractive but distracting work. | Accept / reject / defer. | Project vision and PRD. | The team builds low-value features. |
| Does it affect existing requirements? | Prevents hidden behavior changes. | Revise requirement or create new one. | Requirements and traceability matrix. | Tests no longer match expected behavior. |
| Does it affect architecture? | Prevents rushed design damage. | Update design or create an ADR. | Technical spec and ADR log. | The code becomes inconsistent. |
| Does it affect release timing? | Prevents false delivery promises. | Move release, reduce scope, or defer. | Roadmap and task plan. | The team ships unfinished work. |
| Does it require new tests? | Prevents unverified changes. | Add test cases before implementation. | Test spec and checklist. | New behavior breaks silently. |

**One extra question belongs on this project, ahead of the five above:** *does it test one of
the three guesses that could end the project?* The source PRD's whole argument is that version
one exists to test A1, A2 and A3 as cheaply as possible. An addition that improves the product
without testing one of those is, by that argument, something to defer — however good it is.

---

## Preventing scope creep from the agent (Ch. 14 §14.7)

Scope creep happens quickly with AI agents because they may "helpfully" add extra fields,
extra screens, or extra logic that was never requested.

**Rule:** every task must point back to an approved requirement or design decision. If a
requested change has no matching spec entry, **pause the implementation** — reject it,
defer it, or update the spec first.

> **No new code without a matching approved reason.**

New ideas must pass *through the specification* before they become implementation tasks:

```
new idea → evaluate against intent & goals → accept/defer/reject
                  ↓ (accepted)
        update requirement + spec + tests
                  ↓
             create task
                  ↓
           implementation
```

**Four additions are predictable on this project, and each would look like helpfulness:**

| Likely "helpful" addition | Why it must come through here |
|---|---|
| A threshold that marks assets "high risk" and prompts action | It turns a rank into an instruction, which is BR-001 violated by a config value. `ai-boundary-spec.md` §3 rejects it explicitly. |
| An edit or delete on a decision record, "for corrections" | BR-004. The database refuses it, so the attempt would surface as a bug report rather than a feature — and the fix would be to remove the trigger. |
| Auto-assigning crews to the top-ranked jobs | BR-001. The system moves nobody, at any version. |
| Sending an email — a reset link, an alert, a digest | Round 6 removed every external service. One email dependency reverses that decision quietly. |

---

> Blueprint: blueprints/02-tasks/03-control/scope-change-log.md
