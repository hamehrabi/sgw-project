# Requirements Traceability Matrix (RTM)

> Source: Ch. 10 + Appendix F.
> Traceability is a **chain of evidence**. A requirement is a promise; traceability is how
> you prove the promise did not disappear while the software was being built.

Keep this file next to the requirements. If it lives in another tool, you will not
maintain it.

---

## The matrix

| Req ID | Requirement | Design / Spec section | Task ID | Test ID | Code link | Review status |
|---|---|---|---|---|---|---|
| REQ-F-001 [built: `backend/app/loader/`, `frontend/views/AssetTable.tsx`] | Join asset records into one view per asset, with source and age on every value | Tech spec §2, `database-design.md` §1, §3 | TASK-002 | ATEST-001, ATEST-002, UTEST-002…008, ITEST-001, FTEST-001…003 | — | Draft |
| REQ-F-002 | Every asset ranked by risk in one list | ADR-005, `ai-boundary-spec.md` §1 | TASK-003 | ATEST-003, UTEST-010, PTEST-001, EVAL-001 | — | Draft |
| REQ-F-003 | Reasons behind each rank, in plain words | ADR-005, BR-002 | TASK-003 | ATEST-004, UTEST-009, FTEST-004 | — | Draft |
| REQ-F-004 | Re-rank on a forecast change, without restarting the plan | `database-design.md` §3 (revision key) | TASK-006 | ATEST-005, ITEST-004 | — | Draft |
| REQ-F-005 | Record a crew placement against the ranking | Product spec §10 | TASK-007 | E2E-001, FTEST-005 | — | Draft |
| REQ-F-006 | Accept, change, or reject every recommendation | BR-001, API spec (decision endpoint) | TASK-004 | ATEST-006, ITEST-002, FTEST-005, FTEST-006 | — | Draft |
| REQ-F-007 | One shared list of damage and repair jobs | `database-design.md` §1 | TASK-005 | ATEST-007, ITEST-003, PTEST-002 | — | Draft |
| REQ-F-008 | Dismiss a false alarm in one action | `database-design.md` §3 (dismissal check) | TASK-008 | UTEST-011 | — | Draft |
| REQ-F-009 | Record every recommendation and every decision | BR-004, ADR-004 | TASK-004 | ATEST-008, ITEST-002, STEST-008 | — | Draft |
| REQ-F-010 | An admin loads a prepared storm scenario | CHG-001, CHG-012, `data-and-integration-spec.md` §3 | TASK-002, TASK-009 | ATEST-009, ITEST-005, E2E-002, STEST-005…006, FTEST-001, FTEST-008 | `backend/app/api/scenarios.py`, `backend/app/api/uploads.py`, `backend/app/store/scenarios.py`, `frontend/views/ScenarioUploadPanel.tsx` | **Built** — E2E-002 owed (browser) |
| REQ-NF-001 | Re-rank 220 assets under 5 s; page under 2 s; reasons under 300 ms | Tech spec §8 | TASK-003, TASK-005 | PTEST-001, PTEST-002 | — | Draft |
| REQ-NF-002 | Signed-in access, per-role views, every access recorded | ADR-003, SEC-A/SEC-Z, CHG-008, CHG-009 | TASK-001 | UTEST-001, STEST-001…004 | `backend/app/api/auth.py`, `backend/app/api/middleware.py`, `backend/app/store/sessions.py`, `backend/app/store/users.py` | **Built — in review** |
| REQ-NF-003 | **(a)** state the data's age always; **(b)** name a lost file without degrading a correct screen (CHG-013) | Reliability spec §3, CHG-013 | TASK-002 | ATEST-010, FTEST-002, FTEST-003 | `backend/app/api/views.py`, `frontend/views/StalenessBanner.tsx`, `frontend/views/ScenarioIntegrityNotice.tsx` | **Built** |
| REQ-NF-004 | Any critical action in two actions or fewer | `frontend-component-spec.md` | TASK-003, TASK-005 | E2E-001 | — | Draft |
| REQ-NF-005 | Scoring separable from the views that show it | ADR-001 | TASK-003 | — (FF-002) | — | Draft |
| REQ-NF-006 | Accessibility — WCAG 2.1 AA | `frontend-component-spec.md` (keyboard, colour-never-alone) | TASK-003, TASK-008 | ATEST-011 | — | Draft |
| REQ-NF-007 | Neighbourhood-level display; the CON-003 list is never stored | Security spec §4 | TASK-002, TASK-005 | UTEST-012, STEST-009 | — | Draft |
| REQ-R-001 | A user reads everything but loads no scenario | SEC-Z-001, SEC-Z-002 | TASK-001, TASK-002 | ATEST-009, STEST-005 | `backend/app/store/migrations/001_users_and_sessions.up.sql` (the role check only) | **Partly built** — the two roles exist and the database refuses a third. The *allow-list per action* half arrives with the first endpoint that has one (TASK-002). |
| REQ-R-002 | No role may alter a decision record | ADR-004, SEC-Z-004 | TASK-004 | STEST-008 | — | Draft |
| REQ-R-003 | No role may command a control system | BR-005, SEC-Z-005 | — (structural) | STEST-010 | — | Draft |
| BR-001 | The system never acts; a person decides | ADR-005, `ai-boundary-spec.md` §6 | TASK-004 | ATEST-006, ITEST-002 | — | Draft |
| BR-002 | A rank is never shown without its reasons | ADR-005, `database-design.md` §3 (check constraint) | TASK-003 | ATEST-004, UTEST-009, FTEST-004, EVAL-001 | — | Draft |
| BR-003 | Every value shows its source and age | `database-design.md` §3 (check constraint) | TASK-002 | ATEST-001, UTEST-003, UTEST-004 | — | Draft |
| BR-004 | The decision record is append-only | **ADR-004** (triggers) | TASK-004 | ATEST-008, ITEST-002, STEST-008 | — | Draft |
| BR-005 | Prepared files only; no connection in either direction | ADR-002, CON-005 | — (structural) | STEST-010 | — | Draft |

