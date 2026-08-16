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

# --- The client's dialect (CHG-056) --------------------------------------------------------
#
# The Hurricane Delia pack is written to the client's own build prompt, and three real
# uploads of it were answered with a 500 before this table existed. The loader speaks
# both dialects BY NAMED ALIAS, never by guess: each field reads its CHG-011 name or its
# client-prompt name, and a type outside both vocabularies is still a refusal.

# The seven dialect type names, onto the four scoring categories. A written table: the
# mapping is a decision a reviewer can disagree with, not an inference.
TYPE_SYNONYMS: dict[str, str] = {
    "substation": "substation",
    "switchyard": "substation",
    "relay": "substation",
    "transformer": "substation",
    "line": "line",
    "distribution": "line",
    "transmission line": "line",
    "feeder": "line",
    "plant": "plant",
    "water treatment": "plant",
    "water plant": "plant",
    "pump": "pump",
    "pumping station": "pump",
    "pump station": "pump",
}

# Condition words, through the client's OWN severity equivalences — good 0.2, fair 0.55,
# poor 0.9 — mapped onto the 1–5 scale via severity = (5 - rating) / 5. Exact, so the
# scorer produces precisely the contribution the client's numbers specify.
CONDITION_WORDS: dict[str, str] = {"good": "4.0", "fair": "2.25", "poor": "0.5"}


def _rows(files: dict[str, bytes], name: str) -> list[dict]:
    try:
        text = files[name].decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise LoadFailed(name, "decode", "the file is not valid UTF-8 text") from error
    return list(csv.DictReader(io.StringIO(text)))


def _header(files: dict[str, bytes], name: str) -> list[str]:
    """The column names a CSV actually carries — how the dialect is detected."""
    try:
        text = files[name].decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise LoadFailed(name, "decode", "the file is not valid UTF-8 text") from error
    reader = csv.reader(io.StringIO(text))
    return [column.strip() for column in next(reader, [])]


def _field(row: dict, *names: str) -> str:
    """The first non-blank value among a field's dialect names."""
    for name in names:
        value = (row.get(name) or "").strip()
        if value:
            return value
    return ""


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


def _design_reference(references: dict, dialect_type: str) -> tuple[float | None, float | None]:
    """The basis the manifest states for this DIALECT type, matched case-insensitively.

    Resolved before the type collapses into a scoring category, because that collapse is
    exactly what loses the distinction the basis exists to draw (CHG-056).
    """
    for key, values in references.items():
        if str(key).strip().lower() == dialect_type and isinstance(values, dict):
            return (
                _number(str(values.get("design_gust_mph", "")), float),
                _number(str(values.get("service_life_years", "")), float),
            )
    return None, None


def _read_assets(files: dict[str, bytes], design_references: dict) -> list[LoadedAsset]:
    assets = []
    for row in _rows(files, "assets.csv"):
        code = _field(row, "asset_id", "external_id")
        dialect_type = _field(row, "type", "asset_type").lower()
        asset_type = TYPE_SYNONYMS.get(dialect_type)
        lat, lon = _number(row.get("lat"), float), _number(row.get("lon"), float)

        # §4: a record missing an identifier, a type and a location is rejected, not guessed at.
        if not code or asset_type is None or lat is None or lon is None:
            raise LoadFailed(
                "assets.csv",
                "validate",
                f"record '{code or '(no id)'}' lacks an identifier, a usable type, or a location",
            )

        source = (row.get("condition_source") or "").strip() or None
        condition = (row.get("condition_rating") or "").strip() or None
        observed = (row.get("condition_date") or "").strip() or None
        if condition and condition.lower() in CONDITION_WORDS:
            # The client's words, through the client's own severities — never a guess.
            condition = CONDITION_WORDS[condition.lower()]

        # BR-003 is enforced by the store; refusing it here too would let a bad row reach
        # the insert and fail there, which names the constraint rather than the file.
        if condition and not (source and observed):
            raise LoadFailed(
                "assets.csv",
                "validate",
                f"record '{code}' carries a condition with no source or no date (BR-003)",
            )

        design_gust, service_life = _design_reference(design_references, dialect_type)
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
                # Optional column (CHG-050). "1", "true" and "yes" are claims; everything
                # else — including absence — reads as false, because critical is asserted,
                # never defaulted.
                is_critical_facility=(row.get("is_critical_facility") or "")
                .strip()
                .lower()
                in ("1", "true", "yes"),
                design_gust_mph=design_gust,
                service_life_years=service_life,
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
    # Two shapes, detected by the header rather than guessed (CHG-056). CHG-011's file
    # keeps grid rows (no asset) apart from station rows; the client's file combines
    # them — every row carries the cell, the asset, the FORECAST gust and a mostly-empty
    # `station_gust_mph`. In the combined shape the grid series is every (cell, time)
    # pair's forecast gust; in the split shape it is the bare grid rows, exactly as
    # before.
    combined = "station_gust_mph" in _header(files, "weather.csv")

    observed: dict[str, dict[str, LoadedForecast]] = {}
    for row in _rows(files, "weather.csv"):
        cell = (row.get("grid_cell_id") or "").strip()
        code = _field(row, "asset_id", "external_id")
        when = (row.get("valid_time") or "").strip()
        # In the split shape, asset-linked rows say which cell an asset is in; their gust
        # column is the one the source PRD measured as 97% empty and is never a forecast
        # (defect 3). In the combined shape the gust column IS the forecast.
        if (code and not combined) or not cell or not when:
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
    combined = "station_gust_mph" in _header(files, "weather.csv")

    for row in _rows(files, "weather.csv"):
        cell = (row.get("grid_cell_id") or "").strip()
        code = _field(row, "asset_id", "external_id")
        if not code:
            continue
        # An asset-linked row says which cell the asset is in. The station reading is the
        # one the source PRD measured as 97% empty, and is deliberately never a forecast:
        # in the combined shape it has its own column; in the split shape it squats in
        # the gust column of asset-linked rows.
        station_rows += 1
        station_values += (
            _number(row.get("station_gust_mph" if combined else "wind_gust_mph"), float)
            is not None
        )
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
        code = _field(row, "asset_id", "external_id") or None
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


