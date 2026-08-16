"""CHG-039 — the browser half uses the shared alphabet, and something fails when it stops.

**The alphabet being right is not the same as the alphabet being used**, and this repository has
already paid for that distinction twice: `frontend/lib/api.ts` held a third copy of
`DISMISSAL_REASON_MAX` that nothing read back, and `String.prototype.trim()` sat in front of
three server-validated fields while a tie test certified that one array of codepoints matched
the store. `test_one_alphabet_decides_what_is_blank_in_every_layer` would still have passed with
`lib/blank.ts` imported by nobody.

So this file asserts the other half: the two components CHG-039 covers **call the shared
helper**, and neither reaches for the language's own idea of blank on the way to the server.

**Two things are deliberately out of scope and are named rather than left to be found.**

- `RecommendationDecision.tsx` and `api/recommendations.py` have the same shape on the decision
  note — `(body.note or "").strip()`, and Python's `str.strip()` removes neither U+200B nor
  U+FEFF, so a `change` or `reject` whose required justification is one zero-width space is
  accepted and written into `decision_records`, where BR-004 means it can never be corrected.
  It belongs to **TASK-004**, which is Done, and CHG-024's rule is that an observation is
  recorded rather than smuggled into a remediation for something else. It is in `review-log.md`
  as an observation against this round.
- `DispatchBoard.tsx`'s `neighbourhood.trim()` is left alone because the asymmetry runs the safe
  way there: `store/dispatch.py` already uses the wide alphabet, so the server refuses more than
  the browser does and the person is shown the `400`. It is still a second definition and it is
  still worth removing; it is not a hole.
"""

import pathlib
import re

import pytest

FRONTEND = pathlib.Path(__file__).resolve().parents[4] / "frontend"

# Comments are stripped before the scan, and only comments. The rule is about what the component
# *calls*; a comment that names `String.prototype.trim()` in order to say why it is not used is
# the documentation this repository asks for, and a scan that forbids explaining a rule teaches
# people to stop explaining it.
LINE_COMMENT = re.compile(r"^\s*(//|\*|/\*).*$", re.MULTILINE)


def code(source: str) -> str:
    return LINE_COMMENT.sub("", source)

# The components that send a person's words toward `decision_records` or the switcher.
# `PlacementForm.tsx` was the original CHG-039 subject; CHG-060 removed it from the product,
# and its role — a note bound for the append-only record — passed to the two triage surfaces,
# so the rule follows the role rather than dying with the file.
COVERED = (
    "views/AssetDetailSheet.tsx",
    "views/FocusMode.tsx",
    "views/ScenarioUploadPanel.tsx",
)


@pytest.mark.parametrize("relative", COVERED)
def test_the_component_trims_with_the_shared_alphabet(relative):
    path = FRONTEND / relative
    assert path.exists(), f"{relative} does not exist, so nothing below means anything"
    source = path.read_text(encoding="utf-8")

    # The haystack: this file has to be the component it claims to be before its silence about
    # `.trim()` is worth reporting. `await insights.` / `await scenarios.` is the fact itself —
    # a call leaving for the server — where "async function" was only its most common spelling,
    # and FocusMode writes the same call as an arrow.
    sends = r"await (insights|scenarios|dispatch|recommendations|placements|auth)\."
    assert re.search(sends, source), f"{relative} sends nothing to the server"
    assert "from '@/lib/blank'" in source, (
        f"{relative} does not import the shared alphabet at all, so tying the alphabet to the "
        "store proves nothing about what this component sends"
    )
    assert "isBlank(" in source or "trimBlank(" in source, (
        f"{relative} imports the shared helper and never calls it"
    )
    assert ".trim()" in code(
        (FRONTEND / "views/DispatchBoard.tsx").read_text(encoding="utf-8")
    ), (
        "the scan below found nothing anywhere, which is what it would do if `code()` stripped "
        "the file rather than its comments — DispatchBoard still calls it and must be found"
    )
    assert ".trim()" not in code(source), (
        f"{relative} still calls String.prototype.trim(). It removes U+FEFF and does not remove "
        "U+200B, the store's alphabet removes both, and the layer that disagrees decides "
        "nothing — it only hides the hole, because this is the strictest of the three"
    )


def test_the_alphabet_has_exactly_one_home_in_the_browser_half():
    """A second copy that agrees today is still a second copy.

    `test_one_alphabet_decides_what_is_blank_in_every_layer` already counts the homes; this is
    the same count from the other direction, and it is here so that deleting that test — or
    narrowing the regex it uses back to `DISMISSAL_BLANK_CODEPOINTS` — does not leave the
    property unasserted.
    """
    homes = [
        path
        for directory in ("lib", "views", "app", "e2e")
        for path in sorted((FRONTEND / directory).rglob("*.ts*"))
        if "BLANK_CODEPOINTS = [" in path.read_text(encoding="utf-8")
    ]

    assert len(homes) == 1, f"the browser's alphabet has {len(homes)} homes, not one: {homes}"
    assert homes[0].name == "blank.ts", (
        f"the alphabet lives in {homes[0].name}. It is a fact about every field a person types "
        "into, and the last time it was filed under one field's name two other fields kept "
        "their own definition"
    )
