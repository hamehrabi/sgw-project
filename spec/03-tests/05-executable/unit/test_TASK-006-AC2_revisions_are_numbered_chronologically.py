"""TASK-006 done criterion 2 — a revision number is a position in **time**, not in a file.

CHG-025 decides that a forecast revision is one distinct `valid_time` in `weather.csv`,
*"numbered from 0 in chronological order"*. Everything REQ-F-004 means rests on that sentence:
`POST /scenarios/{id}/forecast-revisions` applies *"the scenario's **next** forecast change"*,
and if the numbering is not chronological then "next" walks the storm **backwards** through its
own forecasts — the plan adjusts to weather that has already passed, and no screen looks wrong.

**This file exists because the suite could not tell the right implementation from the obvious
wrong one.** `loader/load.py` numbers `sorted(observed, key=_chronological)`; the mutation
`enumerate(observed)` numbers by dictionary insertion order, which is file order. Every one of
the 323 tests passed under it, because the only fixture listed its three forecast times already
in chronological file order — the same shape as REQ-NF-007's three-way figure one review before:
*one fixture in which correct and incorrect agree.*

Three orders are named here, and they are deliberately three different answers:

| Order | What produces it |
|---|---|
| **file order** | `enumerate(observed)` — the obvious wrong implementation |
| **text order** | `sorted(observed)` — ISO-8601 as a string, which `_chronological`'s own
  docstring says is not enough |
| **chronological order** | `sorted(observed, key=_chronological)` — the implementation, and
  the only right answer |

`AGENT.md`: *a figure that claims a resolution needs a fixture in which the coarser and the
finer answers are different numbers, and the test must name all three.*
"""

import csv
import io
from datetime import UTC, datetime

import pytest
from conftest import FIXTURES, fixture_files

FIXTURE = "storm-with-a-forecast-change"

WEATHER_HEADER = "grid_cell_id,asset_id,valid_time,wind_gust_mph,rainfall_in"

REVISION_0_AT = "2026-08-15T00:00:00Z"
REVISION_1_AT = "2026-08-15T06:00:00Z"
REVISION_2_AT = "2026-08-15T12:00:00Z"


def load(files):
    from app.loader.load import load_scenario

    return load_scenario(files)


def file_order_of_forecast_times(weather: bytes) -> list[str]:
    """The distinct forecast times in the order the FILE lists them.

    Cell-level rows only — an asset-linked row says which grid cell an asset sits in and its
    gust column is the one the source PRD measured as 97% empty (defect 3), so it is never a
    forecast and `_forecast_series` skips it.
    """
    seen: list[str] = []
    for row in csv.DictReader(io.StringIO(weather.decode("utf-8-sig"))):
        when = (row.get("valid_time") or "").strip()
        if (row.get("asset_id") or "").strip() or not (row.get("grid_cell_id") or "").strip():
            continue
        if when and when not in seen:
            seen.append(when)
    return seen


