# Recommended Tools and Resources

> Source: Appendix S + Front Matter ("Recommended Tools and Development Environment").
> The workflow does not depend on a specific external platform. **The categories matter
> more than any single brand name.**

---

## Tool categories (Appendix S)

| Category | What you need from it | Examples or options |
|---|---|---|
| Writing and specs | A place to create PRDs, technical specs, templates, decision records. | Word processor, Markdown editor, internal wiki, shared document folder. |
| Version control | Track changes, review work, recover older versions. | Local Git, GitHub-compatible platforms, internal VCS. |
| AI coding assistant | Work from project context, generate code, explain changes, help review tests. | Chat-based assistant, IDE assistant, agentic coding tool. |
| Code editor | Search, formatting, terminal access, project navigation. | Any modern IDE or code editor. |
| Test runner | Repeatably run unit, integration, e2e, security, regression tests. | Language-specific frameworks and CLI test tools. |
| Container runtime | Package and run applications consistently across environments. | Docker-compatible tooling or platform-native containers. |
| Database tooling | Local development, migrations, backup, restore, inspection. | Database clients, migration scripts, admin consoles. |
| CI/CD | Repeatable checks, builds, tests, deployment, rollback. | Platform pipeline, local scripts, internal build system. |
| Monitoring and logs | Visibility into errors, performance, usage, production health. | Logging system, metrics dashboard, error tracker, uptime checks. |
| Security review | Dependency checks, secret detection, access review, validation testing. | Static analysis, dependency scanner, secrets scanner, manual checklist. |

---

## Development environment (Front Matter)

| Tool area | Recommended choice | Purpose |
|---|---|---|
| Text and specs | Any document or Markdown editor | Write intent documents, PRDs, technical specs, checklists, review notes. |
| Code editor | Any modern code editor | Edit source, inspect generated code, run tests, review changes. |
| AI assistant | Any AI coding or chat assistant | Generate drafts, propose tests, explain errors, assist implementation. |
| Version control | Local Git or another change-tracking method | Track specs, tasks, tests, code changes, review decisions. |
| Runtime | Python and/or Node.js, depending on the project | Run examples, simple APIs, tests, scripts. |
| Database | SQLite for learning; PostgreSQL for production-style thinking | Model application data; practice migration planning. |
| API testing | Browser, terminal, or API testing client | Check endpoints, payloads, errors, authentication behavior. |
| Containerization | Docker-compatible tooling (optional) | Package and test deployment behavior repeatably. |

> **No external repository required.** The workflow can be practiced entirely locally.
> GitHub or another hosting service is an optional collaboration layer.

---

## What this project needs from each category

Chosen under CON-001 (no technology mandated), CON-006 (no paid services), ADR-001 (modular
monolith), ADR-002 (embedded relational store), and a container on a cloud VM with local, test
and production environments.

| Category | What this project needs | Constrained by |
|---|---|---|
| Writing and specs | Markdown in the repository, beside the code. The agent reads the specification directly, so a second system would drift from the thing the agent actually obeys. | CON-008 — an agent builds this |
| Version control | Any change-tracking method. Branch per task id; commit messages carry the `TASK-###` and the requirement it serves. | — |
| AI coding assistant | An agentic tool for bounded tasks, and a chat assistant for specification and review. **Never an agent with file access for specification work** — `01-docs/` is an input to every task, never an output. | CON-008 |
| Code editor | No constraint. | — |
| Test runner | One command across all levels, with test ids in file names so a failure names the requirement that broke. | `executable-tests.md` |
| Container runtime | Required. The deployment target is a container on a cloud VM, and the container is what makes local, test and production the same shape. | Round 8 Q1 |
| Database tooling | Whatever handles an embedded relational file: migrations up and down, backup by file copy, and a client that can inspect triggers. **The trigger check is not optional** — ADR-004 puts BR-004's only enforcement there. | ADR-002, ADR-004 |
| CI/CD | A script that fails the build, run in the test environment. It must run the suite **and** the six fitness functions. CON-006 rules out a paid platform; the gate is the script, not the platform. | CON-006, TASK-010 |
| Monitoring and logs | Structured logs to stdout with a request id on every line, plus error alerts. Nothing more — Round 8 chose that appetite deliberately. | Round 8 Q3 |
| Security review | A secrets scanner in the gate, plus the manual checklist. A dependency scanner is worth having and is not yet a decision. | CON-006 |

**The category this project cannot compromise on is database tooling**, which is not where most
projects would put the emphasis. Three of the five business rules are enforced by the store —
BR-002 and BR-003 as check constraints, BR-004 as a pair of triggers — so a migration tool that
cannot show you whether a trigger still exists is a tool that cannot show you whether the audit
trail is still protected.

---

## Choosing an AI assistant by stage (Ch. 4 §4.1)

| Assistant type | Best use | Watch out for |
|---|---|---|
| Chat assistant | Explaining concepts, drafting requirements, improving prompts, reviewing small snippets. | May not understand your full project unless you paste the right context. |
| Editor assistant | Suggesting code inside your editor; small implementation tasks. | Can produce local improvements while missing larger design rules. |
| Agentic coding assistant | Planning and changing multiple files under instruction. | Can overreach if task boundaries are weak. |
| Testing assistant | Drafting unit, integration, and failure test cases from requirements. | May generate shallow tests unless acceptance criteria are clear. |

> **Selection rule:** choose the *simplest* assistant that can help with the current stage.
> You do not need an agentic tool for every task — a normal chat assistant is often safer
> for requirements and review.

The last row is the live risk here. `test-specification.md` names three specific ways a test on
this project gets weakened into passing without proving anything, and every one of them is what
a testing assistant produces when handed a requirement without its acceptance criterion.

---

## Tool selection checklist (Appendix S)

- [x] The tool supports your workflow without forcing unnecessary complexity.
- [x] The team can use it consistently.
- [x] It supports review, traceability, and rollback where needed.
- [x] It does not require exposing private data unnecessarily.
- [x] It fits the project's budget, skill level, and deployment environment.

The fourth box carries more weight here than usual and is worth stating rather than ticking
silently: this workspace and its future data describe critical infrastructure. Any tool that
sends source, logs, or stack traces off-site is a decision with a security consequence, not a
convenience — which is why error tracking was offered in Round 6 and declined.

---

> **Final note (Appendix S):** tools will change, but the engineering discipline remains
> the same. Start with clear intent, write testable specs, connect specs to tasks and
> tests, review AI output carefully, deploy with rollback plans, and keep the specs alive
> after release.

---

> Blueprint: blueprints/01-docs/10-reference/recommended-tools.md
