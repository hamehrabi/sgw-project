"""EVAL-001 — the quality floor from `ai-evals.md`.

Runs in **its own harness, not the pytest folders** — `executable-tests.md` is explicit about
why: an eval scores a distribution against a threshold, and forcing that through the same
runner as `assertEqual` produces either a flaky suite or one that asserts nothing.

    python ci/evals.py        # exit 0 = the floor held; exit 1 = block the release

**Eight of the nine scorers are deterministic**, which is easier here than in a model-based
system: a rule produces a reproducible output, so almost everything worth checking can be
checked exactly. What this harness will not do is pretend to measure the one that cannot be
measured yet — see `failure_recall_at_decile` below.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "ci")]

from app.loader.load import load_scenario  # noqa: E402
from app.scoring.rank import rank_assets  # noqa: E402
from synthetic import synthetic_scenario  # noqa: E402

FIXTURE = ROOT / "spec" / "03-tests" / "05-executable" / "fixtures" / "storm-with-seven-defects"
STALE_AFTER_DAYS = 365


def hand_written():
    return {p.name: p.read_bytes() for p in FIXTURE.iterdir()}


# --- The scorers, one per metric ------------------------------------------------------------
# Each returns (passed, measured, detail). The engine below runs any of them against any
# scenario, which is the split `ai-evals.md` §2 asks for: one general engine, specialised
# scorers at the edges. A new metric costs a function, not a change to the harness.


def every_rank_has_reasons(ranked, _result):
    scored = [item for item in ranked if item.score is not None]
    with_reasons = [item for item in scored if item.reasons]
    return len(with_reasons) == len(scored), _ratio(len(with_reasons), len(scored)), (
        f"{len(with_reasons)}/{len(scored)} ranked items carry at least one reason"
    )


def unscorable_surfaced(ranked, result):
    """Every asset the rule could not score appears, marked, with its reason."""
    surfaced = [i for i in ranked if i.score is None and i.unscored_reason and i.rank is None]
    unscorable = [i for i in ranked if i.score is None]
    present = len(ranked) == len(result.assets)
    return (
        present and len(surfaced) == len(unscorable),
        _ratio(len(surfaced), len(unscorable)),
        f"{len(surfaced)}/{len(unscorable)} surfaced; {len(ranked)}/{len(result.assets)} present",
    )


def order_is_reproducible(_ranked, result):
    orders = [
        [item.external_ids[0] for item in rank_assets(result.assets)] for _ in range(3)
    ]
    identical = orders[0] == orders[1] == orders[2]
    return identical, 1.0 if identical else 0.0, "three runs, identical order" if identical else (
        "the same input produced different orders"
    )


def stale_inputs_disclosed(ranked, _result):
    """A rank resting on a value older than a year must say so in its reasons."""
    from datetime import date

    owed = disclosed = 0
    for item in ranked:
        if item.score is None or not item.condition_observed_at:
            continue
        age = (date.today() - date.fromisoformat(item.condition_observed_at)).days
        if age < STALE_AFTER_DAYS:
            continue
        owed += 1
        condition = next((r for r in item.reasons if r.factor == "condition_decayed"), None)
        if condition and item.condition_observed_at in condition.detail:
            disclosed += 1
    return disclosed == owed, _ratio(disclosed, owed), (
        f"{disclosed}/{owed} ranks resting on a value over a year old state its age"
    )


def no_invented_factors(ranked, _result):
    """ADR-009 rule 3, and FF-007. No model yet — this guards the computed text today and
    the model's output unchanged on the day one arrives."""
    from app.scoring import references

    bad = []
    for item in ranked:
        for reason in item.reasons:
            if reason.factor not in references.WEIGHTS:
                bad.append(f"{item.external_ids[0]}:{reason.factor}")
            elif item.score:
                share = reason.contribution / item.score
                expected = (
                    "Strong" if share >= references.STRENGTH_STRONG_AT
                    else "Moderate" if share >= references.STRENGTH_MODERATE_AT
                    else "Slight"
                )
                if reason.strength != expected:
                    bad.append(f"{item.external_ids[0]}:{reason.factor} claims {reason.strength}")
    return not bad, len(bad), f"{len(bad)} reasons unmatched to their input" + (
        f" — {bad[:3]}" if bad else ""
    )


def _ratio(part, whole):
    return 1.0 if whole == 0 else part / whole


SCORERS = {
    "every_rank_has_reasons": (every_rank_has_reasons, "100%"),
    "unscorable_surfaced": (unscorable_surfaced, "100%"),
    "order_is_reproducible": (order_is_reproducible, "100%"),
    "stale_inputs_disclosed": (stale_inputs_disclosed, "100%"),
    "no_invented_factors": (no_invented_factors, "0"),
}

# --- What this harness deliberately does not measure -----------------------------------------
NOT_MEASURABLE = {
    "failure_recall_at_decile": (
        "no real per-asset failure history exists (assumption A7). `ai-evals.md` §1 requires "
        "the golden set to come from REPLAYED HISTORICAL STORMS where the outcome is known — "
        "scoring this against generated failures would measure whether the rule can rediscover "
        "the correlation the generator was written with. The 0.7 floor stays unearned, and "
        "product-spec.md §4 already refuses it as a version-one success metric"
    ),
}
NOT_APPLICABLE = {
    "no_asset_identifiers_in_prompt": "no provider is configured — there is no prompt yet "
    "(Q-029, Q-030)",
    "renders_without_provider": "there is no provider to be without; every ranking already "
    "renders from computed text alone",
    "reasons_are_faithful": "human, sampled at 10% — not automatable, and the one that matters "
    "most under ADR-005",
}

GOLDEN_SET = {
    "EV-hand-written: eight assets, all seven defects": hand_written,
    "EV-demo-scale: 220 assets, all seven defects": lambda: synthetic_scenario(assets=220),
}


def main() -> int:
    failures = []
    for case_name, build in GOLDEN_SET.items():
        result = load_scenario(build())
        ranked = rank_assets(result.assets)
        print(f"\n{case_name}")
        for name, (scorer, floor) in SCORERS.items():
            passed, _measured, detail = scorer(ranked, result)
            print(f"  {'PASS' if passed else 'FAIL'}  {name:<26} floor {floor:<5} {detail}")
            if not passed:
                failures.append(f"{case_name} :: {name} — {detail}")

    print("\nNot measured, and why:")
    for name, why in {**NOT_MEASURABLE, **NOT_APPLICABLE}.items():
        print(f"  ----  {name}: {why}")

    if failures:
        print("\nQUALITY FLOOR BREACHED — blocks release")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print(f"\nQUALITY FLOOR HELD ({len(SCORERS)} scorers x {len(GOLDEN_SET)} cases)")
    print("The recall floor remains UNEARNED. This is not a validated capability.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
