# Debugging Checklist for AI-Generated Code

> Source: Appendix O + Ch. 19.
> Debugging AI-generated software requires **evidence**. Do not ask the agent to guess.

> **Beginner rule (Ch. 19 §19.1):** never debug from memory alone. Write down the failure,
> the expected behavior, the actual behavior, and the evidence before you change code.

---

## The workflow (Ch. 19)

```
Reproduce → collect evidence → identify cause → fix ONE cause → test → update the spec
```

| Step | Action | Output |
|---|---|---|
| 1 | Reproduce the failure | A clear failure description |
| 2 | Collect logs, traces, and failing tests | Evidence |
| 3 | Compare evidence to the requirement | Gap or contradiction |
| 4 | Ask AI for root-cause analysis **only** | Diagnosis |
| 5 | Patch one cause at a time | Controlled fix |
| 6 | Run old and new tests | Proof |
| 7 | Update spec and prevention note | Future guardrail |

**Step 1 is harder here than the workflow implies**, and it is worth planning for. The most
dangerous failure in this product produces no error, no exception and no failing test — an asset
missing from a ranking, a blank board, a stale screen that does not say it is stale. There is
nothing to reproduce until somebody notices the *absence*. When a report arrives that sounds
like *"it said nothing was at risk"*, treat step 1 as: **reproduce the data, not the screen.**

---

## Before asking the AI agent (Appendix O)

- [ ] State the expected behavior from the spec.
- [ ] State the actual behavior observed.
- [ ] Provide the failing test name and output.
- [ ] Provide the relevant stack trace or log excerpt.
- [ ] Identify recent changes that may have introduced the issue.
- [ ] Name files or modules that are likely involved.

## Root cause review

- [ ] The proposed root cause is supported by evidence.
- [ ] The fix addresses the **cause**, not only the symptom.
- [ ] The fix does not weaken validation, tests, or security.
- [ ] A regression test is added or updated.
- [ ] The debugging specification records the lesson learned.

**A sixth check belongs on this project: does the fix move a rule out of the store?** The
tempting fix for a constraint violation is to catch it earlier in application code. That makes
the symptom disappear and removes the enforcement — BR-002, BR-003 and BR-004 are constraints
and triggers on purpose, and a "fix" that turns one into a service-layer check passes every test
while undoing ADR-004.

---

## Reading the evidence (Ch. 19 §19.3)

A stack trace tells you **where** the runtime error happened. It does not automatically
tell you the root cause — the true cause may be a missing validation rule or an incorrect
assumption in the specification.

Read the failure bottom to top, then connect it back to the requirement:
1. What did the system **receive**?
2. What did it **expect**?
3. What did it **do**?
4. Where did actual behavior **first** differ from expected behavior?

```
Requirement ID: AUTH-REQ-03
Expected:  A user with a valid email and password receives a session token.
Actual:    Login returns 500 Internal Server Error.
Log:       TypeError: cannot read property "id" of null
Likely area: user lookup, password check, or token creation.
```

**When there is no stack trace, the four questions still work — ask them of the data.** For a
ranking that looks wrong: what did the scorer receive for that asset, what did it expect, what
did it produce, and at which of load / match / score / render did the asset first stop being
treated correctly? The `ASSET_SCORING_FAILED` and `SCENARIO_PARSE_FAILED` log events exist to
answer the last question without guessing.

---

## Broken assumptions (Ch. 19 §19.5)

A broken assumption happens when the code believes something the real system does not
guarantee. Fix **four things together**: the code, the test, the requirement, and the
agent instruction. Patching only the code lets the mistake return.

| Assumption | Risk | Spec update | Test update |
|---|---|---|---|
| User always exists | Null error | Define missing-user behavior | Test invalid email |
| Token is always valid | Unauthorized access | Define token expiry rule | Test expired token |
| API field is always present | Crash or bad data | Define required fields | Test missing field |
| Password is always supplied | Weak validation | Define empty input rule | Test empty password |

### The assumptions this product's data actually breaks

The seven measured defects are a list of assumptions that are already known to be false. They
are in the specification precisely so nobody has to discover them as bugs — but an implementation
can still make them, and this table is what to check against when something looks wrong.

| Assumption a reasonable implementation makes | Why it is false here | Already covered by |
|---|---|---|
| One asset has one identifier | Four systems use four codes for the same asset | UTEST-002 |
| A condition value describes the asset now | It may be six years old | UTEST-003, BR-003 |
| A weather station reports gusts | 97% of the values are missing | UTEST-005 |
| An outage total is a real total | 83% were zero in a real file | UTEST-006 |
| Counts are within physical limits | Counties report more customers out than they have | UTEST-007 |
| A repair record is a failure record | Most repairs are routine work | UTEST-008 |
| Public data can identify the failed asset | It is county-level by design | UTEST-008 |

---

## Repeat-error prevention (Ch. 19 §19.6)

After a bug is fixed, confirm that:

- [ ] A test now **fails before** the fix and **passes after** the fix.
- [ ] The requirement explains the expected behavior clearly.
- [ ] The technical spec explains the system rule clearly.
- [ ] The agent instruction warns against the previous mistake.
- [ ] The same bug cannot silently return in a future edit.

> Every serious bug must create at least one new test, one note in the debugging
> specification, and one correction to the requirement, technical spec, or agent
> instruction file.

The fourth box is the one that gets skipped, and on this project it is the one that matters
most: an agent builds every task, so a mistake corrected only in code will be made again in the
next feature by the same agent, following the same unchanged instructions.

---

> Blueprint: blueprints/05-review/04-debugging/debugging-checklist.md
