"""CHG-056 — the client's own dataset loads, and nothing a caller uploads can 500.

The Hurricane Delia pack is written to the client's build prompt: `customers_served`,
`external_id`, `asset_type` with seven capitalised names, condition ratings as words, a
`work_type` column, and one combined weather shape. Three real uploads of it were
answered *Something went wrong* — a raw `KeyError` surfacing as a 500. Every case here
is a sentence of that dialect, and the last ones are the guard: whatever the bytes, the
loader's only failure is a **named** `LoadFailed`.
"""

import pytest
from app.loader.load import load_scenario
from app.loader.records import LoadFailed

MANIFEST = b"""{
  "scenario_id": "delia-mini",
  "storm_name": "Hurricane Delia",
  "forecast_issued_at": "2026-09-14T12:00:00Z",
  "files": ["assets.csv", "maintenance.csv", "weather.csv", "outages.csv"],
  "service_areas": [
    {"service_area_id": "SA-COAST-N", "name": "North Coastal", "customers_served": 412000},
    {"service_area_id": "SA-INLAND-E", "name": "East Inland", "customers_served": 158000}
  ],
  "design_references": {
    "Distribution": {"design_gust_mph": 90, "service_life_years": 35},
    "Transmission Line": {"design_gust_mph": 140, "service_life_years": 50},
    "Substation": {"design_gust_mph": 130, "service_life_years": 40}
  },
  "known_defects": ["ignored extra key"]
}"""

ASSETS = b"""external_id,name,asset_type,service_area_id,lat,lon,install_year,flood_zone,condition_rating,condition_source,condition_date,is_critical_facility
SS-1001,Bayside Substation,Substation,SA-COAST-N,29.951,-88.874,1982,VE,fair,field inspection,2021-06-01,true
DL-2001,Oakwood Feeder 4,Distribution,SA-COAST-N,29.960,-88.870,1998,AE,good,field inspection,2024-02-01,false
TL-3001,North Transmission,Transmission Line,SA-INLAND-E,29.970,-88.860,1975,X,poor,field inspection,2019-05-01,false
PS-4001,Harbor Pumping,Pumping Station,SA-COAST-N,29.955,-88.880,2005,AE,good,field inspection,2023-08-01,false
WT-5001,Lakeside Water Treatment,Water Treatment,SA-INLAND-E,29.980,-88.850,1990,X,fair,field inspection,2022-01-01,true
"""

MAINTENANCE = b"""external_id,asset_name,inspection_date,work_type,condition_rating,notes
SS-1001,Bayside Substation,2021-06-01,routine,fair,Annual inspection
DL-2001,Oakwood Feeder 4,2023-03-05,unplanned,poor,Storm damage found
TL-3001,North Transmission,2020-09-05,routine,good,Walkdown complete
"""

WEATHER = (
    b"grid_cell_id,external_id,valid_time,wind_gust_mph,station_gust_mph,rainfall_in\n"
    b"G-01,SS-1001,2026-09-14T13:00:00,85.0,,0.16\n"
    b"G-01,DL-2001,2026-09-14T13:00:00,85.0,88.0,0.16\n"
    b"G-02,TL-3001,2026-09-14T13:00:00,70.0,,0.10\n"
    b"G-02,PS-4001,2026-09-14T13:00:00,70.0,,0.10\n"
    b"G-01,WT-5001,2026-09-14T13:00:00,85.0,,0.16\n"
    b"G-01,SS-1001,2026-09-14T19:00:00,96.0,,0.30\n"
    b"G-01,DL-2001,2026-09-14T19:00:00,96.0,,0.30\n"
    b"G-02,TL-3001,2026-09-14T19:00:00,80.0,,0.22\n"
    b"G-02,PS-4001,2026-09-14T19:00:00,80.0,,0.22\n"
    b"G-01,WT-5001,2026-09-14T19:00:00,96.0,,0.30\n"
)

OUTAGES = b"""external_id,service_area_id,county,failure_time,storm_id,customers_out
SS-1001,SA-COAST-N,Bayline County,2023-08-28T22:46:13,Hurricane Baxter,1200
,SA-INLAND-E,Bayline County,2023-08-28T23:00:00,Hurricane Baxter,300
DL-2001,SA-COAST-N,Bayline County,2023-08-29T01:00:00,Hurricane Baxter,0
"""


def delia(**overrides) -> dict[str, bytes]:
    files = {
        "manifest.json": MANIFEST,
        "assets.csv": ASSETS,
        "maintenance.csv": MAINTENANCE,
        "weather.csv": WEATHER,
        "outages.csv": OUTAGES,
    }
    files.update(overrides)
    return files


# --- The dialect, sentence by sentence ---------------------------------------------------


