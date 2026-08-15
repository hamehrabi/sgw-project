# Debugging Specification

> Source: Ch. 19 §19.7.
> A short record of how a bug was diagnosed, what evidence proved the cause, what changed,
> and how you will prevent the same problem from returning. Not a long report — a clear
> trace from symptom to fix.

---

## Bug log

| Bug ID | Date | Feature | Requirement | Symptom | Root cause | Regression test | Spec updated? | Status |
|---|---|---|---|---|---|---|---|---|

**Empty — no code exists, so no bug does.** `BUG-001` is minted the first time something behaves
other than as specified.

---

## Entry template (Ch. 19 §19.7)

```
Bug ID:              BUG-001
Related Requirement: REQ-###
Feature:             [feature name]

Symptom:             [what failed]
Expected Behavior:   [what should have happened]
Actual Behavior:     [what happened instead]

Evidence:            [logs, stack trace, failing test, reproduction steps]
Root Cause:          [the real cause, not just the error message]

Smallest Safe Fix:   [what changed]
Regression Test:     [test name or test case]
Spec Update Needed:  [requirement, technical spec, API contract, or agent instruction]
Prevention Note:     [what you will not repeat]
```

---

## Common AI coding mistake patterns (Ch. 19 §19.2)

Naming the pattern makes debugging faster. The goal is not to blame the agent — it is to
find where the instruction, context, code, or test coverage was incomplete.

| Pattern | First evidence to check |
|---|---|
| Happy path only | Failure-path test coverage |
| Broken assumption (null / missing field) | Stack trace + input payload |
| Wrong data shape | API contract vs. actual response |
| Misunderstood business rule | Requirement wording vs. implementation |
| Skipped validation | Validation layer + boundary tests |
| Silent scope change | Diff against the task's allowed files |
| Weak error handling | Error-path logs and user messages |

### An eighth pattern this product must watch for

| Pattern | What it looks like | First evidence to check |
|---|---|---|
| **Absence rendered as reassurance** | Nothing is broken. No error fires. A screen shows an empty list, a clear board, or a ranking with an asset missing — and a person reads it as *no risk*, *all clear*, *that one is fine*. | The data behind the screen, not the screen. Did the ranking compute? Did the load succeed? Is the asset present and UNSCORED, or absent? |

**This pattern will not arrive as a bug report.** It arrives as a decision somebody made
confidently and wrongly, weeks later, with no error anywhere in the logs. FTEST-002, FTEST-003
and FTEST-004 exist for it, and if one of them is ever weakened into "no exception was raised",
this row is the reason to put it back.

---

## Prevention ledger

| Bug ID | Pattern | Guardrail added | Where |
|---|---|---|---|

**A fix is complete only when the code, the tests, and the specification agree.** On this project
that has a specific consequence: a bug that reveals a missing rule does not get fixed in code
alone. It produces a regression test *and* a row in
`01-docs/09-change-control/spec-change-log.md` *and*, where the mistake is repeatable, a line in
`AGENT.md`'s **Lessons from past mistakes**. The third of those is the one people skip, and it
is the only one that prevents the same bug in a different feature.

---

## The three failures predicted before any code exists

`AGENT.md` names these. They are repeated here because this is the file somebody opens when
something has already gone wrong, and recognising a predicted failure is faster than diagnosing
a novel one.

| Predicted failure | Pattern | Where it will show |
|---|---|---|
| An unscorable asset dropped from the ranking | Absence rendered as reassurance | FTEST-004, and nowhere else — no error, no failing feature test |
| A permission's allow path built, deny path absent | Happy path only | The deny test for that row of the role matrix in `security-tests.md` |
| A store constraint implemented in a service instead | Misunderstood business rule | UTEST-009, which asserts the **store** refuses — not the caller |

If the first three bugs on this project are these three, the prediction was useful. If they are
not, the new pattern is worth adding to the table above, because it is one this specification
did not anticipate.

---

> Blueprint: blueprints/05-review/04-debugging/debugging-specification.md
