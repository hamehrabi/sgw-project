# Release Notes

> Source: Front Matter workspace (`changelog/release-notes.md`).
> What shipped, when, and which requirements it satisfied.

---

## [Unreleased]

### Added
- Nothing. No code has been written.

### Changed
### Fixed
### Security
### Removed

**The specification workspace was completed on 2026-08-15** — eight rounds, 82 blueprints, five
architecture decisions, 47 planned tests. None of that is a release, and it deliberately does
not appear as one above. What shipped is a plan; this file records what runs.

**The first release will be v0.1.0**, and it will be a probe rather than a product: one storm
scenario, on uploaded data, exercised by real operators to find out whether a ranked view
changes a crew decision. Naming it 1.0.0 would claim something the build is not trying to be.

---

## [1.0.0] — YYYY-MM-DD

**This section is the slot for the first release, and it is deliberately empty.** No release
has happened; the heading keeps the shape the next entry takes. Copy the template below into it
rather than editing this heading, and note that the first release will be **v0.1.0**, not
1.0.0 — see the reasoning under *Unreleased*.

**Release goal:**

**Requirements delivered**

| Req ID | Requirement | Test IDs | Traceability status |
|---|---|---|---|

### Added

### Changed

### Fixed

### Security

### Known issues
→ [`maintenance-log.md`](../03-maintenance/maintenance-log.md)

**Migrations applied:**
**Rollback point:** *(tag / commit)*
**Deployed by:** · **Approved by:**

---

## Entry template

```
## [version] — YYYY-MM-DD

Release goal:

Requirements delivered:
| Req ID | Requirement | Test IDs | Status |

### Added
### Changed
### Fixed
### Security
### Removed
### Known issues

Migrations applied:
Rollback point:
Deployed by / Approved by:
Post-release verification:
```

---

## Rules

- Every release entry lists the **requirement IDs** it delivered — that is what makes it
  traceable back to `../docs/traceability.md`.
- A behavior that shipped but is not in a spec is **spec drift** → log it in
  [`spec-drift-checklist.md`](../03-maintenance/spec-drift-checklist.md).
- Record the rollback point with every release, before you need it.

Two more for this project:

- **Every entry names the requirements it did *not* deliver, and why.** Five are already known
  to be undeliverable at the first release: REQ-NF-001 and REQ-NF-004 have no numbers (Q-012),
  REQ-NF-006 has no standard (Q-013), and REQ-NF-007 is partly unanswerable (Q-007). A release
  note that lists only what shipped lets those four disappear quietly.
- **Every entry records the scoring-rule version in force.** A ranking is only reproducible
  against the rule and weights that produced it, and Q-025 makes weight changes expected. A
  release that changed a weight changed the product, whatever else it did.

---

## What the first release note will need to say honestly

The temptation at the first release is to write it as an achievement. The more useful version
answers three questions somebody will ask six months later:

| Question | Where the answer must come from |
|---|---|
| What did it actually do? | The requirement IDs, not the feature names |
| What did it deliberately not do? | The four capabilities deferred in `constraints-and-non-goals.md`, plus the requirements above with no number behind them |
| What was it *for*? | Testing assumptions A2 and A3 as cheaply as possible. If the release note cannot say what the probe learned, the release did not do its job — however well the software works |

---

> Blueprint: blueprints/07-ops/04-release/release-notes.md
