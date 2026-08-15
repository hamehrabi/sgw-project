# Prompt Library for Spec-Driven AI Engineering

> Source: Appendix J + Ch. 13.
> Replace bracketed sections with your project details. The strongest prompts connect the
> agent to **requirements, specs, tests, and review expectations**.

> **Prompt safety rule (Appendix J):** never ask an AI agent to "just fix everything."
> Ask it to work from one requirement, one task, one failing test, or one review checklist
> at a time.

---

## Quick index (Appendix J)

| Purpose | Prompt |
|---|---|
| Clarify intent | Review this project idea and identify missing business goals, user goals, constraints, risks, and open questions. Do not propose implementation yet. |
| Create PRD | Turn this engineering intent into a PRD with goals, non-goals, user stories, functional requirements, non-functional requirements, and acceptance criteria. |
| Improve requirements | Review these requirements for ambiguity, missing acceptance criteria, hidden assumptions, and testability problems. |
| Create technical spec | Convert this PRD into a technical specification with architecture, modules, data flow, API needs, error handling, security rules, and test strategy. |
| Create task list | Break this technical specification into small implementation tasks. Each task must map to a requirement and include acceptance criteria. |
| Create test plan | Generate unit, integration, end-to-end, security, and edge-case tests from these acceptance criteria. Avoid shallow tests. |
| Review generated tests | Review these tests against the requirements. Identify shallow tests, missing edge cases, and tests that assert implementation details instead of behavior. |
| Implement one task | Implement only TASK-[ID]. Follow the specs, preserve existing behavior, add tests first, and report changed files and assumptions. |
| Code review | Review this code against requirements, architecture, security, validation, performance, and maintainability. Do not rewrite yet; provide findings first. |
| Debug | Use the logs, stack trace, failing tests, and expected behavior to identify the likely root cause. Explain evidence before suggesting a fix. |
| Security review | Review this feature for authentication, authorization, input validation, data protection, secrets exposure, and secure error handling. |
| Deployment review | Review this deployment plan for environment setup, configuration, migrations, rollback, monitoring, and production readiness. |
| Spec drift review | Compare current behavior with the original specs. Identify drift, undocumented changes, and specs that need updating. |

---

## Core four (Ch. 13 §13.8)

### Template 1 — Clarify before building
```
Before writing code, review the specification below.
List any missing details, contradictions, risky assumptions, or unclear requirements.
Do not implement anything yet.

Specification: [PASTE SPEC]

Return:
- Missing details
- Contradictions
- Questions I should answer
- Safe assumptions, if any
```

### Template 2 — Generate implementation plan
```
Using the approved specification below, create a step-by-step implementation plan.
Do not write code yet.

Specification: [PASTE SPEC]

Return:
- Files or modules likely involved
- Tasks in the correct order
- Tests to write before or during implementation
- Risks to review before coding
```

### Template 3 — Implement one task
```
Implement this one task only:
[TASK ID AND TASK DESCRIPTION]

Source of truth:
[PASTE REQUIREMENT / TECHNICAL SPEC / API CONTRACT]

Boundaries:
- Do not work on other tasks.
- Do not change unrelated files.
- Do not add features outside the specification.

Return:
- Code changes
- Short explanation
- Requirement IDs covered
- Suggested tests
```

### Template 4 — Review against the spec
```
Review the output below against the approved specification.
Do not rewrite the whole solution unless necessary.

Approved specification: [PASTE SPEC]
Output to review: [PASTE CODE OR PLAN]

Return:
- What matches the spec
- What is missing
- What is extra or out of scope
- What should be corrected first
```

---

## Prompting from each artifact type (Ch. 13)

### From a requirement (§13.2)
```
You are working from this approved requirement:
[PASTE REQUIREMENT]

Your task:
[STATE ONE SMALL TASK]

Boundaries:
- Do not change: [LIST FILES OR FEATURES]
- Do not add: [LIST OUT-OF-SCOPE ITEMS]

Acceptance criteria:
[PASTE ACCEPTANCE CRITERIA]

Output required:
- Implementation steps
- Code or structured draft
- A short traceability note showing how the output satisfies the requirement
```

