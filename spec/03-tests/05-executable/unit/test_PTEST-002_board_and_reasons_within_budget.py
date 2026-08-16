"""PTEST-002 — REQ-NF-001. Defined in `03-tests/03-non-functional/performance-tests.md`.

*Page load, and opening the reason panel → **under 2 s** and **under 300 ms**, against the
fixture: 220 assets, ~5,000 forecast rows.*

The row's *action if exceeded* column is the specification for this file, and both halves are
asserted as **shape** rather than only as wall-clock:

- *Check the board query for an unindexed scan on `damage_reports(scenario_id, status)`* — so
  the query plan is asserted, and the number of statements the board issues is asserted to be
  constant in the number of reports. A per-report query is the way this target actually fails,
  and it fails at a report count no test fixture will be built at.
- *Check the reason payload is not re-fetched* — so the 300 ms budget is met by construction:
  reasons arrive **in the same response** as the rank (BR-002, `technical-spec.md` §3), and
  opening the panel therefore issues no request at all. A timing number for that would be
  measuring React, not this system.

A wall-clock assertion is kept for the page load itself, deliberately loose, because what it
catches is an order-of-magnitude regression rather than a slow machine.
"""

import time

import pytest
from conftest import ADMIN_PASSWORD, build_application
from fastapi.testclient import TestClient
from synthetic import synthetic_scenario

ASSETS = 220
PAGE_LOAD_BUDGET_SECONDS = 2.0


@pytest.fixture
def demo_scale(tmp_path, monkeypatch):
    """One application, one storm at demo scale, signed in.

    The shipped upload limits rather than `conftest`'s deliberately tiny ones: this is the
    only test that has to push a real dataset through the real endpoint.
    """
    from app.store import users

    application = build_application(
        monkeypatch,
        tmp_path / "perf.db",
        SCENARIO_MAX_FILE_BYTES=8388608,
        SCENARIO_MAX_TOTAL_BYTES=10485760,
    )
    users.create_user(
        application.state.db,
        name="Ops",
        email="perf@sgw.example",
        password=ADMIN_PASSWORD,
        role="admin",
    )
    with TestClient(application) as client:
        client.post(
            "/api/v1/auth/session",
            json={"email": "perf@sgw.example", "password": ADMIN_PASSWORD},
        )
        files = synthetic_scenario(assets=ASSETS)
        created = client.post(
            "/api/v1/scenarios",
            data={"name": "Demo scale", "source_note": "synthetic"},
            files=[("files", (name, content, "text/csv")) for name, content in files.items()],
        )
        assert created.status_code == 201, created.text
        yield application, client, created.json()["scenario_id"]


def seed_reports(application, scenario_id, count):
    """Through the store, not the endpoint: this is volume, not behaviour."""
    from app.store import dispatch

    for index in range(count):
        dispatch.file_report(
            application.state.db,
            scenario_id=scenario_id,
            neighbourhood=f"Area {index % 12}",
            asset_id=None,
            reported_by="U-seed",
        )


def statements_during(connection, work):
    """Every SQL statement the connection executes while `work` runs."""
    seen = []
    connection.set_trace_callback(seen.append)
    try:
        work()
    finally:
        connection.set_trace_callback(None)
    # Prove the haystack is a haystack before anyone reports no needle. Every assertion built
    # on this list compares two counts, and `0 == 0` passes: if `set_trace_callback` ever
    # stopped firing — a different connection, a driver change — the N+1 check below would go
    # quiet rather than red.
    assert seen, "no SQL was captured; the trace callback is not firing"
    return seen


def issued(statements, sql):
    """Was this statement among them? The tracer substitutes the bound parameters, so the SQL
    is matched by the fragments either side of them rather than verbatim."""
    parts = [part for part in sql.split("?") if part.strip()]
    return any(all(part in statement for part in parts) for statement in statements)


def test_the_board_query_searches_by_index_rather_than_scanning(demo_scale):
    """The exact check `performance-tests.md` names, against the SQL the board actually runs.

    **The index is named, and that is the load-bearing half.** `SCAN not in plan` alone cannot
    fail for `repair_jobs`: three indexes are prefixed by `scenario_id` — the one below,
    `sqlite_autoindex_repair_jobs_2` from `unique (scenario_id, location_key)`, and the
    foreign-key parent key added by migration 008 — so dropping the one this row names left the
    plan reading `SEARCH … USING INDEX` and the assertion green. It was an index guarded by
    nothing, in the test that names it. Pinning the name is what makes dropping it red.
    """
    application, _, scenario_id = demo_scale
    from app.store import dispatch

    for sql, index in (
        (dispatch.JOBS_SQL, "repair_jobs_scenario_status"),
        (dispatch.REPORTS_SQL, "damage_reports_scenario_status_job"),
    ):
        plan = " | ".join(
            row["detail"]
            for row in application.state.db.execute(
                f"explain query plan {sql}", (scenario_id,)
            )
        )
        assert "SCAN" not in plan, f"unindexed scan in the board query: {plan}"
        assert "USING INDEX" in plan or "USING COVERING INDEX" in plan, plan
        assert index in plan, f"the board query no longer uses {index}: {plan}"


