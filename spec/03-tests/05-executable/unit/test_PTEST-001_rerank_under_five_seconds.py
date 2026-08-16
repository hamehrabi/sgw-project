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

**This file used to measure a proxy for the operation it names, and the review that blocked
TASK-006 said so.** `TASK-006.md` re-runs PTEST-001 because *"the re-rank limit it measures is
this task's operation"* — and it was not: every case below timed `load_scenario` plus
`rank_assets` **in process**, touching neither `POST /scenarios/{id}/forecast-revisions`, nor
`score_revision`'s join over `scenario_forecast_cells`, nor `save_revision`'s 220-row
`executemany` and compare-and-swap of the scenario pointer. REQ-NF-001's five-second budget was
being measured against a path that excluded every database statement the operation performs. The
in-process cases stay, because they are what makes a regression *name itself* — the endpoint case
tells you the promise is broken and these tell you where. The endpoint case is what the
requirement is actually about.
"""

import time

from conftest import build_application, sign_in
from fastapi.testclient import TestClient
from synthetic import synthetic_scenario

LIMIT_SECONDS = 5.0
ASSETS = 220
PASSWORD = "correct-horse-battery-staple"


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


# --- The operation the requirement actually names -------------------------------------------


def demo_scale_storm(tmp_path, monkeypatch, *, assets: int = ASSETS, name: str = "ptest"):
    """A loaded storm at demo scale, through the endpoint, on its own database file.

    The two size limits are raised to the shipped values because the suite's defaults are
    deliberately tiny (4 KB / 16 KB, so the refusals can be tested without an 8 MB fixture) and
    a demo-scale storm is the thing being measured. They are still read from configuration, so
    this is not a hard-coded limit sneaking in the side door.
    """
    from app.store import users

    application = build_application(
        monkeypatch,
        tmp_path / f"{name}.db",
        SCENARIO_MAX_FILE_BYTES=8_388_608,
        SCENARIO_MAX_TOTAL_BYTES=10_485_760,
    )
    users.create_user(
        application.state.db,
        name="Ops Manager",
        email="admin@sgw.example",
        password=PASSWORD,
        role="admin",
    )
    client = TestClient(application)
    sign_in(client, "admin@sgw.example", PASSWORD)
    created = client.post(
        "/api/v1/scenarios",
        data={"name": "Demo scale", "source_note": "generated"},
        files=[
            ("files", (filename, content, "text/csv"))
            for filename, content in synthetic_scenario(assets=assets).items()
        ],
    )
    assert created.status_code == 201, created.text
    return application, client, created.json()["scenario_id"]


def statements_during(connection, work) -> list[str]:
    """Every SQL statement the connection executes while `work` runs. PTEST-002's technique."""
    seen: list[str] = []
    connection.set_trace_callback(seen.append)
    try:
        work()
    finally:
        connection.set_trace_callback(None)
    # Prove the haystack is a haystack before anyone reports no needle: `0 == 0` passes.
    assert seen, "no SQL was captured; the trace callback is not firing"
    return seen


def test_applying_a_forecast_change_through_the_endpoint_is_inside_the_limit(
    tmp_path, monkeypatch
):
    """REQ-NF-001, measured on the operation it names: *apply a forecast change and re-rank*.

    Everything the in-process cases above skip is inside this measurement — the join over
    `scenario_forecast_cells` for one revision, the whole scoring pass, the 220-row
    `executemany`, the compare-and-swap of the scenario pointer, and the transaction around the
    last two. If a future change makes the re-rank issue one statement per asset, every case
    above stays green and this one does not.
    """
    application, client, scenario_id = demo_scale_storm(tmp_path, monkeypatch)
    # The haystack: this storm really does carry a further forecast, so what is timed below is a
    # re-rank rather than a 409 returned in a microsecond.
    scenario = client.get(f"/api/v1/scenarios/{scenario_id}").json()
    assert scenario["next_forecast_revision"] == 1
    assert len(scenario["forecast_revisions"]) > 2, "the generated storm carries one forecast"

    started = time.perf_counter()
    applied = client.post(f"/api/v1/scenarios/{scenario_id}/forecast-revisions")
    elapsed = time.perf_counter() - started

    assert applied.status_code == 201, applied.text
    body = applied.json()
    assert body["forecast_revision"] == 1
    # Every asset re-ranked, nobody dropped: a fast re-rank that lost half the storm would pass
    # a timing assertion and fail the product.
    assert body["ranked"] + body["unscored"] == ASSETS
    assert body["ranked"] > 0
    assert elapsed < LIMIT_SECONDS, (
        f"the re-rank endpoint took {elapsed:.2f}s against a {LIMIT_SECONDS}s limit"
    )
    application.state.db.close()


