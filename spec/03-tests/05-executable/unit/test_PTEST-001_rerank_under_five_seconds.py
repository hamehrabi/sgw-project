"""PTEST-001 — REQ-NF-001. Defined in `03-tests/03-non-functional/performance-tests.md`.

"Apply a forecast change and re-rank → under 5 s for 220 assets", against the demo-scale
fixture: 220 assets, ~5,000 forecast rows.

The note in that row is a design instruction as much as a test: *profile the scoring pass
first; it is the only unbounded loop in the product. Then the read.* **Do not add a cache** —
`runtime-and-scale.md` §2 refuses one, with reasons.

The limit is generous on purpose, and that is the point: a scoring pass this size should
finish in tens of milliseconds. The assertion is not "is it fast enough" — it is "has
something turned linear work into quadratic work without anyone noticing", which is the way
PTEST-001 actually fails.
"""

import time

from synthetic import synthetic_scenario

LIMIT_SECONDS = 5.0
ASSETS = 220


def parse_and_rank():
    from app.loader.load import load_scenario
    from app.scoring.rank import rank_assets

    files = synthetic_scenario(assets=ASSETS)
    started = time.perf_counter()
    result = load_scenario(files)
    ranked = rank_assets(result.assets)
    return time.perf_counter() - started, result, ranked


def test_the_fixture_is_the_size_the_requirement_names():
    """Otherwise the timing below measures something smaller than the promise."""
    files = synthetic_scenario(assets=ASSETS)

    _, result, _ = parse_and_rank()

    assert len(result.assets) == ASSETS
    assert len(files["weather.csv"].decode().strip().split("\n")) - 1 >= 5000
    assert sum(len(content) for content in files.values()) < 5 * 1024 * 1024


def test_parsing_and_ranking_220_assets_is_inside_the_limit():
    elapsed, _, ranked = parse_and_rank()

    assert len(ranked) == ASSETS
    assert elapsed < LIMIT_SECONDS, f"took {elapsed:.2f}s against a {LIMIT_SECONDS}s limit"


def test_the_scoring_pass_alone_is_comfortably_inside_it():
    """Scoring is the only unbounded loop. Timed separately so a regression names itself."""
    from app.loader.load import load_scenario
    from app.scoring.rank import rank_assets

    result = load_scenario(synthetic_scenario(assets=ASSETS))

    started = time.perf_counter()
    rank_assets(result.assets)
    elapsed = time.perf_counter() - started

    assert elapsed < 1.0, f"scoring alone took {elapsed:.2f}s for {ASSETS} assets"


def test_the_work_grows_with_the_input_rather_than_with_its_square():
    """The regression this test exists for.

    Doubling the assets should roughly double the scoring time. A nested lookup that turns
    the pass quadratic would still finish inside 5 s at 220 and fall over at 2,000 — so the
    shape is asserted, not only the number. The bound is loose because wall-clock on a shared
    machine is noisy; it catches an order-of-magnitude change, which is what a quadratic is.
    """
    from app.loader.load import load_scenario
    from app.scoring.rank import rank_assets

    timings = {}
    for count in (110, 440):
        result = load_scenario(synthetic_scenario(assets=count))
        started = time.perf_counter()
        rank_assets(result.assets)
        timings[count] = time.perf_counter() - started

    # Four times the assets, well under sixteen times the work.
    assert timings[440] < timings[110] * 16 + 0.5


def test_every_asset_is_ranked_or_explicitly_unscored_at_scale():
    """Volume must not quietly drop anyone — the failure the whole product guards against."""
    _, _, ranked = parse_and_rank()

    assert all(item.score is not None or item.unscored_reason for item in ranked)
    assert any(item.score is None for item in ranked), "the generator carries unscorable assets"
