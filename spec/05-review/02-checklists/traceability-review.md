# Traceability Review

> Source: Ch. 30 §30.2 (`05-review/traceability-review.md`), Ch. 10, Appendix F.
> A periodic audit of [`../docs/traceability.md`](../../01-docs/08-traceability/traceability.md).
> Run it before a release, after a batch of agent work, and before any major change.

> Copy this file to `traceability-review-<date>.md` and fill it in, once per audit. **The
> audit cells and the header fields below stay blank in this copy** — an audit that has not
> happened has no reviewer, no date, and no verdicts, and writing plausible ones is worse
> than leaving them empty.

**Review date:**
**Reviewer:**
**Scope reviewed:** *(release / feature / sprint)*

---

## 1. Forward trace — every requirement leads somewhere

| Req ID | Has design decision? | Has task? | Has test? | Has code link? | Reviewed? | Gap |
|---|---|---|---|---|---|---|
| REQ-001 | ✔ / ✘ | ✔ / ✘ | ✔ / ✘ | ✔ / ✘ | ✔ / ✘ | |
| REQ-002 | | | | | | |

## 2. Backward trace — every change came from somewhere

| Changed file / module | Task ID | Requirement | Approved? | Action |
|---|---|---|---|---|
| | | | Yes / **No** | Keep / Document + approve / **Remove** |

> **Code with no requirement is suspicious until approved** (Ch. 10 §10.8).

---

## 3. Gap findings

| Gap type | Count | Items | Action assigned to | Due |
|---|---|---|---|---|
| Requirement without design decision | | | | |
| Design without task | | | | |
| Task without test | | | | |
| Test without code link | | | | |
| **Code without requirement** | | | | |
| Released behavior not in spec | | | | |

---

## 4. Checklist (Appendix F)

- [ ] Every **Must** requirement has at least one task.
- [ ] Every **Must** requirement has at least one test.
- [ ] Every security rule maps to validation or authorization code.
- [ ] Every released feature maps back to a PRD requirement.
- [ ] Every changed behavior is reflected in updated specs.
- [ ] Every blank matrix cell has been reviewed and explained.
- [ ] Any code without a requirement has been removed, documented, or approved.

---

## 5. Outcome

- [ ] **Chain complete** — safe to proceed.
- [ ] **Gaps logged** — tasks created, non-blocking.
- [ ] **Blocked** — release cannot proceed until listed gaps close.

**Follow-up tasks created:**

---

> **Traceability rule (Ch. 30 §30.6):** every accepted code change should point back to a
> requirement and a test. Every requirement should point forward to at least one task and
> one reviewable proof.

---

## What the first audit will find, before it runs

The matrix in `01-docs/08-traceability/traceability.md` was written this round and already
reports its own gaps. An audit run today would find these, and none of them requires waiting:

| Gap type | Already known | Why it is not a surprise |
|---|---|---|
| Requirement without design decision | **1 — REQ-NF-006 (accessibility)** | Q-013 was never answered, so there is no standard to design or test against. It is a requirement in name only, and the honest choices are to answer Q-013 or to move it to non-goals. |
| Design without task | 0 | Every ADR has at least one task. |
| Task without test | 0 | Every task cites its test ids. |
| Test without code link | **47** | No code exists. This is the whole workspace's state, not a finding. |
| Code without requirement | 0 | No code exists to be unapproved — the one gap type that is currently impossible. |
| Released behaviour not in spec | 0 | Nothing has shipped. |

**Three requirements can never gain a code link, and that is correct rather than a gap.**
REQ-R-003 and BR-005 are satisfied by the *absence* of code — no outbound path exists to a
control system — and STEST-010 asserts the absence. REQ-NF-005 is guarded by FF-002, because a
test cannot usefully observe an import boundary. An auditor who marks those three as gaps has
misread the matrix; the matrix says so in its own gap analysis.

**The backward trace is the pass to run hardest here.** An AI agent builds every task (CON-008),
and the one thing a green test suite can never tell you is that a file appeared with no
requirement behind it. Run §2 before §1, on the changed-file list, before reading any code.

---

> Blueprint: blueprints/05-review/02-checklists/traceability-review.md
