"""UTEST-005 — REQ-F-001. Defined in `03-tests/02-functional/unit-tests.md`.

Defect 3 — weather station gust values are largely absent, 97% missing in a real file.
  normal  — wind taken from the forecast grid square
  edge    — a station record present but null → still uses the grid
  failure — wind derived from a station column that is 97% empty → test fails

The fixture's asset-linked weather rows carry an empty `wind_gust_mph` and its grid-cell
rows carry a value everywhere, which is the shape the source PRD measured. A loader that
read the station column would produce `None` for every asset and a ranking with no wind in
it — plausible, and wrong.
"""

from conftest import fixture_files


def load():
    from app.loader.load import load_scenario

    return load_scenario(fixture_files())


def find(assets, external_id):
    return next(a for a in assets if external_id in a.external_ids)


def test_wind_comes_from_the_grid_square_not_the_station_row():
    result = load()

    northgate = find(result.assets, "SS-1042")

    assert northgate.wind_gust_mph == 96.0


def test_every_asset_with_a_grid_cell_gets_a_gust():
    """The whole point of the grid: it has a value everywhere."""
    result = load()

    with_cells = [a for a in result.assets if a.grid_cell_id]

    assert with_cells
    assert all(a.wind_gust_mph is not None for a in with_cells)


def test_a_null_station_value_does_not_override_the_grid():
    result = load()

    ridgeline = find(result.assets, "LN-3312")

    assert ridgeline.wind_gust_mph == 74.0


def test_the_defect_is_recorded_as_caught():
    """FF-006 counts the checks that ran, not the ones that were written down."""
    result = load()

    assert any(finding.defect == 3 for finding in result.findings)


def test_the_check_is_silent_when_no_gust_is_actually_missing():
    """The other half, and the half that was missing.

    This check returned a finding whenever `weather.csv` carried any asset-linked row, so it
    fired on every dataset and reported the defect whether or not it was present — FF-006
    counted it toward 7 of 7 regardless. Found by removing each defect from the fixture in
    turn during the TASK-002 review. A check that cannot be absent is not detecting anything.
    """
    from app.loader.defects import gusts_absent_from_station_rows

    assert gusts_absent_from_station_rows(station_rows=4, station_values=4) is None
    assert gusts_absent_from_station_rows(station_rows=0, station_values=0) is None
    assert gusts_absent_from_station_rows(station_rows=4, station_values=1) is not None


def test_an_asset_outside_every_grid_cell_has_no_invented_gust():
    result = load()

    coastal = find(result.assets, "LN-8899")

    assert coastal.wind_gust_mph is None, "no cell means no reading, never a zero"
