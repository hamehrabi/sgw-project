# Specification Change Log

> Source: Ch. 30 §30.3 (Versioning Requirements and Specs) + Ch. 24 §24.7.
> **The rule:** code must not quietly move ahead of the specification. When behavior
> changes, the requirement, test, task, and review evidence change with it.

---

## Current versions

| Artifact | Version | What changes it | Who approves | Evidence needed |
|---|---|---|---|---|
| PRD | PRD v1.1 | New requirement, changed priority, clarified non-goal. | Product owner | Change note and affected requirement IDs. |
| Technical spec | TECH v3.0 | Architecture, API, data model, or integration decision. | Technical lead or reviewer | ADR or design note. |
| Test spec | TEST v1.0 | New behavior, bug fix, edge case, failure path. | Developer and reviewer | New or updated test cases. |
| Agent rules | AGENT v1.0 | Repeated AI mistake or new coding boundary. | Team lead | Reason and example. |
| Release plan | REL v1.0 | Deployment target, rollback strategy, monitoring rule. | Release owner | Checklist update. |

---

## Change entries

```
Change ID:
Date:
Changed artifact:
Old version:
New version:
Reason for change:
Affected requirements:
Affected tests:
Affected tasks or code areas:
Decision owner:
Reviewer:
Status: proposed / accepted / rejected / deferred
Notes:
```

| Change ID | Date | Artifact | Old → New | Reason | Affected REQ | Affected TEST | Owner | Status |
|---|---|---|---|---|---|---|---|---|
| CHG-001 | 2026-08-15 | `database-design.md` + `data-and-integration-spec.md` | TECH v1.0 → v1.1 | Q-014 answered mid-run: an admin uploads prepared scenarios through the application, and several storms may be loaded at once. Both files were written while that was undecided. | REQ-F-010 | — (Round 7) | Developer | accepted |
| CHG-002 | 2026-08-15 | `fitness-functions.md` + `database-design.md` + `technical-spec.md` | TECH v1.1 → v1.2 | ADR-002 chose an embedded store, which has no role system. BR-004's grant-based enforcement became unrunnable, so ADR-004 replaced it with database triggers and FF-004's check was rewritten. The two separate database credentials in §7.5 no longer exist. | BR-004, REQ-F-009, REQ-R-002 | — (Round 7) | Developer | accepted |
| CHG-003 | 2026-08-15 | `fitness-functions.md` | TECH v1.2 → v1.3 | Round 5 named "all seven known data defects are caught" as a release gate. Nothing in the register covered it, so FF-006 was added. | REQ-NF-003 | — (Round 7) | Developer | accepted |
| CHG-004 | 2026-08-15 | `technical-spec.md` §7.1, §7.2 | TECH v1.3 → v1.4 | Round 6 confirmed no external services, removing email delivery. The reset-link flow ADR-003 implied became unsatisfiable, so password recovery is an admin-set temporary password and the RBAC matrix gained a row. Derived rather than chosen — see Q-024. | REQ-NF-002, SEC-A-004, SEC-Z-006 | — (Round 7) | Developer | accepted |
| CHG-005 | 2026-08-15 | `05-architecture/` — new ADR-005, index and decision log updated | TECH v1.4 → v1.5 | Q-023 answered during Round 7, after the task plan showed TASK-003 blocked with nothing to unblock it. Version one scores with a deterministic weighted rule behind the existing model boundary; deep learning rejected for this scorer on explainability; decision-tree family named as successor. Raises Q-025. | REQ-F-002, REQ-F-003, BR-002 | EVAL-001 | Developer | accepted |
| CHG-007 | 2026-08-15 | `05-architecture/` — new ADR-008 and ADR-009; CON-006 amended; `.env.example`, `runtime-and-scale.md`, `fitness-functions.md`, `ai-boundary-spec.md`, `technical-spec.md` | TECH v2.0 → v3.0 | **Two decisions taken after the intake closed.** ADR-008 moves the backend to Python/FastAPI with Next.js as a separate frontend — amending ADR-001's one-process claim and ADR-002's driver, and resolving the background-job and trigger-generation gaps. ADR-009 introduces a hosted OpenAI model that **phrases computed reasons and may invent nothing**, reversing CON-006 and Round 6's "no external services", and reopening Q-019. Adds FF-007. Raises Q-029, Q-030. | REQ-F-003, BR-002, REQ-NF-003, REQ-NF-007 | FF-007 | Developer | accepted |
| CHG-006 | 2026-08-15 | 20 files across `01-docs/`, `02-tasks/`, `03-tests/`, `07-ops/`; new ADR-006 and ADR-007 | TECH v1.5 → v2.0 | **Fourteen open questions answered after the intake closed.** Q-017 (scenario = manifest + four CSVs, under 5 MB) unblocked TASK-002 and eight downstream tasks. Q-027 (Next.js/TypeScript + SQLite) filled every command in `07-ops/`. Q-007 enumerated the forbidden data. Q-021 and Q-025 became ADR-006 and ADR-007. Q-012 gave measurable limits; Q-013 gave REQ-NF-006 a standard and ATEST-011; Q-015 set retention; Q-011, Q-019, Q-022, Q-024 closed. Q-018 and Q-028 deliberately left open with reasons. | REQ-NF-001, REQ-NF-004, REQ-NF-006, REQ-NF-007, SEC-A-002, SEC-A-004, SEC-A-006, CON-003 | ATEST-011, PTEST-001, PTEST-002 | Developer | accepted |

