# intent.md — Engineering Intent Document

> **Purpose (Ch. 4 §4.4):** Captures problem, users, goals, scope, and constraints.
> **When you use it:** Before writing requirements.
> **Sources:** Appendix A + Ch. 2 §2.7.

One page. Shorter than a PRD, simpler than a technical spec. It is the bridge between a
rough idea and formal requirements — and a strong input for AI, because you can hand the
agent this instead of a vague idea.

**Detail documents in this folder**

| Document | Covers |
|---|---|
| [`project-brief.md`](project-brief.md) | The raw idea, vision vs. implementation, problem-statement formula. |
| [`constraints-and-non-goals.md`](constraints-and-non-goals.md) | Full constraint table and out-of-scope decisions. |
| [`open-questions.md`](open-questions.md) | Unresolved questions and the ambiguity test. |

> **Beginner rule (Ch. 2):** do not ask an AI agent to build from a vague idea. First
> convert the idea into engineering intent.

---

## The document

| Field | Value |
|---|---|
| **Project name** | SGW Resilience Platform |
| **Problem statement** | SGW's storm decisions are made by capable people, but the facts those decisions need sit in four systems that do not share data. So the crew plan is built by hand over hours and restarts whenever the forecast shifts, the damage picture during the storm is assembled from radio calls and a whiteboard, and no numbers are ready when a regulator calls. That costs longer outages, penalty fees, premium-priced emergency crews and rising insurance. Storm decisions should be made from one current, shared set of facts, with people still making every decision. |
| **Primary users** | The operations manager, who places crews before the storm, and the dispatcher, who chooses what is repaired first during it. |
| **Secondary users** | The field crew lead, who carries out the repairs, and the executive, who answers to regulators and the press. |
| **Business goal** | Shorter outages and provable decisions — fewer penalty payments, less premium-priced emergency help, a defensible record for regulators, and a reason for insurers to reconsider premiums. |
| **User goal** | Build and adjust a storm plan in minutes rather than hours, hold one current picture of damage rather than assembling one from radio and a whiteboard, and have current numbers ready at any moment. |
| **Current pain points** | The forecast changes and hours of manual collection start again from zero. Building one full damage picture takes about thirty minutes while new reports keep arriving. Radio and phone signal degrade in the storm, and crews drive to the same place twice. A regulator or journalist asks for numbers nobody has ready. Afterwards there is no clean record of what was decided, when, or why. |
| **Core capabilities** | Four, all in version one: a joined asset view built from prepared data, with the source and age of every value; a list of assets ranked by risk with a plain-words reason beside each rank; a planning view for the operations manager; and a dispatch board for the dispatcher. The ranked risk list is the one this product competes on — see [`subdomain-map.md`](subdomain-map.md). |
| **Desired outcome** | The four roles work from one shared, current set of facts. The plan adjusts when the forecast changes instead of restarting. Every recommendation and every human decision is recorded with its time, so the next storm can be learned from and the last one can be explained. |
| **Out of scope** | → [`constraints-and-non-goals.md`](constraints-and-non-goals.md) |
| **Success measures** | Carried from the source PRD (`proj-knowledge/PRD-SGW-brochure.pdf`, §9) and not yet confirmed as version-one targets — see Q-005. Time to build or adjust the storm plan falls from hours to under one hour, including after a forecast change. Time to one full damage picture falls from about thirty minutes to under five. In scenario tests, operators change their plan in at least one storm in three. Real failures flagged in advance: at least seven in ten, checked by replaying past storms. |
| **Constraints** | → [`constraints-and-non-goals.md`](constraints-and-non-goals.md) |
| **Risks** | The three unproven guesses named in the source PRD (§2), any one of which can end the project: that asset and maintenance data can actually be pulled out of SGW's systems (A1); that a combined, ranked view really changes the crew decision (A2); and that operators will act on rankings produced by a computer (A3). A fourth risk is local to this workspace: the build horizon is about one week, and the scope that fits inside it has not yet been decided (Q-001). |
| **Open questions** | → [`open-questions.md`](open-questions.md) |

### Starter (Appendix A)

```
Project Name:
Problem Statement:
Primary Users:
Business Goal:
User Goal:
Pain Points:
Desired Outcome:
Out of Scope:
Success Measures:
Constraints:
Open Questions:
```

---

## Users, goals, and constraints (Ch. 2 §2.4)

| Element | Question to answer | Your answer |
|---|---|---|
| Primary user | Who uses the system most often? | The operations manager before the storm, and the dispatcher during it. |
| Secondary user | Who reviews, manages, or supports the system? | The field crew lead in the field, and the executive answering regulators and press. |
| Goal | What should improve after the system exists? | Storm decisions are made from one current, shared set of facts, and the plan adjusts when the forecast changes instead of being rebuilt. |
| Constraint | What must limit the design? | Version one is an internal dashboard for a team inside one company, under 50 users, with a build horizon of about one week. No paid third-party services, and certain data must not be stored. Version one runs on prepared data files rather than live connections. The full table, including which data is restricted, is in [`constraints-and-non-goals.md`](constraints-and-non-goals.md). |
| Risk | What could make the project fail? | The data cannot be reached (A1); a combined view does not change the decision (A2); operators do not act on computer rankings (A3); or the scope chosen exceeds the one-week horizon. |

> **Important distinction:** a goal is not a feature. "Create task comments" is a feature.
> "Make task discussions easier to follow" is a goal.

---

## Intent quality checklist (Appendix A)

- [x] The problem is stated without assuming a specific technical solution.
- [x] The intended users are named clearly.
- [x] The desired outcome can be measured or observed.
- [ ] Out-of-scope items are written before implementation begins.
- [x] Open questions are captured instead of being hidden.

## Chapter checklist (Ch. 2)

| Before you move to requirements, confirm that you have: | Done |
|---|---|
| A clear problem statement. | [x] |
| Defined primary and secondary users. | [x] |
| Separated vision from implementation details. | [x] |
| Listed first-version capabilities. | [ ] |
| Listed what is out of scope. | [ ] |
| Identified constraints and risks. | [ ] |
| Defined simple success criteria. | [x] |

> **Self-check (Ch. 2):** if this document does not make writing requirements *easier*,
> it is too vague.

---

**Next:** [`requirements.md`](../02-requirements/requirements.md)

---

> Blueprint: blueprints/01-docs/01-intent/intent.md
