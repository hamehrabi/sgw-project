# Team Workflow Pack

> Source: Ch. 29 §29.8.
> A repeatable way for product managers, developers, reviewers, and AI agents to move from
> product idea to reviewed output **without losing the source of truth**.

**This file is filled thinly on purpose.** Round 7 answered *an AI coding agent, one task at a
time* rather than *a team of developers*, so the handoff files serve a workspace with one human
and one agent rather than several roles passing work between them. The eight-step workflow below
still applies — steps 4, 5 and 6 are exactly what this project does — but the roles collapse
onto fewer people, and pretending otherwise would produce a coordination plan for a team that
does not exist. **Revisit when:** a second person joins, or the platform is handed to SGW's own
engineers.

---

## Pack

```
Project:                   SGW Resilience Platform, version one
Current release goal:      The P0 probe — joined asset view, ranked risks with reasons,
                           planning view, dispatch board, on uploaded prepared data.
                           Its job is to test assumptions A2 and A3 cheaply.
Source-of-truth location:  spec/ in this repository. Order of precedence is in
                           06-agent/01-instructions/AGENT.md.
Decision owner:            [TODO: name the person who decides — see Q-026]
Product owner:             [TODO: name — see Q-026]
Engineering owner:         [TODO: name — see Q-026]
Reviewer(s):               [TODO: name — see Q-026]
AI agent role:             Implementation, one bounded task at a time (CON-008). Never
                           specification work: nothing under 01-docs/ is a task output.

Current requirements:      01-docs/02-requirements/requirements.md — 10 functional,
                           7 non-functional, 3 role, 5 business rules, 10 acceptance criteria
Current technical spec:    01-docs/04-technical-spec/technical-spec.md — TECH v1.5
Active tasks:              02-tasks/01-planning/task-index.md — 10 tasks; TASK-001 ready,
                           TASK-002 blocked on Q-017
Test plan:                 03-tests/01-plan/test-plan.md — 47 ids, standard depth
Open questions:            01-docs/01-intent/open-questions.md — 12 open, 13 answered
Scope changes:             02-tasks/03-control/scope-change-log.md — none yet
Feedback items:            05-review/01-logs/feedback-register.md — none yet

Next review date:          At the completion of TASK-001
Definition of done:        A task is done when its code matches the requirement, its named
                           tests pass, only approved files changed, the completion note is
                           written, and the traceability row gains a code link.
```

**Every named owner is a `[TODO]`.** Decision owners have been recorded as roles throughout this
workspace — *Product owner (not yet named)*, *Tech lead (not yet named)* — and that was honest
during an interview with one participant. It stops being sufficient the moment a question needs
answering, because a question owned by a role is a question nobody answers. See **Q-026**.

---

## The eight-step workflow (Ch. 29 §29.8)

| Step | Owner | Input | Output | Quality gate |
|---|---|---|---|---|
| 1. Clarify product intent | Product manager | Idea, user problem, stakeholder input. | Problem statement, users, success measure. | Non-goals and risks are stated. |
| 2. Write requirements | Product + engineering | Product intent and constraints. | Requirements with acceptance criteria. | Each requirement is testable. |
| 3. Prepare engineering plan | Developers | Requirements and product spec. | Technical spec, tasks, tests, architecture decisions. | Design matches scope and constraints. |
| 4. Create agent context pack | Developer | Relevant specs and task boundary. | Bounded AI task brief. | Agent has enough context and clear limits. |
| 5. Generate and review output | Agent + team | Task brief and source artifacts. | Draft code, tests, docs, or analysis. | Output passes the review checklist. |
| 6. Capture feedback | Team | Review notes, user input, test results. | Feedback register and decisions. | Every item has an owner and status. |
| 7. Update specs | Assigned owner | Accepted feedback and decisions. | Updated requirements, tasks, tests, traceability. | Source of truth reflects reality. |
| 8. Release or iterate | Team lead | Reviewed output and updated specs. | Accepted change or next task cycle. | No unresolved high-risk gaps remain. |

**Steps 1 to 3 are complete.** Step 4 is complete for TASK-001 only. Steps 5 to 8 have not
started, and step 2's quality gate has one failure on record: REQ-NF-006 is not testable,
because Q-013 never gave it a standard.

---

## Alignment rhythm (Ch. 29 §29.7)

Alignment is not a one-time meeting. It is a rhythm.

| Practice | When to use it | What to check | Output |
|---|---|---|---|
| Spec review session | Before implementation, or after major changes. | Requirements, non-goals, risks, open questions. | Approved spec or action list. |
| Task kickoff | Before assigning work to a developer or agent. | Task boundary, context, tests, review rule. | Clear task brief. |
| Mid-work checkpoint | When ambiguity appears. | Assumptions, blockers, design choices. | Decision or revised task. |
| Review meeting | After a meaningful AI-generated change. | Requirements, architecture, tests, security. | Accept, revise, or reject. |
| Spec update review | After feedback or release learning. | Changed behavior, tests, docs, traceability. | Updated source of truth. |

With one human and one agent, three of these five are the same conversation with yourself — and
the one that must stay formal is the **mid-work checkpoint**, because it is the only mechanism
that turns an agent's invented answer into a question before it becomes code.

### Weekly alignment questions (Ch. 29 §29.7)

1. What requirement changed this week?
2. What decision did we make that must be recorded?
3. Which AI outputs were accepted, revised, or rejected?
4. Which tests were added because of feedback?
5. Which task is too vague for an AI agent to execute safely?
6. What is now out of scope?
7. What must be updated before the next implementation cycle?

**Question 5 already has an answer, before any week has passed:** TASK-002. It is not vague for
want of writing — it is vague because Q-017 has not said what a prepared scenario is.

---

## Team workflow checklist (Ch. 29)

| Area | Checklist item | Status |
|---|---|---|
| Shared source | The team agrees where requirements, specs, tasks, tests, decisions, and feedback live. | [x] |
| Product handoff | Each feature has a problem statement, users, acceptance criteria, risks, and non-goals. | [x] |
| Engineering handoff | Developers convert product intent into technical design, tasks, and tests. | [x] |
| Agent handoff | Each AI-agent task includes scope, context, constraints, expected output, and review rules. | [x] |
| Review | AI output is reviewed against requirements, architecture, security, tests, and maintainability. | [ ] |
| Feedback | Feedback items have affected artifacts, owners, decisions, and status. | [ ] |
| Scope change | Accepted changes update requirements, design, tests, tasks, and traceability. | [ ] |
| Alignment rhythm | The team has regular reviews for open questions, decisions, drift, and next tasks. | [ ] |

Four boxes unticked, all for the same reason: nothing has been built, so nothing has been
reviewed, no feedback exists, no scope change has been requested, and no rhythm has had a chance
to establish itself. The fourth is the one to watch — an alignment rhythm that is never
established does not announce itself, it simply never happens.

---

> Blueprint: blueprints/06-agent/04-handoffs/team-workflow-pack.md