**Status values:** Draft · Ready · In review · Approved · Needs update · Released

Every `Code link` is empty because no code exists. That column is the honest measure of how far
this workspace is from a product: twenty-five promises, zero implementations.

---

## The chain (Ch. 10 §10.1)

| Item | Simple question it answers |
|---|---|
| Requirement | What must the system do? |
| Design decision | How will the system support it? |
| Task | What work must be completed? |
| Test | How will you verify it? |
| Code reference | Where is it implemented? |
| Review status | Is the chain complete and approved? |

### Linking pattern (Ch. 10 §10.3)

```
Requirement ID: REQ-AUTH-001
Requirement:    A registered user must be able to sign in with an email and password.

Design Decision ID: DD-AUTH-001
Decision: Use server-side authentication with hashed passwords and a short-lived
          session token.
```

```
Test ID:         TEST-AUTH-02
Test:            Valid credentials return a session token.
Code link:       auth/login.py -> login_user()
Supporting code: auth/passwords.py -> verify_password_hash()
Status:          Passing
```

---

## Gap analysis (Ch. 10 §10.8)

A **gap is any missing link**. Blank cells are the point of this document.

| Gap found | What it may mean | What you should do |
|---|---|---|
| Requirement has no design link. | The implementation approach is unclear. | Write or confirm the design decision. |
| Design has no task. | The work has not been planned. | Create a small agent-friendly task. |
| Task has no test. | You cannot verify completion. | Write at least one test case. |
| Test has no code link. | Implementation may be missing or hard to locate. | Add file/function reference after implementation. |
| **Code has no requirement.** | The agent may have added unapproved behavior. | Remove it, or document and approve it. |

> Treat code with no requirement as **suspicious until approved**.

### The gaps this matrix shows today

| Gap | What it means | Action |
|---|---|---|
| ~~REQ-NF-006 has no design link, no task, and no test.~~ | **Closed by CHG-006.** Q-013 named WCAG 2.1 AA, so accessibility now has a standard, two design rules in `frontend-component-spec.md`, two tasks, and ATEST-011. It was the one row on this matrix that could not be closed by building anything. | Done. |
| ~~REQ-NF-001 and REQ-NF-004's tests are Blocked.~~ | **Closed by CHG-006.** Q-012 gave real numbers and Q-017 gave a dataset to run them against. *Under 5 s* is measurable; *under one minute* was not, because the volume was missing. | Done — PTEST-001 and PTEST-002 are Planned. |
| ~~REQ-NF-007 is partly unanswerable.~~ | **Closed by CHG-006.** CON-003 now enumerates exactly what must never be stored. | Done. |
| REQ-R-003 and BR-005 have **no task**. | Correct, and worth stating: they are satisfied by the absence of code, not by any code. | Nothing to build. STEST-010 asserts the absence, which is the only way an absence can be proven. |
| REQ-NF-005 has **no test**. | Correct: an import boundary is guarded by FF-002, not by a test. | Nothing to add. Wiring FF-002 is TASK-010. |
| ~~Every row has an empty **Code link**.~~ | **Two rows now carry one.** TASK-001 is built: REQ-NF-002 in full, REQ-R-001 in the half a schema can hold. Every other row is still empty, which remains the workspace's true state rather than a finding. | Build TASK-002. |

**Two requirements cannot be closed by building anything**, and that is the most useful thing
this matrix still says. REQ-R-003 and BR-005 are proven by structural *absence* — no outbound
path exists to a control system — and STEST-010 asserts it. Three other gaps closed in CHG-006,
and every one of them closed by somebody answering a question rather than by writing code.

---

## AI-specific risks this catches (Ch. 10 §10.2)

| AI risk | Traceability response |
|---|---|
| The agent builds a related but wrong feature. | Check whether the task links back to the exact requirement. |
| The agent skips an edge case. | Check whether the acceptance criteria produced a test case. |
| Code passes basic tests but breaks a rule. | Check whether business rules appear in the test links. |
| The implementation changes architecture silently. | Check whether the code still follows the design decision. |

> **AI control point:** never ask an agent to "just build the feature" when the
> requirement has not been linked to a task and a test.

CON-008 now says an AI agent builds this workspace, one task at a time. That makes the fourth
row the live risk: ADR-001 to ADR-005 each carry a rule the agent must follow, and nothing
except FF-001, FF-002 and review notices when one is quietly dropped.

---

## Traceability review checklist (Ch. 10 + Appendix F)

- [x] Every important requirement has a unique ID.
- [x] Every Must requirement has at least one task.
- [x] Every Must requirement has at least one test.
- [ ] Every requirement links to at least one design decision or implementation approach.
- [x] Every design decision links to one or more small tasks.
- [ ] Every implemented feature has a code link.
- [x] Every security rule maps to validation or authorization code.
- [ ] Every released feature maps back to a PRD requirement.
- [ ] Any code without a requirement has been removed, documented, or approved.
- [x] Any blank matrix cell has been reviewed before moving forward.
- [ ] Every changed behavior is reflected in updated specs.

Five boxes are unticked. **One is a real gap** — REQ-NF-006 has no design link (Q-013). The other
four are unreachable rather than unmet: nothing is implemented, nothing is released, no code
exists to be unapproved, and no behaviour has changed yet. They become meaningful the day
TASK-001 produces a file.

---

> Blueprint: blueprints/01-docs/08-traceability/traceability.md
