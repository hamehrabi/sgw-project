"""Parsing a prepared storm into one record per asset.

A pure function over the uploaded bytes: no request, no screen, no store. It either returns
a complete `LoadResult` or raises `LoadFailed` naming the file and the stage — there is no
third outcome, because a half-loaded storm is worse than a refused one.

It scores nothing. The four factors ADR-007 weighs are carried out of here as values; what
they are worth is `scoring/`'s, and TASK-003's.
"""

import csv
import io
import json
from datetime import UTC, datetime

from app.loader import defects
from app.loader.matching import merge_by_site_and_name
from app.loader.records import (
    Finding,
    ForecastRevision,
    LoadedAsset,
    LoadedForecast,
    LoadedOutage,
    LoadFailed,
    LoadResult,
)

REQUIRED_FILES = ("manifest.json", "assets.csv", "maintenance.csv", "weather.csv", "outages.csv")
ASSET_TYPES = frozenset({"substation", "line", "plant", "pump"})


def _rows(files: dict[str, bytes], name: str) -> list[dict]:
    try:
        text = files[name].decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise LoadFailed(name, "decode", "the file is not valid UTF-8 text") from error
    return list(csv.DictReader(io.StringIO(text)))


def _number(value, cast):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return cast(value)
    except ValueError:
        return None


