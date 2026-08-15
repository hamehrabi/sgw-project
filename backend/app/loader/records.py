"""What a load produces.

Plain data. The loader is a pure function over parsed rows — it reads no request, knows about
no screen, and writes nowhere. `api/` stores what comes back.
"""

from dataclasses import dataclass, field


@dataclass
class Finding:
    """One defect, caught by its own check, named.

    `defect` is the row number in `data-and-integration-spec.md` §4. FF-006 counts distinct
    values here against a fixture that deliberately carries all seven.
    """

    defect: int
    code: str
    subject: str
    message: str


@dataclass
class LoadedAsset:
    external_ids: list[str]
    name: str
    type: str
    lat: float
    lon: float
    install_year: int | None = None
    flood_zone: str | None = None
    condition: str | None = None
    condition_source: str | None = None
    condition_observed_at: str | None = None
    # BR-003's display half, decided at load: a screen cannot render a distinction it was
    # never told about.
    condition_estimated: bool = False
    grid_cell_id: str | None = None
    wind_gust_mph: float | None = None
    rainfall_in: float | None = None
    # AC-001: 'matched' or 'needs_review'. Never dropped, never merged on a guess.
    match_status: str = "matched"


@dataclass
class LoadedOutage:
    """A historical outage row. Replay only — it feeds nothing at run time."""

    asset_external_id: str | None
    failure_time: str
    storm_id: str
    customers_out: int | None
    service_area_id: str | None
    percentage_out: float | None = None
    source_file: str = "outages.csv"


@dataclass
class LoadResult:
    scenario_id: str
    storm_name: str
    forecast_issued_at: str
    assets: list[LoadedAsset] = field(default_factory=list)
    outages: list[LoadedOutage] = field(default_factory=list)
    failures: list[LoadedOutage] = field(default_factory=list)
    service_areas: dict[str, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)


class LoadFailed(Exception):
    """The load fails whole, naming the file and the stage.

    A half-loaded storm is worse than a refused one, because it looks complete
    (`technical-spec.md` §9.1). Nothing partial is ever left behind.
    """

    def __init__(self, file: str, stage: str, reason: str) -> None:
        super().__init__(f"{file}: {reason} (stage: {stage})")
        self.file = file
        self.stage = stage
        self.reason = reason
