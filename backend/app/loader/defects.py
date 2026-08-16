"""The seven defect rules from `data-and-integration-spec.md` §4.

These are not hypotheticals: the source PRD §7 measured each one in real public files of the
same kinds, and the shipped fixture injects all seven on purpose so the design is proven
against dirty data rather than clean data.

Every rule runs at **load** time. A defect caught at read is a defect already stored.

One function per rule, each independently testable, because FF-006's threshold is *7 of 7
caught by its own check* — a single pass that happens to notice several of them would satisfy
the wording and prove nothing about the sixth.
"""

from app.loader.records import Finding

ESTIMATED_SOURCES = frozenset({"estimated", "modelled", "modeled", "derived"})

# Defect 6: language that marks a maintenance row as a record of *completed repair work* —
# the kind that would inflate a failure history if anyone counted it. Recognising them is not
# how failures are found — failures come from `outages.csv` and nowhere else — it is how the
# loader can *say* what it excluded.
#
# "routine" and "scheduled" were here and are deliberately gone. They describe inspections
# and future plans, not repairs, so they matched "Routine inspection - no action" and made
# this check fire on any dataset containing an inspection — which is every dataset. A check
# that cannot be absent is not detecting anything.
REPAIR_MARKERS = ("repair order", "work order", "replaced", "repaired")


def condition_is_estimated(condition_source: str | None) -> bool:
    """Defect 2, display half — an estimated value must never look like a measured one."""
    return (condition_source or "").strip().lower() in ESTIMATED_SOURCES


def percentage_out(customers_out: int | None, population: int | None) -> float | None:
    """Defect 4 — refuse the percentage rather than publish a wrong one.

    Returns None when there is no independent population figure, or when the stored total is
    the broken zero the source PRD measured in 83% of rows. **A zero percentage is the
    dangerous output**: it renders as *nothing is out*.
    """
    if not population or customers_out is None or customers_out <= 0:
        return None
    return 100.0 * customers_out / population


def outage_count_is_impossible(customers_out: int | None, population: int | None) -> bool:
    """Defect 5 — more customers out than exist in the area.

    A count *equal* to the population is possible: everyone is out. Only more than that is
    arithmetic nobody can defend.
    """
    if customers_out is None or not population:
        return False
    return customers_out > population


def looks_like_scheduled_work(notes: str | None) -> bool:
    """Defect 6 — a maintenance row that describes planned work, not a failure."""
    return any(marker in (notes or "").lower() for marker in REPAIR_MARKERS)


def unmatched_codes(assets) -> Finding | None:
    """Defect 1 — the same asset carries different codes in different systems."""
    flagged = [a for a in assets if a.match_status == "needs_review"]
    if not flagged:
        return None
    names = ", ".join(sorted(code for a in flagged for code in a.external_ids))
    return Finding(
        defect=1,
        affected_file="assets.csv",
        code="ASSET_CODES_UNRESOLVED",
        subject=names,
        message=(
            f"{len(flagged)} record(s) could not be resolved to a single asset and are "
            f"flagged for a person: {names}. Never merged on a guess."
        ),
    )


def stale_condition(assets, *, stale_after_days: int = 365) -> Finding | None:
    """Defect 2 — condition data between two months and six years old."""
    dated = [a for a in assets if a.condition_observed_at]
    if not dated:
        return None
    oldest = min(dated, key=lambda a: a.condition_observed_at)
    return Finding(
        defect=2,
        affected_file="assets.csv",
        code="CONDITION_DATA_OLD",
        subject=", ".join(oldest.external_ids),
        message=(
            f"Oldest condition observation is {oldest.condition_observed_at}. Every condition "
            f"is stored with its source and its age and is never rendered as a current reading."
        ),
    )


def gusts_absent_from_station_rows(station_rows: int, station_values: int) -> Finding | None:
    """Defect 3 — station gust values are largely absent, so wind comes from the grid.

    Fires on *absence*, not on the existence of station rows. It returned a finding whenever
    `station_rows > 0`, so a file whose gusts were all present still reported the defect —
    detecting that weather.csv exists rather than that anything was missing from it.
    """
    missing = station_rows - station_values
    if station_rows == 0 or missing == 0:
        return None
    return Finding(
        defect=3,
        affected_file="weather.csv",
        code="STATION_GUSTS_ABSENT",
        subject="weather.csv",
        message=(
            f"{missing} of {station_rows} asset-linked weather rows carry no gust. Wind is "
            f"taken from the forecast grid square, which has a value everywhere."
        ),
    )


def broken_total(asset_code: str | None, service_area_id: str | None) -> Finding:
    """Defect 4 — a stored customer total that cannot support a percentage."""
    subject = asset_code or f"area {service_area_id}"
    return Finding(
        defect=4,
        affected_file="outages.csv",
        code="OUTAGE_TOTAL_BROKEN",
        subject=subject,
        message=(
            f"{subject} reports a customer total of zero. No percentage is published for it — "
            f"a zero percentage would read as 'nothing is out'."
        ),
    )


def impossible_count(asset_code: str | None, area: str, out: int, population: int) -> Finding:
    """Defect 5 — one area absorbing its neighbours' outages."""
    subject = asset_code or f"area {area}"
    return Finding(
        defect=5,
        affected_file="outages.csv",
        code="OUTAGE_COUNT_IMPOSSIBLE",
        subject=subject,
        message=(
            f"{subject} reports {out} customers out in {area}, which has {population}. "
            f"Flagged at load; the figure is not used."
        ),
    )


def repair_rows_excluded(count: int, subjects: list[str]) -> Finding | None:
    """Defect 6 — routine work mixed in with real failures."""
    if not count:
        return None
    return Finding(
        defect=6,
        affected_file="maintenance.csv",
        code="REPAIR_ROWS_NOT_FAILURES",
        subject=", ".join(sorted(subjects)),
        message=(
            f"{count} maintenance row(s) describe scheduled work. The failure history is built "
            f"from outages.csv alone and never from repair records."
        ),
    )


def area_level_only(count: int) -> Finding | None:
    """Defect 7 — public outage data is area-level and never names the failed asset."""
    if not count:
        return None
    return Finding(
        defect=7,
        affected_file="outages.csv",
        code="OUTAGE_AREA_LEVEL_ONLY",
        subject="outages.csv",
        message=(
            f"{count} outage row(s) name no asset. Kept at area level rather than attributed "
            f"to a guess — per-asset truth can only come from SGW's own records."
        ),
    )
