# Issue / Work Request Template

> Source: Ch. 15 §15.5.
> In spec-driven AI engineering, an issue must not be vague. It points to the requirement,
> the expected behavior, the files likely involved, and the acceptance criteria.

Use this inside a local document, a tracker, or a GitHub issue.

---

```
Issue Title:    [short behavior summary]
Requirement ID: REQ-###
Spec Source:    01-docs/technical-spec.md, [section]
Goal:           [one sentence: what should be true after this is done]

Acceptance Criteria:
- 
- 
- 
- 

Files likely affected:
- 
- 
- 

Out of scope:
- 

Tests required:
- TEST-###

Priority: P0 / P1 / P2 / P3
Owner:
```

---

## One field to add on this project

```
Stop condition:
- [the open question this issue could reach, and the instruction to stop rather than choose]
```

Five open questions have answers an agent could plausibly invent — Q-007, Q-017, Q-021, Q-022,
Q-025 — and an invented answer is indistinguishable from a decision once it is in code. An issue
that could reach one and does not name it is an issue inviting a guess.

---

## Issue quality check

- [ ] Points to a requirement ID that exists.
- [ ] Acceptance criteria are testable, not aspirational.
- [ ] Likely files are named (so unrelated changes are visible in the diff).
- [ ] Out-of-scope items are stated.
- [ ] Tests are identified before implementation.
- [ ] The stop condition is named, or the issue cannot reach one.

**The third box does more work than it looks like.** Naming the likely files is not a
convenience for the implementer — it is what makes an unexpected file visible in the diff. On a
project where an agent writes every change, an issue with no file list produces a pull request
whose scope nobody can check.

---

## A worked issue — the first bug this project is likely to see

Written before it happens, so the shape is available when it does.

```
Issue Title:    An asset with unusable inputs is missing from the ranking
Requirement ID: REQ-F-002, BR-002
Spec Source:    01-docs/07-security-and-reliability/ai-boundary-spec.md §4 (Refusal)
Goal:           An asset that cannot be scored appears in the ranked list, marked
                UNSCORED, with the reason it could not be scored.

Acceptance Criteria:
- An asset with contradictory inputs is present in the ranking response.
- It carries no rank and no score, and a stated reason.
- It is NOT given a default score, and NOT given a low score.
- The ranking for every other asset completes normally.
- ASSET_SCORING_FAILED is logged with scenario_id, asset_id, and reason.

Files likely affected:
- 04-src/scoring/          (the refusal path)
- 04-src/api/              (the response shape for an unscored item)
- 04-src/views/            (RiskList rendering of UNSCORED)

Out of scope:
- Changing the scoring rule itself
- Anything about why the inputs were contradictory — that is a loader concern

Tests required:
- FTEST-004

Priority: P0
Owner:    [TODO — see Q-026]

Stop condition:
- None. This is fully specified; if the implementation appears to need a decision,
  the specification has been misread.
```

**Why this one is worth writing in advance:** it will not arrive as a bug report. It arrives as
somebody saying *"it said nothing was at risk"* — no error, no exception, no failing feature
test, and a screen that looked entirely reasonable. Having the issue already shaped means the
first response is to check the data rather than to argue about the screen.

---

> Blueprint: blueprints/05-review/03-version-control/issue-template.md
