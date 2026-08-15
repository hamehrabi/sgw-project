"""The core subdomain: the risk score, the rank, and the reasons behind them.

This is the one thing the product competes on (`subdomain-map.md`), and the only module whose
output a person is expected to act on during a storm.

WHAT THIS RULE IS, AND WHAT IT IS NOT
=====================================

**The four weights are uncalibrated.** 0.40 / 0.25 / 0.20 / 0.15 have never been validated
against a real storm. The band boundaries at 60 and 30 are round numbers rather than measured
thresholds. The per-type design gusts and service lives in `references.py` are category-level
public figures standing in for a design basis only SGW holds (CHG-014).

**Their source is ADR-007's reasoning, not SGW's data.** ADR-007 argues from the physics of the
decision — what is about to hit the asset matters most, condition data is between two months and
six years old so it should not carry the weight of something measured — and that argument is
worth reading. It is still an argument, not a measurement.

**The exit condition is calibration with SGW's engineers.** Until that happens, no ranking this
module produces is authoritative, and the operator sessions exist to challenge exactly these
numbers. ADR-005 names the risk precisely: a rule encodes today's beliefs, and if the real
driver of failure is something nobody put in the rule, the ranking will be confidently wrong and
the reasons will be confidently wrong in the same way — **which is more persuasive than a wrong
model, not less.**

WHAT THIS MODULE CAN EARN
=========================

Not trustworthiness. **Explainability.** Every rank carries the arithmetic that produced it, so
a person can disagree with a specific factor rather than with a number. That is testable, and it
is what the tests here assert: that reasons are computed and correct — *not* that the ranking is
right. The distinction is the whole design, not a caveat on it.

RULES
=====

- **Score and reasons come out of one computation**, never two (ADR-005). A reason produced
  separately is a plausible sentence that explains nothing, and it is indistinguishable on
  screen from one that does.
- **No training step, model file, or learned parameter**, at any point (ADR-005).
- **Criticality is not risk** (ADR-007). A `critical_facility` asset is never scored higher —
  risk orders the planning list, criticality badges the dispatch queue.
- **An asset that cannot be scored is UNSCORED with its reason** — never omitted from the
  ranking, and never given a low score (FTEST-004). Omitting it is the tidiest code and the
  most dangerous screen in the product: silence must never be readable as safety.
- **Never tune a weight until a ranking looks agreeable.** A rule tuned to look right is
  indistinguishable on screen from one that is right. A ranking that looks wrong is a finding
  for calibration, not a diff.
- No module outside `api/` imports this package, and none of its constants may appear in the
  frontend (FF-002).
"""
