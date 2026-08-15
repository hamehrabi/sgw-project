# Maintenance Log

> Source: Ch. 30 §30.2 (`07-ops/maintenance-log.md`) + Ch. 4 §4.3 (`07-ops/maintenance-notes.md`).
> Production learning captured as engineering record — not as informal memory.

---

## Log entries

| Date | Signal source | Observation | Classification | Root cause | Action taken | Spec updated | Test added | Owner |
|---|---|---|---|---|---|---|---|---|

**Empty — nothing is in production.** The first entry is written the first time the deployed
system teaches you something, which is not the same as the first time it breaks.

---

## Entry template

```
Date:
Signal source:      [monitoring / user feedback / error tracker / support / QA]
Observation:        [what was seen, with evidence]
Evidence:           [log line, metric, screenshot description, ticket]

Classification:     Bug / Missing requirement / Performance issue / Security issue / Spec drift

Compared with spec: [what the spec says vs. what production does]
Root cause:

Action taken:       [narrow fix / new requirement / spec update / accepted limitation]
Task created:       TASK-###
Spec updated:       CHG-###
Test added:         TEST-###

Follow-up needed:
Owner:
```

**The `Classification` field is where this log earns its place**, and on this project two of its
five values are easy to confuse. A ranking that operators disagree with is not a *Bug* — it may
be *Missing requirement* (the scoring factors were never agreed, Q-025) or it may be the product
working and the guess being wrong, which is a finding rather than a fault. Reach for
`feedback-register.md` before reaching for a fix.

---

## Known issues and limitations

| ID | Issue | Impact | Workaround | Planned fix | Documented for support |
|---|---|---|---|---|---|

Maintained in [`maintenance-notes.md`](maintenance-notes.md), where KI-001 to KI-005 are already
recorded. Kept here as a heading rather than a second copy: two lists of known issues disagree
within a month, and the one somebody reads is whichever they found first.

---

## Operational notes

| Topic | Note |
|---|---|
| Capacity assumptions | → [`maintenance-notes.md`](maintenance-notes.md) |
| Recurring manual steps | → same |
| Seasonal/traffic patterns | → same. In short: storm-driven, near-zero for weeks, then the only hours that matter. |
| Dependencies with known instability | None. Version one depends on nothing outside the process. |

Runbook → [`../ops/runbook.md`](../02-monitoring/runbook.md)

---

## The first three entries this log should expect

Written in advance so the shape is available, and so that recognising a predicted event is
faster than diagnosing a novel one.

| Likely first entry | Signal source | Correct classification | Where it goes |
|---|---|---|---|
| An operator says *"I'd have sent them there anyway"* | User feedback | **Not a bug.** This is assumption A2 failing, and it is the most important observation the project can receive. | `feedback-register.md`, then success metric 1 |
| The unscored-asset count rises between two loads of the same storm | Monitoring (`ASSET_SCORING_FAILED`) | **Correctness** — the input data changed shape, not the code | Investigate the loader; possibly an eighth data defect |
| A migration ran and both triggers are still there | The post-deploy check | **Nothing** — and it should still be recorded the first few times | Here, as evidence the check is actually being run |

The third looks like noise and is not. A check that is never recorded is a check that quietly
stops being performed, and it is the only thing standing between a routine migration and an
editable audit trail.

---

> Blueprint: blueprints/07-ops/03-maintenance/maintenance-log.md