def test_the_delia_manifest_parses_with_customers_served():
    result = load_scenario(delia())
    assert result.service_areas == {"SA-COAST-N": 412000, "SA-INLAND-E": 158000}
    assert result.service_area_names["SA-COAST-N"] == "North Coastal"


def test_external_id_and_asset_type_alias_onto_the_stored_shape():
    result = load_scenario(delia())
    codes = {code for asset in result.assets for code in asset.external_ids}
    assert "SS-1001" in codes and "TL-3001" in codes
    types = {asset.type for asset in result.assets}
    # Seven dialect names land in the four scoring categories, by table not by guess.
    assert types <= {"substation", "line", "plant", "pump"}
    named = {asset.external_ids[0]: asset.type for asset in result.assets}
    assert named["SS-1001"] == "substation"
    assert named["DL-2001"] == "line"
    assert named["TL-3001"] == "line"
    assert named["PS-4001"] == "pump"
    assert named["WT-5001"] == "plant"


def test_condition_words_map_through_the_clients_own_severities():
    # good 0.2, fair 0.55, poor 0.9 (the client's numbers) through severity=(5-r)/5:
    # good -> 4.0, fair -> 2.25, poor -> 0.5. Exact, not approximate.
    result = load_scenario(delia())
    by_code = {asset.external_ids[0]: asset for asset in result.assets}
    assert by_code["DL-2001"].condition == "4.0"
    assert by_code["SS-1001"].condition == "2.25"
    assert by_code["TL-3001"].condition == "0.5"


def test_the_combined_weather_shape_yields_a_forecast_series_and_gusts():
    result = load_scenario(delia())
    assert len(result.forecast_revisions) == 2, "two distinct valid times"
    by_code = {asset.external_ids[0]: asset for asset in result.assets}
    assert by_code["SS-1001"].wind_gust_mph == 85.0, "revision 0's grid gust"
    assert by_code["SS-1001"].grid_cell_id == "G-01"


def test_defect_3_counts_the_station_column_when_it_exists():
    result = load_scenario(delia())
    station = next(f for f in result.findings if f.defect == 3)
    # 10 rows, 1 station reading: 9 absences, counted from the station column.
    assert "9" in station.message
    assert station.affected_file == "weather.csv"


def test_defect_6_counts_routine_rows_when_work_type_exists():
    result = load_scenario(delia())
    routine = next(f for f in result.findings if f.defect == 6)
    assert "2" in routine.message, "two routine rows; the unplanned one is failure evidence"


def test_the_per_type_design_basis_reaches_each_asset():
    # Distribution is built to 90 mph and Transmission Line to 140. Both are category
    # `line` — which is exactly why the basis must travel per asset, not per category.
    result = load_scenario(delia())
    by_code = {asset.external_ids[0]: asset for asset in result.assets}
    assert by_code["DL-2001"].design_gust_mph == 90
    assert by_code["TL-3001"].design_gust_mph == 140
    assert by_code["SS-1001"].service_life_years == 40
    assert by_code["PS-4001"].design_gust_mph is None, "the manifest stated none for pumps"


def test_the_chg011_dialect_still_loads_identically():
    from conftest import fixture_files

    result = load_scenario(fixture_files())
    assert len(result.assets) > 0
    assert {1, 2, 3, 4, 5, 6, 7} <= {finding.defect for finding in result.findings}


# --- The guard: whatever the bytes, the only failure is a NAMED LoadFailed ----------------


@pytest.mark.parametrize(
    "broken",
    [
        # The exact 500 from the log: an area without the population key.
        delia(**{"manifest.json": b'{"scenario_id":"x","storm_name":"y",'
                 b'"forecast_issued_at":"z","service_areas":[{"service_area_id":"SA-1"}]}'}),
        # service_areas as a string, not a list.
        delia(**{"manifest.json": b'{"scenario_id":"x","storm_name":"y",'
                 b'"forecast_issued_at":"z","service_areas":"oops"}'}),
        # design_references as a list.
        delia(**{"manifest.json": b'{"scenario_id":"x","storm_name":"y",'
                 b'"forecast_issued_at":"z","design_references":[1,2]}'}),
        # A CSV whose header row is binary-ish junk that still decodes.
        delia(**{"assets.csv": b"\xef\xbb\xbfgarbage header\nrow"}),
    ],
)
def test_nothing_a_caller_uploads_can_raise_anything_but_loadfailed(broken):
    with pytest.raises(LoadFailed) as refused:
        load_scenario(broken)
    # Named: a stage and a file, so the 422 tells the person what to fix — never the
    # generic sentence three real uploads were answered with.
    assert refused.value.file
    assert refused.value.reason
