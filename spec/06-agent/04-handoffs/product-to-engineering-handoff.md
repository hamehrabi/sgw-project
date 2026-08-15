# Product-to-Engineering Handoff

> Source: Ch. 29 §29.2.
> Where product intent becomes **buildable engineering work**. The goal is not to hand
> developers a vague idea and ask them to figure it out.

---

## Template (Ch. 29 §29.2)

```
Feature name:
Problem statement:
Target users:
User goals:

Must-have requirements:
  - 
  - 

Acceptance criteria:
  - 
  - 

Non-goals for this release:
  - 

Known constraints:
  - 

Risks and sensitive areas:
  - [security, privacy, reliability, usability, compliance]

Open questions:
  - 

Decision owner:
Date of handoff:
```

---

## The handoff for version one

```
Feature name:      SGW Resilience Platform, version one — the ranked-risk probe
Problem statement: When a storm is one to three days away, SGW's operations manager must
                   decide where to place crews; during the storm the dispatcher must
                   decide what is repaired first. Both decide well, but the facts sit in
                   four systems that do not share data — so the plan is built by hand over
                   hours and restarts whenever the forecast shifts, the damage picture is
                   assembled from radio calls and a whiteboard, and no numbers are ready
                   when a regulator calls. Two of the six parts of a sound decision are
                   broken: the information, and the reasoning that rests on it.
Target users:      Operations manager (before the storm), dispatcher (during it). The
                   field crew lead and the executive are NOT served by version one.
User goals:        Reach a crew placement from current shared facts rather than assembling
                   them; hold one damage picture rather than reconstructing it; be able to
                   show afterwards why a job was ordered as it was.

Must-have requirements:
  - Join the uploaded files into one record per asset, each value carrying its source
    and its age (REQ-F-001)
  - Rank every asset by risk, with plain-words reasons beside each rank (REQ-F-002/003)
  - Accept, change, or reject every recommendation; the system never acts (REQ-F-006)
  - One shared list of damage reports and repair jobs (REQ-F-007)
  - An unalterable record of every recommendation and decision (REQ-F-009)
  - An admin uploads a prepared storm; several may be loaded at once (REQ-F-010)

Acceptance criteria:
  - ATEST-001 to ATEST-010, in 03-tests/02-functional/acceptance-tests.md. Every one is
    Given/When/Then with an observable result.
  - The four that decide whether version one is worth anything are written out in full
    there: ATEST-002, ATEST-004, ATEST-006, ATEST-009.

Non-goals for this release:
  - Live connections to the four source systems — version one runs on uploaded files
  - Water early-warning on sensor readings
  - The automatic summary writer for leadership
  - The offline crew app, field photo capture, and route planning
  - Any threshold that turns a rank into an instruction to act
  - Any outbound path to a system controlling the grid or the water network, at any version

Known constraints:
  - CON-002: about one week for version one
  - CON-005: prepared files only; no live connections
  - CON-006: no paid third-party services
  - CON-007: read-only toward controlling systems; neighbourhood-level display
  - CON-008: an AI coding agent builds it, one task at a time

Risks and sensitive areas:
  - Product: a combined ranked view may not change the crew decision (assumption A2), and
    operators may not act on a computer's ranking (A3). Version one exists to find out.
  - Safety: an asset silently missing from a ranking is indistinguishable, on screen, from
    an asset that is safe. FTEST-004 exists for this alone.
  - Security: asset locations and connections describe critical infrastructure. The upload
    is the only place untrusted input enters, and there is no malware scanner (CON-006) —
    accepted with a written revisit trigger.
  - Reliability: the platform is used DURING the event it describes. Every failure lands
    mid-storm, in front of someone deciding where to send people.
  - Compliance: the decision record is evidence for a regulator, and no retention period
    has been set.

Open questions:
  - Blocked on Q-017 until the prepared-scenario formats and sizes are known — TASK-002
    cannot start, and eight tasks sit downstream of it.
  - Q-025 governs the scoring factors and weights; ADR-005 fixes the kind of scorer, not
    its content. Q-013 leaves accessibility as a requirement with no standard behind it.
    Q-007, Q-012, Q-015, Q-018, Q-019, Q-021, Q-022 and Q-024 remain open with owners.

Decision owner: Product owner (not yet named)
Date of handoff: 2026-08-15
```