def test_the_board_issues_the_same_number_of_queries_at_ten_reports_and_at_two_hundred(
    demo_scale,
):
    """The N+1 this target dies of. A query per report passes every functional test."""
    application, client, scenario_id = demo_scale
    from app.store import dispatch

    seed_reports(application, scenario_id, 10)
    small = statements_during(
        application.state.db, lambda: client.get(f"/api/v1/scenarios/{scenario_id}/jobs")
    )
    seed_reports(application, scenario_id, 190)
    large = statements_during(
        application.state.db, lambda: client.get(f"/api/v1/scenarios/{scenario_id}/jobs")
    )

    # The positive assertion beside the comparison, over the same enumeration: the two
    # statements the board is supposed to issue must be found in it. Without this, an
    # enumeration that quietly returned nothing would satisfy `len(large) == len(small)`
    # perfectly and prove nothing at all.
    for sql in (dispatch.JOBS_SQL, dispatch.REPORTS_SQL):
        assert issued(small, sql), f"the board did not issue {sql}"
    assert len(large) == len(small), (
        f"{len(small)} statements for 10 reports and {len(large)} for 200 — "
        "the board is querying inside a loop"
    )


def test_the_first_usable_screen_is_inside_two_seconds(demo_scale):
    """Every request the screen makes on load, at the volume the requirement names."""
    application, client, scenario_id = demo_scale
    seed_reports(application, scenario_id, 200)

    started = time.perf_counter()
    responses = [
        client.get(f"/api/v1/scenarios/{scenario_id}"),
        client.get(f"/api/v1/scenarios/{scenario_id}/assets"),
        client.get(f"/api/v1/scenarios/{scenario_id}/risks"),
        client.get(f"/api/v1/scenarios/{scenario_id}/jobs"),
    ]
    elapsed = time.perf_counter() - started

    assert [response.status_code for response in responses] == [200, 200, 200, 200]
    # The screen's own request, bounded by the API contract at a page rather than the whole
    # scenario — but ranked over all 220, which is the volume the requirement names.
    assert responses[2].json()["total"] == ASSETS
    assert len(responses[1].json()["items"]) == ASSETS
    assert elapsed < PAGE_LOAD_BUDGET_SECONDS, (
        f"the four page-load requests took {elapsed:.2f}s against a "
        f"{PAGE_LOAD_BUDGET_SECONDS}s budget"
    )


def test_the_reasons_arrive_with_the_rank_and_are_never_re_fetched(demo_scale):
    """The 300 ms half. Opening the panel costs no request, so the budget is structural."""
    _, client, scenario_id = demo_scale

    ranking = client.get(f"/api/v1/scenarios/{scenario_id}/risks").json()

    scored = [item for item in ranking["items"] if item["score"] is not None]
    assert scored, "the fixture carries scored assets"
    assert all(item["reasons"] for item in scored), "a rank on screen without its reasons (BR-002)"


def test_no_endpoint_returns_reasons_on_their_own(demo_scale):
    """If one existed, a view could be written that fetches them — and the state BR-002
    forbids, a rank on screen with its reasons still loading, becomes reachable.

    Read from the published schema rather than from `application.routes`. The first version of
    this test walked that list and **could not fail**: this FastAPI wraps `include_router` in a
    route object whose own `path` is `None`, so the walk saw four documentation routes and none
    of the application's. It was written, passed, and proved nothing until the mutation check
    added a `/reasons` endpoint and the test stayed green — the fourth gate-that-cannot-fail
    found in this repository, and the first one found in a test rather than in a fitness
    function.
    """
    application, _, _ = demo_scale

    paths = list(application.openapi()["paths"])

    # The guard that keeps the assertion below from going quiet: if the enumeration stops
    # finding endpoints, this fails rather than passing on an empty list.
    assert "/api/v1/scenarios/{scenario_id}/risks" in paths
    assert not [path for path in paths if "reason" in path.lower()]


def test_the_board_read_does_not_grow_slower_than_its_input(demo_scale):
    """Wall-clock on 200 reports, loose enough to survive a shared machine and tight enough
    to catch work that is quadratic in the report count."""
    application, client, scenario_id = demo_scale
    seed_reports(application, scenario_id, 200)

    started = time.perf_counter()
    board = client.get(f"/api/v1/scenarios/{scenario_id}/jobs")
    elapsed = time.perf_counter() - started

    assert board.json()["report_count"] == 200
    assert elapsed < PAGE_LOAD_BUDGET_SECONDS, f"the board alone took {elapsed:.2f}s"
