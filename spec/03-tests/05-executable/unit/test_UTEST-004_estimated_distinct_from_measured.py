"""UTEST-004 — REQ-F-001, BR-003. Defined in `03-tests/02-functional/unit-tests.md`.

Defect 2, display half — estimated versus measured.
  normal  — a measured value renders as measured
  edge    — an estimated value renders visually distinct
  failure — an estimated value indistinguishable from measured → test fails

This file asserts the **data** half: the loader must carry the distinction out of the file,
because a screen cannot render a difference it was never told about. The rendering half is
`AssetTable`'s, and is asserted where the component is tested — the two halves fail
separately and for different reasons, which is why they are not one test.
"""

from conftest import fixture_files


def load():
    from app.loader.load import load_scenario

    return load_scenario(fixture_files())


def find(assets, external_id):
    return next(a for a in assets if external_id in a.external_ids)


def test_a_measured_condition_is_marked_measured():
    result = load()

    northgate = find(result.assets, "SS-1042")

    assert northgate.condition_source == "inspection"
    assert northgate.condition_estimated is False


def test_an_estimated_condition_is_marked_estimated():
    result = load()

    ridgeline = find(result.assets, "LN-3312")

    assert ridgeline.condition_source == "estimated"
    assert ridgeline.condition_estimated is True


def test_the_two_are_distinguishable_by_a_field_rather_than_by_convention():
    """A caller must not have to know that the string 'estimated' is special."""
    result = load()

    estimated = {a.condition_estimated for a in result.assets if a.condition_source}

    assert estimated == {True, False}, "the fixture must carry both, and both must be readable"


def test_an_absent_condition_is_not_reported_as_measured():
    """No value is not the same as a value nobody estimated."""
    result = load()

    coastal = find(result.assets, "LN-8899")

    assert coastal.condition is None
    assert coastal.condition_estimated is False
    assert coastal.condition_source is None
