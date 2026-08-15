"""UTEST-007 — REQ-F-001. Defined in `03-tests/02-functional/unit-tests.md`.

Defect 5 — one county absorbs its neighbours' outages, showing more customers out than it
has.
  normal  — counts within the population pass
  edge    — a count equal to the population passes, with a flag
  failure — more customers out than exist → flagged at load, **by name**

"A range check that flags any impossible figure, at load time, by name" (§4). At load time,
because a defect caught at read is a defect already stored; by name, because a flag nobody
can trace to a row is a warning nobody can act on.
"""

from conftest import fixture_files


def load():
    from app.loader.load import load_scenario

    return load_scenario(fixture_files())


def test_a_count_inside_the_population_passes():
    result = load()

    impossible = [f for f in result.findings if f.defect == 5]

    assert not any("SS-1042" in f.subject for f in impossible)


def test_more_customers_out_than_exist_is_flagged():
    """7200 out of SA-COAST's 4500. The fixture's cross-area contamination."""
    result = load()

    impossible = [f for f in result.findings if f.defect == 5]

    assert impossible, "an impossible figure must be caught at load"
    assert any("PL-7788" in f.subject for f in impossible)


def test_the_flag_names_the_figure_and_the_population():
    result = load()

    finding = next(f for f in result.findings if f.defect == 5 and "PL-7788" in f.subject)

    assert "7200" in finding.message
    assert "4500" in finding.message


def test_a_count_equal_to_the_population_passes_with_a_flag():
    from app.loader.defects import outage_count_is_impossible

    assert outage_count_is_impossible(customers_out=4500, population=4500) is False
    assert outage_count_is_impossible(customers_out=4501, population=4500) is True


def test_an_impossible_count_does_not_stop_the_load():
    """It is a flag, not a parse failure. The storm does not pause for a bad row."""
    result = load()

    assert result.assets, "the scenario still loads"
    assert any(f.defect == 5 for f in result.findings)