def _load_scenario(files: dict[str, bytes]) -> LoadResult:
    missing = [name for name in REQUIRED_FILES if name not in files]
    if missing:
        raise LoadFailed(missing[0], "validate", "required file is absent from the upload")

    manifest = _read_manifest(files)
    _check_row_counts(manifest, files)

    # The population figure reads its CHG-011 name or its client-prompt name
    # (`customers_served`), and a malformed block is a NAMED refusal — the exact area
    # shape that raised a raw KeyError here is the 500 CHG-056 was written against.
    raw_areas = manifest.get("service_areas", [])
    if not isinstance(raw_areas, list) or any(not isinstance(a, dict) for a in raw_areas):
        raise LoadFailed(
            "manifest.json", "validate", "service_areas must be a list of objects"
        )
    service_areas: dict[str, int] = {}
    service_area_names: dict[str, str] = {}
    for area in raw_areas:
        area_id = str(area.get("service_area_id") or "").strip()
        population = area.get("customer_count", area.get("customers_served"))
        if not area_id or not isinstance(population, int) or population < 0:
            raise LoadFailed(
                "manifest.json",
                "validate",
                f"service area '{area_id or '(no id)'}' needs a service_area_id and a "
                "whole-number customer_count (or customers_served)",
            )
        service_areas[area_id] = population
        if area.get("name"):
            service_area_names[area_id] = str(area["name"])

    design_references = manifest.get("design_references", {})
    if not isinstance(design_references, dict):
        raise LoadFailed(
            "manifest.json", "validate", "design_references must be an object keyed by asset type"
        )

    assets, match_candidates = merge_by_site_and_name(_read_assets(files, design_references))
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
    # maintenance file is read only so the loader can say what it excluded. With a
    # `work_type` column (the client's dialect) the file says so itself — only
    # `unplanned` rows are failure evidence, and the routine ones are what is excluded;
    # without one, the note text is matched as before.
    if "work_type" in _header(files, "maintenance.csv"):
        scheduled = [
            _field(row, "asset_id", "external_id")
            for row in _rows(files, "maintenance.csv")
            if (row.get("work_type") or "").strip().lower() != "unplanned"
        ]
    else:
        scheduled = [
            _field(row, "asset_id", "external_id")
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
        service_area_names=service_area_names,
        findings=findings,
        match_candidates=match_candidates,
        # CHG-051: the utility's own design basis, when the manifest states one. Read
        # here, stored with the scenario, read by the scorer first — CHG-014's sourced
        # table is the fallback, not the authority, the day the client supplies theirs.
        design_references=design_references,
    )


def load_scenario(files: dict[str, bytes]) -> LoadResult:
    """Parse a prepared storm — and fail ONLY as a named `LoadFailed` (CHG-056).

    A raw exception surfacing from user bytes is a 500 wearing a stack trace, and three
    real uploads were answered exactly that way. Whatever shape the bytes take, the
    refusal names a file, a stage and a reason — the person gets something to fix, never
    *Something went wrong*.
    """
    try:
        return _load_scenario(files)
    except LoadFailed:
        raise
    except Exception as error:
        raise LoadFailed(
            "(upload)",
            "parse",
            f"the file set does not match any prepared-scenario shape "
            f"({type(error).__name__} while parsing)",
        ) from error