---

## Stage acceptance and skips

Two things are recorded here as **dated rows**, and neither is ever a file of its own: the
acceptance of each round's gate, and any blueprint deliberately skipped with its reason.

A separate acceptance file would be a second place to look for the same fact, and the two
would disagree within a week. A row in the log that already exists cannot.

**The date is the first column.** That is what makes a row findable — an acceptance buried
in a nine-column change entry is not a record anyone can check, and the change-entries table
above starts with an identifier rather than a date, so it cannot serve.

| Date | Stage or type | Artifact | Note or reason |
|---|---|---|---|
| 2026-08-15 | Round 1 — the idea | — | Accepted by the developer. 7 decisions, 2 inferences, 6 TODOs (Q-001 to Q-006). |
| 2026-08-15 | Round 2 — scope boundaries | — | Accepted by the developer. 6 decisions, 1 inference, 4 new TODOs (Q-007 to Q-010); Q-001 to Q-004 closed. |
| 2026-08-15 | Round 3 — users, roles, and data | — | Accepted by the developer. 8 decisions, 4 inferences, 6 new TODOs (Q-011 to Q-016); Q-010 closed. |
| 2026-08-15 | Round 4 — product shape | — | Accepted by the developer. 9 decisions, 2 inferences, 3 new TODOs (Q-018 to Q-020); Q-005 closed. |
| 2026-08-15 | Round 5 — architecture and stack | — | Accepted by the developer. 7 decisions (ADR-001 to ADR-004, DD-001 to DD-007), 1 inference, 2 new TODOs (Q-021, Q-022); Q-016 and Q-020 closed. CHG-002 and CHG-003 raised. |
| 2026-08-15 | Round 6 — security, reliability, integrations | — | Accepted by the developer. 8 decisions (SEC-A-001 to SEC-A-006, SEC-Z-001 to SEC-Z-006), 3 inferences, 2 new TODOs (Q-023, Q-024). CHG-004 raised. `ai-boundary-spec.md` filled rather than skipped. |
| 2026-08-15 | Round 7 — tasks and tests | — | Accepted by the developer. 11 decisions (TASK-001 to TASK-010, A-001 to A-015, 47 test ids), 2 inferences, 1 new TODO (Q-025); Q-009 and Q-023 closed. CHG-005 raised, adding ADR-005 out of round. `ai-evals.md` filled rather than skipped. |
| 2026-08-15 | Round 8 — operations | — | Accepted by the developer. 9 decisions, 1 inference, 1 new TODO (Q-026), deferred at the developer's direction: no real people exist, one person holds every role for the prototype, rollback triggers self-approved, naming left as a production-planning TODO rather than invented. Final round; 39 files written. |

**A skip with no reason is a silent skip wearing a label.** The reason is what lets a later
reader tell a decision from an omission.

---

## When implementation reveals something the spec missed (Ch. 15 §15.8)

| When this happens | Update this document |
|---|---|
| A rule becomes clearer during implementation | Requirements document |
| A design decision changes | Technical specification or ADR |
| A new test case is discovered | Test plan |
| A task produces extra work | Task plan and traceability matrix |
| A behavior is removed or postponed | Scope and out-of-scope notes |

## When production teaches you something (Ch. 3 §3.9)

| Change type | Artifact to update |
|---|---|
| A new user behavior is added. | Requirements and product specification. |
| A data field or relationship changes. | Technical specification and data model. |
| A new security rule is added. | Requirements, technical specification, test plan. |
| A bug reveals missing expected behavior. | Requirement, test plan, task history. |
| Deployment process changes. | Deployment checklist and maintenance notes. |

---

## Spec update fields (Ch. 24 §24.7)

| Field | What to write |
|---|---|
| Change date | When the spec was updated. |
| Reason | Bug fix, user feedback, performance issue, security finding, product decision. |
| Affected requirement | The requirement ID or section that changed. |
| Affected tests | Which tests need to be added or changed. |
| Affected code area | The module, endpoint, page, job, or service connected to the change. |
| Review status | Draft, reviewed, approved, implemented, or released. |

---

> **Spec drift warning (Ch. 15 §15.8):** spec drift happens when the code changes but the
> specification stays behind. The longer you allow drift, the harder it becomes to trust
> the source of truth for your project.

---

> Blueprint: blueprints/01-docs/09-change-control/spec-change-log.md
