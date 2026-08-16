"""UTEST-009 — BR-002. Defined in `03-tests/02-functional/unit-tests.md`.

Rule under test: a score cannot exist without at least one reason.
  normal  — a scored asset carries ≥ 1 reason
  edge    — an asset with exactly one reason is valid
  failure — a score with an empty `reasons` array → **refused by the store, not by the caller**

The failure case is the one that matters and the one easiest to fake. `executable-tests.md`
names this test as sitting deliberately below the application: it asserts the *store* refuses
the write. A service-layer version of this check passes just as green and is removed by the
first refactor.

Also asserts the property ADR-005 makes non-negotiable: **reasons come out of the same
computation as the score.** Each one names a factor that actually contributed, and its strength
is that factor's share of the total — so a "Strong" label cannot attach to a 3% contribution.
"""

import sqlite3

import pytest
from conftest import fixture_files


def scored():
    from app.loader.load import load_scenario
    from app.scoring.rank import rank_assets

    return rank_assets(load_scenario(fixture_files()).assets)


def test_every_scored_asset_carries_at_least_one_reason():
    for item in scored():
        if item.score is not None:
            assert item.reasons, f"{item.external_ids} has a score and no reasons"


def test_every_reason_names_a_factor_the_rule_actually_computed():
    """No reason may name a factor outside the configured set — that is FF-007's rule.

    It does **not** require a non-zero contribution. A factor that scored zero still
    participated, and dropping it hid stale inputs: an asset rated 5/5 six years ago
    contributes nothing, so filtering it left the rank silent about a six-year-old
    inspection. The eval harness caught that; `stale_inputs_disclosed` is the floor it broke.
    """
    from app.scoring.references import WEIGHTS

    for item in scored():
        for reason in item.reasons:
            assert reason.factor in WEIGHTS
            assert reason.contribution >= 0


def test_a_factor_that_contributed_nothing_still_explains_itself():
    """The regression the eval found. Silence about a stale input is invisible on screen."""
    for item in scored():
        if item.score is None:
            continue
        assert {reason.factor for reason in item.reasons} == {
            "gust_vs_design",
            "flood_zone",
            "age_vs_service_life",
            "condition_decayed",
        }


def test_reason_strength_is_that_factors_share_of_the_score():
    """ADR-007: ≥ 25% Strong, 10–25% Moderate, < 10% Slight. Derived, never authored."""
    for item in scored():
        if item.score in (None, 0):
            continue
        for reason in item.reasons:
            share = reason.contribution / item.score
            expected = "Strong" if share >= 0.25 else "Moderate" if share >= 0.10 else "Slight"
            assert reason.strength == expected, (
                f"{reason.factor} contributed {share:.0%} and was labelled {reason.strength}"
            )


def test_the_contributions_sum_to_the_score():
    """The reasons are the arithmetic, not a commentary on it."""
    for item in scored():
        if item.score is None:
            continue
        assert abs(sum(r.contribution for r in item.reasons) - item.score) < 0.01


def test_an_unscorable_asset_has_no_score_and_still_has_its_reason():
    """FTEST-004's other half: UNSCORED is not the same as scoring zero."""
    unscored = [item for item in scored() if item.score is None]

    assert unscored, "the fixture carries an asset that cannot be scored"
    for item in unscored:
        assert item.unscored_reason
        assert item.rank is None


def one_rankable_storm(connection, admin_id) -> None:
    """A storm, one forecast revision and one asset — the smallest thing a ranking may hang off.

    The revision row is not decoration. Since CHG-028 a ranking carries a composite foreign key
    into `scenario_forecast_revisions`, so a `risk_scores` insert without one is refused for a
    reason that has nothing to do with BR-002 — and the refusal test below would then pass with
    the reasons constraint removed. That is the fifth-and-counting shape this repository keeps
    finding: an assertion that cannot fail for the reason it claims.
    """
    connection.execute(
        "insert into scenarios (id, name, source_note, loaded_by, loaded_at, forecast_revision)"
        " values ('SC-1', 'S', 'n', ?, '2026-08-15', 0)",
        (admin_id,),
    )
    connection.execute(
        "insert into scenario_forecast_revisions"
        " (scenario_id, forecast_revision, valid_time, created_at)"
        " values ('SC-1', 0, '2026-08-15T00:00:00Z', '2026-08-15')"
    )
    connection.execute(
        "insert into assets (id, scenario_id, external_ids, type, location, match_status,"
        " created_at) values ('A-1', 'SC-1', '[\"SS-1\"]', 'line', '{}', 'matched', '2026-08-15')"
    )


def test_the_store_refuses_a_score_with_no_reasons(application, accounts):
    """Asserted against the database. BR-002 is a constraint, not a convention."""
    connection = application.state.db
    one_rankable_storm(connection, accounts["admin"]["id"])

    with pytest.raises(sqlite3.IntegrityError) as refused:
        connection.execute(
            "insert into risk_scores (id, scenario_id, asset_id, forecast_revision, score,"
            " rank, reasons, weight_set_version, computed_at)"
            " values ('R-1', 'SC-1', 'A-1', 0, 55.0, 1, '[]', 'adr-007-v1', '2026-08-15')"
        )
        connection.commit()
    connection.rollback()

    # Refused by BR-002 in particular, and not by a foreign key the row happens also to miss.
    assert "CHECK constraint failed" in str(refused.value), (
        f"refused by something other than BR-002: {refused.value}"
    )


def test_the_store_accepts_a_score_that_carries_one_reason(application, accounts):
    """The edge case: exactly one reason is valid. Brevity is not the rule.

    It is also the permitted case beside the refusal above — the same insert differing in the
    one column the rule is about, so the refusal cannot be a malformed statement.
    """
    connection = application.state.db
    one_rankable_storm(connection, accounts["admin"]["id"])

    connection.execute(
        "insert into risk_scores (id, scenario_id, asset_id, forecast_revision, score, rank,"
        " reasons, weight_set_version, computed_at)"
        " values ('R-1', 'SC-1', 'A-1', 0, 55.0, 1,"
        " '[{\"factor\":\"flood_zone\"}]', 'adr-007-v1', '2026-08-15')"
    )
    connection.commit()

    assert connection.execute("select count(*) from risk_scores").fetchone()[0] == 1


def test_every_stored_ranking_records_the_weight_set_that_produced_it(application, accounts):
    """Done criterion 5. A recalibration must not silently rewrite history."""
    connection = application.state.db
    columns = {row[1] for row in connection.execute("pragma table_info(risk_scores)")}

    assert "weight_set_version" in columns