def _read_manifest(files: dict[str, bytes]) -> dict:
    try:
        manifest = json.loads(files["manifest.json"].decode("utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise LoadFailed("manifest.json", "parse", "the manifest is not valid JSON") from error

    for field in ("scenario_id", "storm_name", "forecast_issued_at"):
        if not manifest.get(field):
            raise LoadFailed("manifest.json", "validate", f"{field} is missing")
    return manifest


def _check_row_counts(manifest: dict, files: dict[str, bytes]) -> None:
    """A CSV that parses and is half the length it claims is what a size limit misses."""
    for name, expected in (manifest.get("row_counts") or {}).items():
        if name not in files:
            raise LoadFailed(name, "validate", "named in the manifest but not supplied")
        actual = len(_rows(files, name))
        if actual != expected:
            raise LoadFailed(
                name,
                "validate",
                f"the manifest claims {expected} rows and the file carries {actual}",
            )


def _read_assets(files: dict[str, bytes]) -> list[LoadedAsset]:
    assets = []
    for row in _rows(files, "assets.csv"):
        code = (row.get("asset_id") or "").strip()
        asset_type = (row.get("type") or "").strip().lower()
        lat, lon = _number(row.get("lat"), float), _number(row.get("lon"), float)

        # §4: a record missing an identifier, a type and a location is rejected, not guessed at.
        if not code or asset_type not in ASSET_TYPES or lat is None or lon is None:
            raise LoadFailed(
                "assets.csv",
                "validate",
                f"record '{code or '(no id)'}' lacks an identifier, a usable type, or a location",
            )

        source = (row.get("condition_source") or "").strip() or None
        condition = (row.get("condition_rating") or "").strip() or None
        observed = (row.get("condition_date") or "").strip() or None

        # BR-003 is enforced by the store; refusing it here too would let a bad row reach
        # the insert and fail there, which names the constraint rather than the file.
        if condition and not (source and observed):
            raise LoadFailed(
                "assets.csv",
                "validate",
                f"record '{code}' carries a condition with no source or no date (BR-003)",
            )

        assets.append(
            LoadedAsset(
                external_ids=[code],
                name=(row.get("name") or "").strip(),
                type=asset_type,
                lat=lat,
                lon=lon,
                install_year=_number(row.get("install_year"), int),
                flood_zone=(row.get("flood_zone") or "").strip() or None,
                condition=condition,
                condition_source=source,
                condition_observed_at=observed,
                condition_estimated=defects.condition_is_estimated(source),
            )
        )
    return assets


def _chronological(valid_time: str) -> tuple[int, str]:
    """A total order over forecast times.

    ISO-8601 strings usually sort chronologically as text, and "usually" is how the rest of
    this repository ended up with an order that was not one (CHG-018). The times are parsed;
    anything unparseable sorts after everything that parsed, by its own text, so the series is
    still total and still the same on every run.
    """
    try:
        parsed = datetime.fromisoformat(valid_time.replace("Z", "+00:00"))
    except ValueError:
        return (1, valid_time)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return (0, parsed.astimezone(UTC).isoformat())


def _forecast_series(files: dict[str, bytes]) -> list[ForecastRevision]:
    """Every distinct forecast time in `weather.csv`, as a complete grid each (CHG-025).

    **Each revision carries every cell the file has ever named**, not only the cells that got a
    new row at that time: a forecast grid square that goes quiet has not stopped forecasting,
    and blanking it would make its assets UNSCORED at every revision after the first — the list
    would not re-rank, it would empty. The carried value keeps the `valid_time` it was issued
    at, so nothing claims to be more current than it is.

    Carrying forward happens **once, here, at load**. It is a decision about what a revision
    contains, and deliberately not a read-time fallback: §7.3 forbids a read that quietly
    answers with a different revision than the one it was asked for.
    """
    observed: dict[str, dict[str, LoadedForecast]] = {}
    for row in _rows(files, "weather.csv"):
        cell = (row.get("grid_cell_id") or "").strip()
        code = (row.get("asset_id") or "").strip()
        when = (row.get("valid_time") or "").strip()
        # Asset-linked rows say which cell an asset is in; their gust column is the one the
        # source PRD measured as 97% empty and is never a forecast (defect 3).
        if code or not cell or not when:
            continue
        observed.setdefault(when, {}).setdefault(
            cell,
            LoadedForecast(
                grid_cell_id=cell,
                valid_time=when,
                wind_gust_mph=_number(row.get("wind_gust_mph"), float),
                rainfall_in=_number(row.get("rainfall_in"), float),
            ),
        )

    carried: dict[str, LoadedForecast] = {}
    series = []
    for revision, when in enumerate(sorted(observed, key=_chronological)):
        carried.update(observed[when])
        series.append(
            ForecastRevision(
                forecast_revision=revision,
                valid_time=when,
                cells=tuple(carried[cell] for cell in sorted(carried)),
            )
        )
    return series


def _apply_weather(
    assets: list[LoadedAsset], files: dict[str, bytes], series: list[ForecastRevision]
) -> Finding | None:
    """Defect 3 — wind comes from the forecast grid, never from the station column.

    The gust an asset carries is **revision 0's**, taken from the same series the store keeps,
    so the joined asset view and the revision-0 ranking cannot disagree about what was loaded.
    """
    cell_of_asset: dict[str, str] = {}
    station_rows = station_values = 0

    for row in _rows(files, "weather.csv"):
        cell = (row.get("grid_cell_id") or "").strip()
        code = (row.get("asset_id") or "").strip()
        if not code:
            continue
        # An asset-linked row says which cell the asset is in. Its gust column is the
        # one the source PRD measured as 97% empty, and is deliberately not read.
        station_rows += 1
        station_values += _number(row.get("wind_gust_mph"), float) is not None
        if cell:
            cell_of_asset[code] = cell

    grid = {cell.grid_cell_id: cell for cell in series[0].cells} if series else {}
    for asset in assets:
        cell = next((cell_of_asset[c] for c in asset.external_ids if c in cell_of_asset), None)
        if cell is None:
            continue
        asset.grid_cell_id = cell
        forecast = grid.get(cell)
        asset.wind_gust_mph = forecast.wind_gust_mph if forecast else None
        asset.rainfall_in = forecast.rainfall_in if forecast else None

    return defects.gusts_absent_from_station_rows(station_rows, station_values)


def _read_outages(files, service_areas, findings) -> list[LoadedOutage]:
    outages = []
    for row in _rows(files, "outages.csv"):
        code = (row.get("asset_id") or "").strip() or None
        area = (row.get("service_area_id") or "").strip() or None
        out = _number(row.get("customers_out"), int)
        population = service_areas.get(area) if area else None

        # Defect 5 first: an impossible figure is flagged and then not used for anything.
        if defects.outage_count_is_impossible(out, population):
            findings.append(defects.impossible_count(code, area, out, population))
            percentage = None
        else:
            percentage = defects.percentage_out(out, population)
            # Defect 4: a total that cannot support a percentage is named, not rounded to 0.
            if out is not None and out <= 0:
                findings.append(defects.broken_total(code, area))

        outages.append(
            LoadedOutage(
                asset_external_id=code,
                failure_time=(row.get("failure_time") or "").strip(),
                storm_id=(row.get("storm_id") or "").strip(),
                customers_out=out,
                service_area_id=area,
                percentage_out=percentage,
            )
        )
    return outages


def load_scenario(files: dict[str, bytes]) -> LoadResult:
    missing = [name for name in REQUIRED_FILES if name not in files]
    if missing:
        raise LoadFailed(missing[0], "validate", "required file is absent from the upload")

    manifest = _read_manifest(files)
    _check_row_counts(manifest, files)

    service_areas = {
        area["service_area_id"]: area["customer_count"]
        for area in manifest.get("service_areas", [])
    }

    assets = merge_by_site_and_name(_read_assets(files))
    findings: list[Finding] = []

    for finding in (defects.unmatched_codes(assets), defects.stale_condition(assets)):
        if finding:
            findings.append(finding)

    series = _forecast_series(files)
    weather_finding = _apply_weather(assets, files, series)
    if weather_finding:
        findings.append(weather_finding)

    outages = _read_outages(files, service_areas, findings)

    # Defect 6 — the failure history comes from outages.csv and from nowhere else. The
    # maintenance file is read only so the loader can say what it excluded.
    scheduled = [
        (row.get("asset_id") or "").strip()
        for row in _rows(files, "maintenance.csv")
        if defects.looks_like_scheduled_work(row.get("notes"))
    ]
    excluded = defects.repair_rows_excluded(len(scheduled), scheduled)
    if excluded:
        findings.append(excluded)

    # Defect 7 — rows that name no asset are kept at area level, never attributed to a guess.
    unattributed = defects.area_level_only(sum(o.asset_external_id is None for o in outages))
    if unattributed:
        findings.append(unattributed)

    return LoadResult(
        scenario_id=manifest["scenario_id"],
        storm_name=manifest["storm_name"],
        forecast_issued_at=manifest["forecast_issued_at"],
        assets=assets,
        forecast_revisions=series,
        outages=outages,
        failures=[o for o in outages if o.asset_external_id],
        service_areas=service_areas,
        findings=findings,
    )
