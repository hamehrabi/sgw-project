# maintenance-notes.md — Maintenance Notes

> **Purpose (Ch. 4 §4.3):** The `/ops` folder stores deployment and **maintenance** notes.
> **Sources:** Ch. 24, Ch. 30 §30.7, Appendix Q.

**Detail documents in this folder**

| Document | Covers |
|---|---|
| [`monitoring-plan.md`](../02-monitoring/monitoring-plan.md) | What to observe: availability, correctness, performance, errors, usage, security. |
| [`spec-drift-checklist.md`](spec-drift-checklist.md) | Appendix Q — after every release and monthly. |
| [`maintenance-log.md`](maintenance-log.md) | Dated production-learning entries. |
| [`release-notes.md`](../04-release/release-notes.md) | What shipped, when, and which requirements. |
| [`engineering-quality-review.md`](../04-release/engineering-quality-review.md) | Quality metrics and the improvement loop. |
| [`runbook.md`](../02-monitoring/runbook.md) | Incident procedure and failure playbooks. |

> **The production rule (Ch. 24 §24.1):** every meaningful production lesson should answer
> one question — **does the spec still describe the system you need to maintain?**
>
> A code fix without a spec update solves today's bug and creates tomorrow's confusion.

---

## Operational facts

| Item | Value |
|---|---|
| Service name | SGW Resilience Platform |
| Environments | local / test / production |
| Health endpoint | `/health` |
| Log location | Structured logs to stdout, collected from the container |
| Metrics dashboard | None — Round 8 chose logs plus error alerts |
| Error tracker | None off-site — Round 6 declined it, to keep stack traces containing infrastructure context inside SGW |
| On-call owner | [TODO — see Q-026] |
| Rollback approver | [TODO — see Q-026] |
| Backup schedule / restore procedure | Nightly file copy of the database and scenario uploads. → [`backup-and-recovery.md`](../01-deployment/backup-and-recovery.md). **Restore never tested.** |

---

## Known issues and limitations

| ID | Issue | Impact | Workaround | Planned fix | Documented for support |
|---|---|---|---|---|---|
| KI-001 | No malware scanning on uploaded scenario files | An admin could upload a malicious file | Admin-only; files parsed as data, never executed, never served back to a browser | Revisit if the upload opens beyond admins or a file is ever returned to a browser | Yes |
| KI-002 | Single writer (ADR-002) | A parse job and an operator decision can contend | Invisible at 50 users | Revisit at concurrent writers, or the first live connection | Yes |
| KI-003 | Availability target is 99.0% | About 7 hours a month, which is fine on ordinary days and not fine during a hurricane | None | The target must be revisited before the platform is used in a real storm | Yes |
| KI-004 | Recovery objective of 24 hours means up to a day of decision records is unrecoverable | Scenarios and rankings are re-derivable; the decision record is not | None | Tighten the backup frequency — cheap here, since a backup is a file copy | Yes |
| KI-005 | No accessibility standard is defined | REQ-NF-006 is a requirement with no design and no test | None | Answer Q-013, or move accessibility to non-goals | Yes |

**These are known before anything is built**, which is unusual and useful: each one is a
consequence of a decision that was written down with its trade-off, rather than a surprise found
in production. KI-003 and KI-004 are the two worth reading twice — both are acceptable for a
probe on prepared data and neither is acceptable for a platform used during a real storm.

## Operational notes

| Topic | Note |
|---|---|
| Capacity assumptions | Under 50 users, one container, one instance, one embedded database file. Sized for one prepared scenario at a time; **the size of a scenario is unknown (Q-017)**, so this assumption is untested. |
| Recurring manual steps | Confirming both `decision_records` triggers exist after every migration. It is a manual step until TASK-010 wires FF-004 into a gate. |
| Seasonal / traffic patterns | Storm-driven, not weekday-driven. Load is near zero for weeks, then concentrated into hours — and those hours are the only ones that matter. **Never schedule maintenance during a storm.** |
| Dependencies with known instability | **None.** Version one depends on no external service (Round 6, CON-005, CON-006), which is the largest single reliability decision in the design. |
| Data retention jobs | A deleted scenario's files are removed with it. Decision records are never removed (BR-004). **No retention period is set** — see Q-015. |

---

## Maintenance checklist (Ch. 24 §24.9)

Run after each release, after each serious production issue, and before asking an AI agent
to make a major change to an existing system.

| Maintenance check | Done? |
|---|---|
| Key workflows have monitoring requirements. | Yes |
| Errors are grouped and reviewed by severity. | Yes, in plan |
| Logs include request IDs and useful context. | Yes, specified |
| Performance targets exist for important workflows. | **No** — the targets are words, the numbers are unset (Q-012) |
| User feedback is mapped to requirements or decisions. | Yes — the register exists and is empty |
| Specs are updated after production behavior changes. | Not applicable yet |
| New or changed behavior has matching tests. | Yes — 47 ids written before any code |
| AI agent instructions use the current spec, not outdated context. | Yes today — and this is the check that degrades fastest |
| Spec drift review is completed before major changes. | Not applicable yet |

---

## What to update when behavior changes (Ch. 3 §3.9)

| Change type | Artifact to update |
|---|---|
| A new user behavior is added. | `01-docs/requirements.md` and `01-docs/product-spec.md` |
| A data field or relationship changes. | `01-docs/technical-spec.md` and `01-docs/database-design.md` |
| A new security rule is added. | `01-docs/requirements.md`, `01-docs/security-specification.md`, test plan |
| A bug reveals missing expected behavior. | Requirement, test plan, `05-review/debugging-specification.md` |
| Deployment process changes. | `deployment-checklist.md` and this file |

One more, specific to this system: **a change to the scoring factors or weights** updates
`ai-evals.md` (the eval set is re-run), the decision log (a weight change is a product decision),
and Q-025's status. It is not a configuration tweak.

> **Maintenance rule:** when behavior changes, update the spec. If the spec does not change
> with the system, it slowly stops being useful.

---

## Areas to watch (Ch. 27 §27.10)

| Area | What to watch | Action | Spec update required? |
|---|---|---|---|
| Correctness | Impossible values, mismatch with source data. | Investigate ingestion and calculation rules. | Yes, if meaning changes. |
| Performance | Slow endpoints. | Review queries, indexes, cache rules, ranges. | Yes, if limits or targets change. |
| Error tracking | API failures, failed jobs, permission errors. | Classify cause and create fix tasks. | Yes, if new error states appear. |
| User feedback | Confusing UI, missing filters, new requests. | Convert repeated feedback into requirements. | Yes, when accepted into the roadmap. |
| **Spec drift** | Code behavior no longer matches requirements. | Update specs or refactor code to match approved behavior. | **Always.** |

---

## Monthly maintenance review (Appendix Q)

- [ ] Compare top user feedback with current requirements.
- [ ] Review frequent errors and decide whether specs or code need updates.
- [ ] Review performance trends and capacity assumptions.
- [ ] Remove obsolete tasks and mark superseded decisions.
- [ ] **Refresh the project context pack before giving it to an AI agent.**

---

> Blueprint: blueprints/07-ops/03-maintenance/maintenance-notes.md
