"""A prepared scenario at demo scale, generated.

Q-017 fixes the shape: 220 assets, ~2,000 maintenance rows, ~5,000 forecast rows, ~300 outage
rows, under 5 MB. The hand-written eight-asset fixture proves the *rules*; this proves the
system holds at the size it will actually see (PTEST-001).

**Seeded, so it is byte-identical every run.** A performance test whose input changes between
runs measures the generator as much as the code, and `order_is_reproducible` could not be
asserted against it at all.

**This is not a golden set and must never be used as one.** `ai-evals.md` §1 requires the
golden set to come from *replayed historical storms where the outcome is known* — not invented
cases. Scoring `failure_recall_at_decile` against generated failures would measure whether the
rule can rediscover the correlation the generator was written with, which is the eval-shaped
version of training on the fixture that ADR-005 rejects.
"""

import json
import random
from datetime import date, timedelta

TYPES = ("substation", "line", "plant", "pump")
FLOOD_ZONES = ("VE", "AE", "X", "X", "AE")
SERVICE_AREAS = [
    {"service_area_id": f"SA-{index:02d}", "customer_count": 4000 + index * 850}
    for index in range(1, 13)
]
ISSUED_AT = "2026-08-15T00:00:00Z"
TODAY = date(2026, 8, 15)


def synthetic_scenario(
    *, assets: int = 220, forecast_rows: int = 5000, maintenance_rows: int = 2000,
    outage_rows: int = 300, seed: int = 7,
) -> dict[str, bytes]:
    rng = random.Random(seed)
    cells = [f"GC-{index:03d}" for index in range(1, 41)]

    asset_rows, cell_of = [], {}
    for index in range(1, assets + 1):
        code = f"AS-{index:04d}"
        kind = TYPES[index % len(TYPES)]
        cell_of[code] = cells[index % len(cells)]

        # Two assets in every hundred carry no condition at all — the unscorable path has to
        # exist at scale, not only in the small fixture (FTEST-004).
        unscorable = index % 50 == 0
        observed = TODAY - timedelta(days=rng.randint(60, 2190))
        rating = "" if unscorable else str(rng.randint(1, 5))
        source = "" if unscorable else ("estimated" if index % 9 == 0 else "inspection")
        # Defect 1 at scale. Every 25th asset shares a site and type with its predecessor but
        # carries a different name — a near match, which must be flagged rather than merged
        # (AC-001). Without these the generated scenario would carry six of the seven defects
        # and quietly look like a clean dataset.
        near_match = index % 25 == 0
        site = index - 1 if near_match else index
        asset_rows.append(
            ",".join(
                [
                    code,
                    f"Asset {site} annex" if near_match else f"Asset {index}",
                    TYPES[site % len(TYPES)] if near_match else kind,
                    f"{33.7 + (site % 40) * 0.01:.4f}",
                    f"{-118.5 + (site % 37) * 0.01:.4f}",
                    str(rng.randint(1960, 2020)),
                    FLOOD_ZONES[index % len(FLOOD_ZONES)],
                    rating,
                    source,
                    "" if unscorable else observed.isoformat(),
                ]
            )
        )

    # Asset-linked rows carry no gust (defect 3); the grid cell rows carry one everywhere.
    weather_rows = [f"{cell_of[f'AS-{i:04d}']},AS-{i:04d},{ISSUED_AT},,{rng.random():.2f}"
                    for i in range(1, assets + 1)]
    for cell in cells:
        weather_rows.append(f"{cell},,{ISSUED_AT},{rng.randint(45, 135)},{rng.random():.2f}")
    # The remaining rows are LATER forecasts for the same grid — which is what a prepared
    # scenario's ~5,000 forecast rows are for, and what REQ-F-004 re-ranks against (CHG-025).
    # They were dated 12-14 August against an issue time of the 15th, so the storm's own
    # "revision 0" was a forecast issued three days before the one the manifest names.
    while len(weather_rows) < forecast_rows:
        cell = rng.choice(cells)
        stamp = f"2026-08-1{rng.randint(5, 7)}T{rng.randint(10, 23)}:00:00Z"
        weather_rows.append(f"{cell},,{stamp},{rng.randint(40, 130)},{rng.random():.2f}")

    maintenance = []
    for index in range(maintenance_rows):
        code = f"AS-{rng.randint(1, assets):04d}"
        when = TODAY - timedelta(days=rng.randint(60, 2190))
        note = "REPAIR ORDER - replaced hardware" if index % 40 == 0 else "Inspection logged"
        maintenance.append(f"{code},{when.isoformat()},{rng.randint(1, 5)},{note}")

    outages = []
    for index in range(outage_rows):
        area = SERVICE_AREAS[index % len(SERVICE_AREAS)]
        code = "" if index % 30 == 0 else f"AS-{rng.randint(1, assets):04d}"
        out = 0 if index % 17 == 0 else rng.randint(50, area["customer_count"] - 1)
        if index % 61 == 0:
            out = area["customer_count"] + 500  # defect 5, at scale
        stamp = f"2024-09-2{rng.randint(0, 9)}T0{rng.randint(0, 9)}:00:00Z"
        outages.append(f"{code},{stamp},STORM-2024-REPLAY,{out},{area['service_area_id']}")

    files = {
        "assets.csv": "asset_id,name,type,lat,lon,install_year,flood_zone,condition_rating,"
        "condition_source,condition_date\n" + "\n".join(asset_rows) + "\n",
        "weather.csv": "grid_cell_id,asset_id,valid_time,wind_gust_mph,rainfall_in\n"
        + "\n".join(weather_rows) + "\n",
        "maintenance.csv": "asset_id,inspection_date,condition_rating,notes\n"
        + "\n".join(maintenance) + "\n",
        "outages.csv": "asset_id,failure_time,storm_id,customers_out,service_area_id\n"
        + "\n".join(outages) + "\n",
    }
    manifest = {
        "scenario_id": "STORM-SYNTHETIC-DEMO-SCALE",
        "storm_name": "Synthetic storm at demo scale",
        "forecast_issued_at": ISSUED_AT,
        "files": sorted(files),
        "row_counts": {
            name: len([line for line in text.strip().split("\n")[1:] if line])
            for name, text in files.items()
        },
        "service_areas": SERVICE_AREAS,
    }
    return {"manifest.json": json.dumps(manifest, indent=2).encode(),
            **{name: text.encode() for name, text in files.items()}}
