"""UTEST-006 — REQ-F-001. Defined in `03-tests/02-functional/unit-tests.md`.

Defect 4 — outage records carry a broken customer total, 83% of rows zero in a real file.
  normal  — a percentage computed against an independent population figure
  edge    — total present and plausible → used
  failure — a total of zero → **no percentage is published**, not a zero percentage

"Refuse the percentage rather than publish a wrong one" (§4). A zero percentage is the
dangerous output here: it renders as *nothing is out*, which is the screen this product
exists to never show.

The independent figure comes from the manifest's `service_areas` block (CHG-011), never
from the outage rows themselves — a total cannot validate itself.
"""

from conftest import fixture_files


def load():
    from app.loader.load import load_scenario

    return load_scenario(fixture_files())


def outage_for(result, external_id):
    return next(o for o in result.outages if o.asset_external_id == external_id)


def test_a_plausible_total_yields_a_percentage():
    result = load()

    northgate = outage_for(result, "SS-1042")

    # 1850 of SA-NORTH's 12000
    assert northgate.customers_out == 1850
    assert northgate.percentage_out is not None
    assert round(northgate.percentage_out, 2) == 15.42


def test_a_zero_total_publishes_no_percentage_at_all():
    result = load()

    harbor = outage_for(result, "SS-2210")

    assert harbor.customers_out == 0
    assert harbor.percentage_out is None, "a zero percentage reads as 'nothing is out'"


def test_the_refusal_is_recorded_by_name():
    result = load()

    refusals = [f for f in result.findings if f.defect == 4]

    assert refusals
    assert any("SS-2210" in f.subject for f in refusals)


def test_the_percentage_is_computed_against_the_manifest_population():
    """Not against a total derived from the outage rows, which is the thing under suspicion."""
    result = load()

    assert result.service_areas["SA-NORTH"] == 12000
    assert result.service_areas["SA-COAST"] == 4500


def test_an_outage_in_an_unknown_service_area_publishes_no_percentage():
    """No independent figure means no percentage — the same rule, a different cause."""
    from app.loader.defects import percentage_out

    assert percentage_out(customers_out=500, population=None) is None
