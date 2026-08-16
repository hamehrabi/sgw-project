"""Matching one physical asset across the differing codes its source systems give it.

Defect 1. `SS-1042` in one system and `TX-4471` in another are one substation, and the
prepared files have no shared key that says so.

**The join key is an implementation decision, not a specification one.** §4 requires only
that what can be matched is matched, that the rest is flagged `needs_review` and surfaced,
and that nothing is ever merged on a guess. The rule below is the narrowest one that
satisfies it:

    same type  +  same position to 4 decimal places (~11 m)  +  same normalised name

Position and type alone are a *near* match — two pumps can share a site — so a name that
disagrees **withholds** the merge rather than completing it.

**The two errors do not cost the same, and that asymmetry is the whole design.**

- A **wrong merge** deletes an asset from the ranking. Two records become one, the second
  asset is never scored, never ranked, and never appears on the planning list — it is gone
  from the one thing this product exists to produce, silently, with every screen looking
  complete. Nothing downstream can detect it.
- A **wrong split** adds a row to the review queue. A person looks at two records, sees they
  are the same pump, and says so. It costs about ten seconds and it is self-correcting,
  because the queue exists to be read.

One failure is invisible and unrecoverable; the other is visible and cheap. So the tie goes
to *not merging* — always, and even when a merge looks very likely — because being wrong in
the cheap direction is worth being wrong more often.

This is the same reasoning ADR-007 applies to the score itself, one layer down. There, a
factor measured between two months and six years ago is discounted rather than trusted,
because a confidently wrong ranking is more dangerous than a hedged one. Here, an identity
inferred from a coordinate match is refused rather than assumed, for the same reason: the
cost of the two mistakes is not symmetric, so the threshold should not sit in the middle.
"""

import re

from app.loader.records import LoadedAsset

COORDINATE_PRECISION = 4


def normalise_name(name: str) -> str:
    """Case, punctuation and spacing are formatting; they are not identity."""
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def site_key(asset: LoadedAsset) -> tuple:
    return (
        asset.type,
        round(asset.lat, COORDINATE_PRECISION),
        round(asset.lon, COORDINATE_PRECISION),
    )


def merge_by_site_and_name(
    assets: list[LoadedAsset],
) -> tuple[list[LoadedAsset], list[dict]]:
    """Return one record per physical asset, flagging what could not be resolved —
    **and both sides of everything withheld** (CHG-048).

    The second list is the review queue's content: `needs_review` on an asset says a
    person is owed a look, and used to say nothing about what they were owed a look AT.
    Each entry pairs one withheld record with the site-mate it was nearly merged with, in
    the shape the drawer renders. Confidence is a word and never a percentage: the rule is
    a position threshold and a name comparison, and dressing that as 87% would invent a
    precision the arithmetic does not have.
    """
    by_site: dict[tuple, list[LoadedAsset]] = {}
    for asset in assets:
        by_site.setdefault(site_key(asset), []).append(asset)

    resolved: list[LoadedAsset] = []
    withheld: list[dict] = []
    for candidates in by_site.values():
        if len(candidates) == 1:
            resolved.append(candidates[0])
            continue

        by_name: dict[str, list[LoadedAsset]] = {}
        for candidate in candidates:
            by_name.setdefault(normalise_name(candidate.name), []).append(candidate)

        # One site, one name: the same asset under two codes. Merge, keeping every code.
        if len(by_name) == 1:
            resolved.append(_merged(candidates))
            continue

        # One site, names that disagree. A near match below the bar: surface every record
        # to a person rather than choosing between them.
        anchor = candidates[0]
        for candidate in candidates:
            candidate.match_status = "needs_review"
            resolved.append(candidate)
            if candidate is not anchor:
                withheld.append(
                    {
                        # Keyed to the anchor's first code: save_loaded_scenario resolves
                        # this to the stored asset id, so the queue row belongs to a row
                        # a reviewer can act on.
                        "anchor_code": anchor.external_ids[0],
                        "map_record": _card(anchor),
                        "candidate_record": _card(candidate),
                        # Same type AND same position to ~11 m — that is what put the
                        # two at one site. "high" is the only grade this rule can honestly
                        # give; a weaker rule would need a weaker word, not a number.
                        "confidence": "high",
                    }
                )

    return resolved, withheld


def _card(asset: LoadedAsset) -> dict:
    """One side of a comparison, in the fields the drawer shows. No coordinate leaves
    here beyond what the registry itself carries."""
    return {
        "id": asset.external_ids[0],
        "name": asset.name,
        "type": asset.type,
        "condition": asset.condition,
        "condition_observed_at": asset.condition_observed_at,
        "install_year": asset.install_year,
    }


def _merged(candidates: list[LoadedAsset]) -> LoadedAsset:
    """Keep the most recently observed condition, and every external code."""
    dated = [c for c in candidates if c.condition_observed_at]
    primary = max(dated, key=lambda c: c.condition_observed_at) if dated else candidates[0]

    primary.external_ids = sorted({code for c in candidates for code in c.external_ids})
    primary.match_status = "matched"
    return primary