---

## Handoff items (Ch. 29 §29.2)

| Item | What it should contain | Question it answers | Common weakness |
|---|---|---|---|
| Problem statement | User pain, business reason, current limitation. | Why should this be built? | The problem is described as a feature request only. |
| User requirement | User goal, action, outcome, acceptance criteria. | What must the user be able to do? | The requirement has no pass/fail condition. |
| Priority and non-goals | Must-have, should-have, later, explicitly out of scope. | What should the team **not** build now? | The team overbuilds because boundaries are missing. |
| Risk notes | Security, privacy, reliability, usability, compliance concerns. | What could go wrong? | Risks are discovered after implementation. |
| Open questions | Unknowns that need a decision before or during design. | What needs clarification? | The AI agent fills gaps with guesses. |

> **An open question in a handoff is a CITATION.** `Q-` rows are DEFINED in
> `open-questions.md`, and only there. Cite the id inside prose — *"blocked on `Q-###` until
> the export format is decided"* — never as a table row whose first cell is the id with
> the question restated beside it. The register owns the question, its owner, and its status;
> a restated copy here disagrees with it the day either changes.

---

## What each role needs (Ch. 29 §29.1)

| Role | What the role needs | What goes wrong without specs | Spec artifact that helps |
|---|---|---|---|
| Product manager | Clear scope, user needs, priorities, acceptance criteria. | Features built that do not match the product goal. | PRD and change log. |
| Developer | Architecture, constraints, data model, APIs, tests. | Code works locally but breaks design, security, or maintainability. | Technical specification and task list. |
| AI agent | Bounded context, explicit instructions, examples, forbidden changes. | The agent guesses, overbuilds, or changes unrelated code. | Agent context pack and task brief. |
| Reviewer | Requirements, expected behavior, tests, risks, evidence. | Review becomes opinion-based instead of evidence-based. | Review checklist and traceability matrix. |
| Stakeholder | Visible progress, trade-offs, decisions, impact. | Feedback arrives late and causes major rework. | Decision log, demo notes, feedback register. |

> **Practical rule:** a shared specification should answer three questions for everyone:
> *What are we building? How will we know it works? What has changed since the last
> decision?*

The third question has a specific answer here, and it is not obvious from any single document:
**CHG-001 to CHG-005 in the spec change log.** Five accepted decisions were changed during the
interview itself, each because a later answer made an earlier one unsatisfiable. Anyone reading
this workspace for the first time should read that table before anything else in `01-docs/`.

---

## Downstream chain

```
Product handoff
    → 01-docs/requirements.md          (engineering converts intent to testable behavior)
    → 01-docs/technical-spec.md
    → 02-tasks/                          (bounded work)
    → 06-agent/developer-to-agent-handoff.md
    → 05-review/                        (team review of output)
    → 01-docs/spec-change-log.md        (updated source of truth)
```

---

## Handoff acceptance check

Engineering should refuse a handoff that cannot answer these:

- [x] Is the problem stated, not just the feature?
- [x] Are the users named?
- [x] Does every must-have requirement have a pass/fail acceptance criterion?
- [x] Are the non-goals written down?
- [x] Are risks and sensitive areas identified?
- [x] Are open questions listed with a decision owner?

**All six pass, and the handoff is still not fully buildable** — which is worth saying plainly
rather than letting the ticks imply otherwise. The gap is not in the handoff: it is Q-017,
listed above with its owner, blocking the task eight others depend on. A handoff that names its
blocker is acceptable; one that hides it behind six green ticks is not.

---

> Blueprint: blueprints/06-agent/04-handoffs/product-to-engineering-handoff.md
