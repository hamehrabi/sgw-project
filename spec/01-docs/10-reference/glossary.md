# Glossary of Key Terms

> Source: Appendix R. Practical definitions as used throughout the book.

| Term | Definition |
|---|---|
| **Acceptance criteria** | Clear conditions that prove a requirement has been met. |
| **Agent** | An AI system or assistant that performs a defined engineering task using context and instructions. |
| **Architecture decision record (ADR)** | A short document explaining an important technical decision and its trade-offs. |
| **Context pack** | A focused package of project information given to an AI agent for a specific task. |
| **Continuous integration** | A workflow that checks code changes with automated tests and validation. |
| **Database migration** | A controlled change to the database structure or data. |
| **Deployment** | The process of releasing software into an environment where users or systems can use it. |
| **Engineering intent** | The early statement of why a project exists and what outcome it should create. |
| **Integration test** | A test that checks whether connected components work together. |
| **Non-functional requirement** | A requirement about quality attributes such as security, reliability, performance, or usability. |
| **Product requirements document (PRD)** | A document describing what the product or feature must do and why it matters. |
| **Refactoring** | Improving code structure without changing intended behavior. |
| **Requirements traceability matrix (RTM)** | A table connecting requirements to specs, tasks, tests, code, and review evidence. |
| **Rollback** | A planned way to return to a safer previous state after a failed release. |
| **Spec drift** | The gap that appears when actual software behavior no longer matches the written specification. |
| **Technical specification** | A document explaining how approved product requirements will be designed and implemented. |
| **Unit test** | A test for one small piece of behavior, usually a function or class. |
| **Version control** | A disciplined way to track, review, and recover changes to files over time. |

---

## Additional terms used in this template

| Term | Definition |
|---|---|
| **Acceptance test** | A test written from the user or business view that proves a requirement works end to end. |
| **Business rule** | A policy decision the software must enforce, written separately from implementation. |
| **Constraint** | A fixed condition that limits the solution (budget, time, technology, compliance, device). |
| **Edge case** | An unusual but possible situation the system must still handle correctly. |
| **Failure condition** | A situation where the system cannot complete the request safely. |
| **Idempotency** | The property that repeating an operation produces no additional harmful effect — a prerequisite for safe retries. |
| **Modular monolith** | One deployable application organized internally into clear modules with respected boundaries. |
| **Non-goal** | Something the team deliberately chooses not to build in this release. |
| **Observability** | The ability to use logs, metrics, and traces together to understand *why* a system behaved as it did. |
| **Quality gate** | A condition that must be true before work is allowed to move to the next stage. |
| **RBAC** | Role-based access control: permissions defined per role instead of per user. |
| **Scope creep** | New features entering the work without being approved in the specification. |
| **Shallow test** | A test that confirms something happened without proving the behavior was correct. |
| **Smoke test** | A short check of core flows run immediately after deployment. |
| **Stage gate** | A checkpoint between lifecycle stages that prevents unfinished work from moving forward. |
| **Vibe coding** | Prompting an AI repeatedly until the result "feels right" — useful for exploration, unsafe for production. |

---

## Terms specific to this project

Domain words a reader will meet in these documents and nowhere in the book.

| Term | Definition |
|---|---|
| **Scenario** | One prepared storm, uploaded by an admin as a set of files. Everything else in the data model belongs to exactly one scenario, and two scenarios never blend into one ranking. |
| **Forecast revision** | A numbered version of a scenario's weather forecast. Applying a change writes revision *n+1* and never overwrites *n*, so the ranking a decision was made against stays retrievable. |
| **Joined asset view** | One record per substation, line, plant or pump, assembled from files that use different codes for the same asset — with the source and age of every value visible. |
| **Reasons** | The plain-words explanation shown beside a risk rank. Not a diagnostic: BR-002 makes them part of the contract, and a rank cannot be stored without at least one. |
| **UNSCORED** | How an asset appears when it cannot be scored. It stays in the list, with the reason. It is never omitted and never given a low score — the difference between an honest gap and a screen that reads as safety. |
| **Decision record** | The append-only log of every recommendation the system made and every accept, change or reject a person made. Enforced by database trigger (ADR-004), not by application code. |
| **Prepared data** | Files standing in for four systems that are not connected. Deliberately carries the seven measured defects, so the design is proven against dirty data rather than clean data. |
| **The seven defects** | Seven data problems measured in real public files of the same kinds, injected into the test fixture on purpose. Listed in `data-and-integration-spec.md` §4. |
| **One-way wall** | The property that no code path exists by which this platform could send a command to a system controlling the grid or the water network. Asserted structurally (STEST-010), not as a refusal. |
| **The quality floor** | The release gate on the ranking: the assets that actually failed appear in the top decile. Provisional until SGW supplies per-asset failure history. |
| **A1, A2, A3** | The three unproven guesses from the source PRD that version one exists to test: can the data be reached; does a combined ranked view change the crew decision; will operators act on a computer's ranking. |
| **Core subdomain** | The ranked risk list with its reasons. The one thing this product competes on, and the only area given full spec depth and full test depth. |

**Two of these are worth reading twice.** *UNSCORED* names the most dangerous failure in the
product, and *reasons* names the thing that stops being optional the moment BR-002 is written as
a database constraint rather than a hope. If a new reader learns only two words from this table,
those are the two.

---

> Blueprint: blueprints/01-docs/10-reference/glossary.md