### From a product spec (§13.3)
```
Using the product requirements below, create a feature plan for [FEATURE NAME].

Product goal:  [PASTE PRODUCT GOAL]
Target user:   [PASTE USER PERSONA]
In scope:      [PASTE FEATURE SCOPE]
Out of scope:  [PASTE OUT-OF-SCOPE ITEMS]

Return:
1. The feature behavior in simple steps
2. The screens or endpoints needed
3. The main user flow
4. Risks or unclear points that must be clarified before coding
```

### From a technical spec (§13.4)
```
Use the technical specification below as the source of truth.

Technical area to work on: [FRONTEND / BACKEND / DATABASE / API / SECURITY]
Approved technical decisions: [PASTE RELEVANT EXCERPT]
Task: [STATE ONE SMALL IMPLEMENTATION TASK]

Constraints:
- Follow the existing folder structure.
- Use the existing naming style.
- Do not change unrelated modules.
- Do not introduce a new library unless the spec says so.

Return:
- The proposed files to create or edit
- The implementation
- A short explanation of how the code follows the technical spec
```

### From an API contract (§13.5)
```
Implement the API endpoint using this contract only:

Endpoint:          [PASTE ENDPOINT AND METHOD]
Request contract:  [PASTE REQUEST BODY]
Response contract: [PASTE RESPONSE BODY]
Validation rules:  [PASTE VALIDATION RULES]
Error behavior:    [PASTE ERROR RESPONSES]

Important boundaries:
- Do not change the contract.
- Do not rename fields.
- Do not add extra response fields.
- If something is unclear, list the question before writing code.

Return:
- Endpoint logic
- Validation logic
- Example success response
- Example error response
```

### For tests (§13.6)
```
Create tests from the acceptance criteria below.
Do not test behavior that is not listed.

Feature:             [FEATURE NAME]
Acceptance criteria: [PASTE]
Edge cases:          [PASTE]
Error cases:         [PASTE]

Return a table with:
- Test ID
- Scenario
- Input
- Expected result
- Requirement ID covered

Then provide the test code or test pseudocode.
```

### For refactoring (§13.7)
```
Refactor the code below without changing its approved behavior.

Current behavior that must remain true: [PASTE REQUIREMENTS OR ACCEPTANCE CRITERIA]
Reason for refactoring: [SIMPLIFY / REMOVE DUPLICATION / IMPROVE NAMING / IMPROVE ERROR HANDLING]

Boundaries:
- Do not change public function names unless requested.
- Do not change request or response formats.
- Do not remove validation rules.
- Do not introduce unrelated features.

Tests that must still pass: [PASTE TEST LIST]

Return:
1. Refactored code
2. Explanation of what changed
3. Confirmation of what behavior stayed the same
4. Any risk that still needs manual review
```

---

## Lifecycle control prompts

### Stage gate review (Prompt box 3.4)
```
Act as a spec-driven AI engineering reviewer.

Current stage: [stage name]
Artifact: [paste artifact]

Check whether this artifact is ready for the next stage. Identify missing information,
vague statements, risky assumptions, and the exact corrections needed. Do not move to
implementation.
```

### Implement one controlled task (Prompt box 3.3 / Ch. 16 §16.7)
```
You are implementing one task from the approved spec-to-code pipeline.

Task ID:
Source requirement:
Technical design reference:
Allowed files to change:
Files not allowed to change:
Expected behavior:
Required tests:
Acceptance criteria:

Instructions:
1. Make the smallest safe change.
2. Do not add unrelated features.
3. Explain changed files after implementation.
4. Show how the tests prove the requirement.
```

### Agent self-review before merge (Ch. 15 §15.7)
```
Review your own changes before I accept them.
Explain:
1. Every file you changed.
2. Which requirement each change supports.
3. Which tests prove the change works.
4. Any assumptions you made.
5. Any files you changed that were not listed in the task plan.
```

---

## Project-specific prompts