def as_instant(valid_time: str) -> datetime:
    parsed = datetime.fromisoformat(valid_time.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def files_with_weather(rows: list[str]) -> dict[str, bytes]:
    """The fixture, with `weather.csv` replaced and the manifest's row count kept honest.

    `_check_row_counts` refuses a file that is not the length the manifest claims, so a test
    that swapped the weather rows and left the count alone would fail during validation and
    never reach the numbering at all.
    """
    import json

    files = dict(fixture_files(FIXTURE))
    files["weather.csv"] = ("\n".join([WEATHER_HEADER, *rows]) + "\n").encode()
    manifest = json.loads(files["manifest.json"])
    manifest["row_counts"]["weather.csv"] = len(rows)
    files["manifest.json"] = json.dumps(manifest).encode()
    return files


# --- The shipped fixture: file order and chronological order must disagree ------------------


def test_the_fixture_does_not_list_its_forecasts_in_chronological_file_order():
    """The haystack, and the reason this assertion is first.

    Every claim below is worth nothing if the fixture is ever tidied back into chronological
    file order: the wrong implementation would agree with the right one again and the whole
    file would go quietly green. So the disagreement is asserted as a property of the fixture
    rather than trusted to survive somebody's editor.
    """
    in_file = file_order_of_forecast_times((FIXTURES / FIXTURE / "weather.csv").read_bytes())

    assert in_file == [REVISION_1_AT, REVISION_2_AT, REVISION_0_AT]
    assert in_file != sorted(in_file, key=as_instant), (
        "the fixture is back in chronological file order, so numbering by file order would "
        "pass every test in this file"
    )


def test_revisions_are_numbered_by_time_and_not_by_position_in_the_file():
    """Three orders, three different answers, all three named (`AGENT.md`).

    file order   06:00, 12:00, 00:00   <- `enumerate(observed)`
    text order   00:00, 06:00, 12:00   <- coincides here; the offsets case below separates it
    the answer   00:00, 06:00, 12:00
    """
    series = load(fixture_files(FIXTURE)).forecast_revisions

    assert [revision.forecast_revision for revision in series] == [0, 1, 2]
    assert [revision.valid_time for revision in series] == [
        REVISION_0_AT,
        REVISION_1_AT,
        REVISION_2_AT,
    ]


def test_each_revision_carries_the_forecast_issued_at_its_own_time():
    """The number and the data have to move together.

    A numbering that is chronological while the cells behind it are not is the same defect
    wearing a correct-looking list: revision 0 would be labelled 00:00 and hold the 06:00 gusts.
    """
    series = load(fixture_files(FIXTURE)).forecast_revisions
    gusts = [
        {cell.grid_cell_id: cell.wind_gust_mph for cell in revision.cells}
        for revision in series
    ]

    assert gusts[0]["GC-A"] == 120 and gusts[0]["GC-B"] == 70
    assert gusts[1]["GC-A"] == 60 and gusts[1]["GC-B"] == 128
    assert gusts[2]["GC-A"] == 132 and gusts[2]["GC-B"] == 55
    # Revision 2 names two cells; the other three keep the value they were last issued, and
    # keep the time they were issued at rather than claiming the revision's own (CHG-025).
    assert gusts[2]["GC-C"] == 60
    assert [cell.valid_time for cell in series[2].cells if cell.grid_cell_id == "GC-C"] == [
        REVISION_1_AT
    ]


def test_the_asset_row_carries_the_earliest_forecast_and_not_the_first_one_in_the_file():
    """`_apply_weather` dates the joined asset view from `series[0]`, so the same defect reaches
    REQ-F-001's picture of the storm *as loaded* — ALPHA would be loaded at 60 mph, the gust six
    hours after the storm was prepared."""
    result = load(fixture_files(FIXTURE))

    alpha = next(a for a in result.assets if "SS-ALPHA" in a.external_ids)
    bravo = next(a for a in result.assets if "SS-BRAVO" in a.external_ids)
    assert alpha.wind_gust_mph == 120
    assert bravo.wind_gust_mph == 70


# --- The orders that only a parse can get right ----------------------------------------------


def test_a_file_written_backwards_produces_exactly_the_same_series():
    """Reversing the file must change nothing at all. If it changes the numbering, the file is
    the order — which is what CHG-025 says it is not."""
    forwards = load(fixture_files(FIXTURE)).forecast_revisions

    weather = (FIXTURES / FIXTURE / "weather.csv").read_bytes().decode()
    body = [line for line in weather.strip().split("\n")[1:] if line]
    backwards = load(files_with_weather(list(reversed(body)))).forecast_revisions

    assert [(r.forecast_revision, r.valid_time) for r in backwards] == [
        (r.forecast_revision, r.valid_time) for r in forwards
    ]
    assert [
        (cell.grid_cell_id, cell.valid_time, cell.wind_gust_mph)
        for revision in backwards
        for cell in revision.cells
    ] == [
        (cell.grid_cell_id, cell.valid_time, cell.wind_gust_mph)
        for revision in forwards
        for cell in revision.cells
    ]


def test_two_forecasts_in_different_offsets_are_ordered_by_the_instant_not_the_text():
    """The clause `_chronological` exists for, and the one nothing reached.

    `2026-08-15T01:00:00+02:00` **is** `2026-08-14T23:00:00Z` — an hour and a half *before*
    `2026-08-15T00:30:00Z`. Sorted as text it comes second, because `'1' > '0'`. So this file
    separates all three orders at once:

        file order   00:30Z, 01:00+02:00
        text order   00:30Z, 01:00+02:00
        the answer   01:00+02:00, 00:30Z

    A prepared file may legitimately carry a local offset — `data-and-integration-spec.md`
    fixes the column as a timestamp and not as a UTC-only one — and reading the storm backwards
    through two forecasts is the same failure as reading it backwards through three.
    """
    earlier_in_text = "2026-08-15T00:30:00Z"
    earlier_in_fact = "2026-08-15T01:00:00+02:00"
    assert sorted([earlier_in_text, earlier_in_fact]) == [earlier_in_text, earlier_in_fact]
    assert as_instant(earlier_in_fact) < as_instant(earlier_in_text)

    series = load(
        files_with_weather(
            [
                f"GC-A,,{earlier_in_text},70,0.4",
                f"GC-B,,{earlier_in_text},70,0.4",
                f"GC-A,,{earlier_in_fact},120,0.4",
                f"GC-B,,{earlier_in_fact},120,0.4",
            ]
        )
    ).forecast_revisions

    assert [(r.forecast_revision, r.valid_time) for r in series] == [
        (0, earlier_in_fact),
        (1, earlier_in_text),
    ]
    assert [cell.wind_gust_mph for cell in series[0].cells] == [120, 120]


def test_a_forecast_time_nothing_can_parse_sorts_last_and_the_series_stays_total():
    """`_chronological`'s other branch, exercised rather than assumed.

    A `valid_time` no parser accepts still has to land somewhere fixed, or the series is a
    different list on different runs — `AGENT.md`'s total-order row, one table further out. It
    sorts after everything that parsed, by its own text, and the storm's real forecasts keep
    their real order in front of it.
    """
    series = load(
        files_with_weather(
            [
                "GC-A,,soon,80,0.4",
                f"GC-A,,{REVISION_1_AT},60,0.3",
                f"GC-A,,{REVISION_0_AT},120,0.4",
                "GC-A,,also-soon,90,0.4",
            ]
        )
    ).forecast_revisions

    assert [(r.forecast_revision, r.valid_time) for r in series] == [
        (0, REVISION_0_AT),
        (1, REVISION_1_AT),
        (2, "also-soon"),
        (3, "soon"),
    ]


def test_two_rows_for_one_cell_at_one_time_do_not_become_two_revisions():
    """One revision is one forecast time — `unique (scenario_id, valid_time)` says so in the
    schema, and the loader has to agree or the insert aborts a whole load."""
    series = load(
        files_with_weather(
            [
                f"GC-A,,{REVISION_0_AT},120,0.4",
                f"GC-A,,{REVISION_0_AT},999,9.9",
                f"GC-B,,{REVISION_0_AT},70,0.4",
            ]
        )
    ).forecast_revisions

    assert [(r.forecast_revision, r.valid_time) for r in series] == [(0, REVISION_0_AT)]
    assert {cell.grid_cell_id: cell.wind_gust_mph for cell in series[0].cells} == {
        "GC-A": 120,
        "GC-B": 70,
    }


# --- At the size the requirement names --------------------------------------------------------


@pytest.mark.parametrize("assets", [40])
def test_the_demo_scale_storm_is_numbered_chronologically_too(assets):
    """`ci/synthetic.py` emits its ~5,000 filler forecast rows at randomly chosen times, so the
    generated storm is genuinely out of order in the file — and 43 forecasts walked backwards is
    a plan that ends where the storm started."""
    from synthetic import synthetic_scenario

    files = synthetic_scenario(assets=assets)
    in_file = file_order_of_forecast_times(files["weather.csv"])
    assert in_file != sorted(in_file, key=as_instant), "the generator now emits sorted times"

    series = load(files).forecast_revisions

    assert [revision.forecast_revision for revision in series] == list(range(len(series)))
    instants = [as_instant(revision.valid_time) for revision in series]
    assert instants == sorted(instants)
    assert len(set(instants)) == len(instants), "two revisions claim one forecast time"