ROW_INSERT = "insert into risk_scores"


def test_the_rerank_reads_and_moves_the_pointer_in_a_constant_number_of_statements(
    tmp_path, monkeypatch
):
    """The N+1 this target actually dies of, asserted as **shape** rather than as wall-clock.

    Five seconds is generous on purpose, so a query per asset finishes well inside it at 220 and
    falls over at 2,000 — which is the regression the row's *action if exceeded* column tells the
    reader to look for. PTEST-002 asserts the same property for the board; the re-rank is the
    other place in this product where a loop can quietly become a query.

    **The row inserts are counted separately, and saying why is the point.** SQLite's trace
    callback fires per *parameter set* (and again for the `before insert` trigger's program), so
    `executemany` over 220 assets traces many times whatever the code does — a total that grows
    with the input is not evidence of a loop, and comparing raw totals is a check that could only
    ever fail. So the writes are asserted for what they should be — the **same number per asset**
    at both sizes, which a `for` loop issuing an extra lookup per row would break — and
    **everything else** is required to be constant: the join over `scenario_forecast_cells`, the
    scenario lookups, the transaction, and the pointer's compare-and-swap.
    """
    small_app, small_client, small_id = demo_scale_storm(
        tmp_path, monkeypatch, assets=110, name="small"
    )
    small = statements_during(
        small_app.state.db,
        lambda: small_client.post(f"/api/v1/scenarios/{small_id}/forecast-revisions"),
    )
    small_app.state.db.close()

    large_app, large_client, large_id = demo_scale_storm(
        tmp_path, monkeypatch, assets=ASSETS, name="large"
    )
    large = statements_during(
        large_app.state.db,
        lambda: large_client.post(f"/api/v1/scenarios/{large_id}/forecast-revisions"),
    )

    # The positive assertions beside the comparison, over the same enumeration: the work the
    # re-rank is supposed to do must be in it, or a tracer that had stopped firing would satisfy
    # every count below perfectly.
    assert any("update scenarios set forecast_revision" in sql for sql in large), large
    assert any("scenario_forecast_cells" in sql for sql in large), large
    inserts_small = sum(ROW_INSERT in sql for sql in small)
    inserts_large = sum(ROW_INSERT in sql for sql in large)
    assert inserts_small and inserts_large, "no ranking rows were written"
    assert inserts_large * 110 == inserts_small * ASSETS, (
        f"{inserts_small} write statements for 110 assets and {inserts_large} for 220 — "
        "the write is not one row per asset"
    )

    around_small = [sql for sql in small if ROW_INSERT not in sql]
    around_large = [sql for sql in large if ROW_INSERT not in sql]
    assert len(around_large) == len(around_small), (
        f"{len(around_small)} statements around the write at 110 assets and "
        f"{len(around_large)} at 220 — the re-rank is querying inside a loop"
    )
    large_app.state.db.close()


def test_reading_the_reranked_list_back_is_inside_the_limit_too(tmp_path, monkeypatch):
    """REQ-NF-001's other half, and the reason `technical-spec.md` §6 separates them: a re-rank
    is a write and every read is served from stored rows, so one bounds the write and one bounds
    the read. AC-005's *retrievable for comparison* is a read of an **earlier** revision, which
    is the one a cache would have made fast and honest measurement does not."""
    application, client, scenario_id = demo_scale_storm(tmp_path, monkeypatch)
    assert client.post(f"/api/v1/scenarios/{scenario_id}/forecast-revisions").status_code == 201

    started = time.perf_counter()
    recalled = client.get(
        f"/api/v1/scenarios/{scenario_id}/risks?forecast_revision=0&limit=500"
    )
    elapsed = time.perf_counter() - started

    assert recalled.status_code == 200, recalled.text
    assert len(recalled.json()["items"]) == ASSETS
    assert elapsed < LIMIT_SECONDS, (
        f"reading the earlier revision took {elapsed:.2f}s against a {LIMIT_SECONDS}s limit"
    )
    application.state.db.close()