Three prompts this project needs that the general library does not cover, each aimed at a
failure the specification predicts.

### Guard against the calm wrong screen
```
Review the component below against frontend-component-spec.md's five states.

Component: [PASTE]

For the EMPTY state specifically, answer:
- What exact words appear when there is no data?
- Could a reader mistake that state for good news — no risk, no damage, all clear?
- Does the component distinguish "nothing to show" from "we could not compute this"?

Three screens in this product read as reassuring when blank. Report any wording that
does, before considering the component correct.
```

### Guard against a store rule moved into code
```
Review the change below against database-design.md §3.

Change: [PASTE]

Answer only this: is any rule enforced here in application code that the store could
refuse instead? Name each one, and say what constraint or trigger would enforce it.

Do not rewrite the code. BR-002, BR-003 and BR-004 are enforced by the store on purpose —
a rule that lives only in a service is removed by the first refactor with every test green.
```

### Guard against reasons decoupled from the score
```
Review the scoring implementation below against ADR-005.

Implementation: [PASTE]

Answer:
- Are the reasons produced by the same computation that produces the score, or assembled
  afterwards from the inputs?
- If a factor's weight changed, would the reasons change with it automatically?
- Does every stored score carry at least one reason, refused by the store if not?

A reason generated separately from the score is a plausible sentence that explains
nothing, and it is indistinguishable on screen from one that does.
```

---

## Prompt quality checklist (Ch. 13)

- [ ] Have you provided the approved requirement or specification?
- [ ] Have you limited the task to one clear unit of work?
- [ ] Have you stated what the agent must **not** change?
- [ ] Have you included acceptance criteria or review criteria?
- [ ] Have you requested a clear output format?
- [ ] Have you asked the agent to identify unclear details **before** coding?
- [ ] Have you connected the output back to requirement IDs or spec sections?

**An eighth box belongs on this project: have you named the stop condition?** Five open
questions have answers an agent could invent, and a prompt that does not name the relevant one
is a prompt inviting a guess.

---

## Weak vs. spec-driven prompts (Ch. 1 §1.4)

| Weak prompt | Spec-driven prompt |
|---|---|
| Build a login system. | Using REQ-001 and the authentication technical spec below, implement only the email/password login endpoint. Do not add password reset, social login, or account roles. Generate unit tests for the acceptance criteria before implementation. |
| Make the app better. | Review the task creation workflow against the acceptance criteria. List missing validations first. Then propose only the smallest code changes needed to satisfy the requirement. |
| Fix the bugs. | Use the failing test output and the requirement below to identify the root cause. Explain the mismatch between expected behavior and current behavior before suggesting a patch. |
| Add authentication. | Implement REQ-AUTH-001 only: email-and-password login. Use the existing user model. Do not add social login. Add validation and tests. |
| Fix the dashboard. | Fix TASK-DASH-004: the project count should exclude archived projects. Update the service function and its unit test only. |
| Improve the API. | Update the `POST /projects` contract to require `name` and `ownerId`. Do not change response fields. Add validation errors for missing fields. |

### The three weak prompts this project must never send

`agent-task-list.md` names them; they are repeated here because this is the file somebody reads
when they are about to write a prompt.

| Never send | Send instead |
|---|---|
| "Score the assets." | "Implement A-007 only: the deterministic scoring rule from ADR-005, inside `scoring/`. No training step, no model file, no learned parameter. Reasons produced by the same computation as the score. Do not choose factor weights — Q-025 is open; read them from configuration and fail at startup if absent." |
| "Handle bad data." | "Implement the seven defect rules in `data-and-integration-spec.md` §4, one check each, against a fixture that contains all seven. Six of seven caught looks identical to seven of seven in any summary output — hence UTEST-002 through UTEST-008 as separate ids." |
| "Make the ranking explainable." | "BR-002 is a database check constraint, not a presentation goal: a score with an empty reasons array must be refused by the store. Implement the constraint and UTEST-009, which asserts the STORE refuses it — not that the caller declines to write it." |

---

> Blueprint: blueprints/06-agent/03-prompts/prompt-library.md
