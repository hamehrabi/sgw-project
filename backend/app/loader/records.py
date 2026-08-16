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
    # Which uploaded file the check actually read (CHG-047). Set where the rule runs,
    # never inferred later: defect 3 is measured in whichever file carried the gusts, and
    # a rule that names a file it did not read is wrong the moment a scenario is shaped
    # differently.
    affected_file: str = ""


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
    # CON-003's one permitted boolean about an asset (CHG-050). Optional in the file;
    # absent reads as false, because "critical" is a claim somebody made, not a default.
    is_critical_facility: bool = False


@dataclass(frozen=True)
class LoadedForecast:
    """One grid cell's forecast, and **when that value was issued**.

    `valid_time` is not always the revision's own time. A cell with no row at a later forecast
    keeps the value it last had, and BR-003 requires the age of a value to travel with it — a
    six-hour-old gust rendered as current is the quiet wrongness REQ-NF-003 exists to prevent.
    """

    grid_cell_id: str
    valid_time: str
    wind_gust_mph: float | None = None
    rainfall_in: float | None = None


@dataclass(frozen=True)
class ForecastRevision:
    """One forecast time, as a complete grid (CHG-025).

    REQ-F-004's change is *inside* the prepared scenario: `weather.csv` carries a `valid_time`
    per row, and each distinct time among the cell-level rows is one revision, numbered from 0
    in chronological order.
    """

    forecast_revision: int
    valid_time: str
    cells: tuple[LoadedForecast, ...] = ()


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
    # Chronological, revision 0 first. Revision 0 is the forecast the assets above carry, so
    # the two can never disagree about what was loaded (CHG-025).
    forecast_revisions: list[ForecastRevision] = field(default_factory=list)
    outages: list[LoadedOutage] = field(default_factory=list)
    failures: list[LoadedOutage] = field(default_factory=list)
    service_areas: dict[str, int] = field(default_factory=dict)
    # Optional names for the areas above, keyed the same way (CHG-049: a depot is a
    # service area, and the manifest may give it a human name).
    service_area_names: dict[str, str] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    # Defect 1's withheld merges, both sides kept (CHG-048): what the loader deferred to
    # a person, in the shape the review drawer shows. Each entry names the asset row it
    # concerns, the record already at the site, and the record the merge was withheld
    # from — because `needs_review` alone told the person nothing to review.
    match_candidates: list[dict] = field(default_factory=list)
    # CHG-051: the utility's own design basis, keyed by asset type, when the manifest
    # carries one. The scorer reads this first and falls back to CHG-014's sourced table.
    design_references: dict = field(default_factory=dict)


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
