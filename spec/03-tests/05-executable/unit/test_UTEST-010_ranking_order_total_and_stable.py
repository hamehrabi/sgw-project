"""UTEST-010 — REQ-F-002. Defined in `03-tests/02-functional/unit-tests.md`.

Rule under test: ranking order is total and stable.
  normal  — distinct scores order by score
  edge    — equal scores tie-break by oldest condition observation
  failure — the same input producing two different orders across runs → test fails

Also covers TASK-003 done criterion 4: **changing one weight changes the ranking, and no
arithmetic elsewhere needs editing.** That assertion uses a weight set that is not the shipped
one, per `AGENT.md`'s first lesson — every other test here uses ADR-007's numbers, so a scorer
that ignored the config entirely would satisfy all of them.

**None of this asserts that the ranking is right.** It cannot: the weights are uncalibrated
(CHG-014, ADR-007). What it asserts is that the order is a function of the inputs and the
configured numbers, and nothing else.
"""

from conftest import fixture_files


def rank(weights=None, references=None):
    from app.loader.load import load_scenario
    from app.scoring.rank import rank_assets

    result = load_scenario(fixture_files())
    return rank_assets(result.assets, weights=weights, references=references)


def codes(ranked):
    return [item.external_ids[0] for item in ranked]


def test_the_order_is_by_descending_score():
    ranked = [item for item in rank() if item.score is not None]

    scores = [item.score for item in ranked]
    assert scores == sorted(scores, reverse=True)


def test_every_scored_asset_gets_a_distinct_rank_number():
    ranked = [item for item in rank() if item.score is not None]

    positions = [item.rank for item in ranked]
    assert positions == list(range(1, len(positions) + 1))


def test_the_same_input_produces_the_same_order_every_time():
    """A total order, not an order that happens to fall out of dict iteration."""
    assert codes(rank()) == codes(rank()) == codes(rank())


def test_equal_scores_tie_break_by_oldest_condition_observation():
    """The tie-break is a rule, not an accident. Older observation ranks first: it is the
    one nobody has looked at recently, so it is the one most likely to be wrong."""
    from app.scoring.rank import tie_break_key

    older = tie_break_key(condition_observed_at="2019-02-28", external_ids=["A"])
    newer = tie_break_key(condition_observed_at="2026-07-15", external_ids=["B"])

    assert older < newer


def test_a_tie_with_no_observation_dates_still_orders_deterministically():
    """Two assets, both unobserved, must not swap between runs."""
    from app.scoring.rank import tie_break_key

    first = tie_break_key(condition_observed_at=None, external_ids=["ZZ-1"])
    second = tie_break_key(condition_observed_at=None, external_ids=["AA-1"])

    assert second < first


def test_changing_one_weight_changes_the_ranking():
    """Done criterion 4, with a weight set that is not the shipped one.

    Inverting the emphasis — condition dominant, gust negligible — must reorder the list. If
    it does not, the arithmetic is not reading the config, and every other test in this file
    would still pass.
    """
    shipped = codes(rank())
    inverted = codes(
        rank(
            weights={
                "gust_vs_design": 0.05,
                "flood_zone": 0.05,
                "age_vs_service_life": 0.10,
                "condition_decayed": 0.80,
            }
        )
    )

    assert inverted != shipped, "the weights in the config block must drive the arithmetic"


def test_changing_a_design_reference_changes_the_ranking():
    """The same for CHG-014's constants — they are configuration, not constants in code."""
    from app.scoring.references import ASSET_TYPE_REFERENCES, AssetTypeReference

    weaker_lines = dict(ASSET_TYPE_REFERENCES)
    weaker_lines["line"] = AssetTypeReference(40.0, 40.0, "test: lines rated far lower")

    assert codes(rank(references=weaker_lines)) != codes(rank())
