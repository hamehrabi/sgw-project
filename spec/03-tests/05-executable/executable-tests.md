# 03-tests/ — Executable Tests

> Source: Front Matter workspace (`03-tests/unit`, `03-tests/integration`, `03-tests/end-to-end`) +
> Ch. 12 §12.4.

This folder holds the **runnable** tests. The written plans and specifications they come
from live in [`../tests/`](../01-plan/test-plan.md).

```
03-tests/
  unit/           # small behavior tests
  integration/    # API, database, and workflow tests
  end-to-end/     # complete user flows
```

**The three folders are empty.** No code exists, so no test does. Every id below is *Planned* in
its owning file, and this document is the mapping that says where each will land — written now,
before implementation, because a test written after the code tends to test what the code does
rather than what the requirement promised.

---

## Plan → executable mapping

| Plan document | Executable location |
|---|---|
| [`../tests/unit-tests.md`](../02-functional/unit-tests.md) | `unit/` |
| [`../tests/integration-tests.md`](../02-functional/integration-tests.md) | `integration/` |
| [`../tests/end-to-end-tests.md`](../02-functional/end-to-end-tests.md) | `end-to-end/` |
| [`../tests/security-tests.md`](../03-non-functional/security-tests.md) | `integration/` (negative cases) |
| [`../tests/edge-cases-and-failures.md`](../04-failure/edge-cases-and-failures.md) | matching level |
| [`../tests/acceptance-tests.md`](../02-functional/acceptance-tests.md) | `end-to-end/` or `integration/` |

Two plan documents are not in that table and land differently:

| Plan document | Executable location |
|---|---|
| [`../tests/ai-evals.md`](../03-non-functional/ai-evals.md) | Its own harness, not the test folders. Evals score a distribution against a threshold; forcing them through the same runner as `assertEqual` tests produces either a flaky suite or one that asserts nothing. |
| [`../tests/performance-tests.md`](../03-non-functional/performance-tests.md) | Run against a real prepared dataset, outside the ordinary suite. Both cases are **blocked** on Q-012 and Q-017. |

---

## Naming convention

Include the test ID and the requirement so a failure points straight at the spec:

```
unit/test_TEST-012_task_title_required.py
integration/test_TEST-021_viewer_cannot_export.py
end-to-end/test_TEST-030_create_task_flow.py
```

Applied to this project — the shape a reviewer should expect once the tasks land:

```
03-tests/05-executable/
  unit/
    test_UTEST-001_no_credential_in_logs.*
    test_UTEST-002_asset_codes_differ_across_systems.*
    test_UTEST-003_condition_carries_its_age.*
    test_UTEST-004_estimated_distinct_from_measured.*
    test_UTEST-005_gusts_from_forecast_grid.*
    test_UTEST-006_no_percentage_from_broken_total.*
    test_UTEST-007_impossible_outage_count_flagged.*
    test_UTEST-008_failures_not_from_repair_logs.*
    test_UTEST-009_score_refused_without_reasons.*
    test_UTEST-010_ranking_order_total_and_stable.*
    test_UTEST-011_dismissal_never_anonymous.*
    test_UTEST-012_damage_location_aggregated.*
  integration/
    test_ITEST-001_load_to_rank_with_all_seven_defects.*
    test_ITEST-002_second_decision_returns_409.*
    test_ITEST-003_two_reports_one_job.*
    test_ITEST-004_earlier_revision_returns_earlier_order.*
    test_ITEST-005_scenarios_never_blend.*
    test_STEST-001_signed_out_reaches_no_data.*
    test_STEST-002_expired_session_refused.*
    test_STEST-003_no_account_enumeration.*
    test_STEST-004_login_rate_limited_per_account.*
    test_STEST-005_user_cannot_upload_scenario.*
    test_STEST-006_content_inspection_not_extension.*
    test_STEST-007_user_cannot_read_decision_record.*
    test_STEST-008_database_refuses_decision_update.*
    test_STEST-009_no_household_location_leaves.*
    test_STEST-010_no_outbound_path_exists.*
    test_STEST-011_reset_does_not_change_role.*
    test_FTEST-001_partial_parse_creates_nothing.*
    test_FTEST-002_unreadable_file_shows_last_good.*
    test_FTEST-003_staleness_is_stated.*
    test_FTEST-004_unscorable_asset_surfaced.*
    test_FTEST-005_failed_write_keeps_typed_input.*
    test_FTEST-006_duplicate_decision_one_row.*
    test_FTEST-007_expired_session_no_crash.*
    test_FTEST-008_killed_parse_job_reports_stage.*
    test_FTEST-009_single_writer_contention.*
    test_FTEST-010_no_stack_trace_in_response.*
  end-to-end/
    test_ATEST-001_joined_view_with_source_and_age.*
    test_ATEST-002_broken_file_shows_last_good.*
    test_ATEST-003_every_asset_ranked.*
    test_ATEST-004_rank_never_without_reasons.*
    test_ATEST-005_reranking_keeps_previous_order.*
    test_ATEST-006_decision_recorded_no_dispatch.*
    test_ATEST-007_two_reports_one_job.*
    test_ATEST-008_decision_record_append_only.*
    test_ATEST-009_user_refused_scenario_load.*
    test_ATEST-010_staleness_stated_on_screen.*
    test_E2E-001_place_crews_against_ranking.*
    test_E2E-002_load_a_prepared_storm.*
```

---

## Rules

- **Tests come from acceptance criteria**, not from the code that was just written
  (Ch. 17 §17.1). Testing after code means you may accidentally test what the code already
  does instead of what the requirement promised.
- Every behavior change adds or updates a test (Ch. 11 §11.5).
- Security-sensitive paths need **negative** tests (Appendix P).
- Never delete or weaken a test to make code pass (Appendix H).
- Every fixed bug gets a regression test that **fails before** the fix and **passes after**
  (Ch. 19 §19.6).
- A test that asserts "something happened" instead of "the right thing happened" is a
  shallow test — strengthen the assertion (Ch. 18 §18.3).

**Three tests here sit at a level below the application and must stay there.** `STEST-008` issues
its statement against the database, not through a repository; `STEST-010` inspects the built
artifact rather than calling an endpoint; and `UTEST-009` asserts the store refuses the write.
Each of them is easy to "fix" into an application-level check that passes and proves nothing —
which is the failure their owning specifications each describe in their own words.

---

## Run commands

The runner is not chosen — no stack has been selected beyond ADR-001 and ADR-002, and CON-001
records that no technology is mandated. The **shape** of the commands is fixed regardless, and
the gate is what matters:

```
Unit only:        <runner> 03-tests/05-executable/unit
Integration:      <runner> 03-tests/05-executable/integration
End-to-end:       <runner> 03-tests/05-executable/end-to-end
Full gate:        <runner> 03-tests/05-executable  +  the six fitness functions
One requirement:  <runner> 03-tests/05-executable -k "UTEST-009 or ATEST-004"
```

**The full gate is the suite plus the fitness functions, not the suite alone.** FF-001 to FF-006
are defined in [`fitness-functions.md`](../../01-docs/04-technical-spec/fitness-functions.md),
every one currently marked `Not wired yet`, and TASK-010 is the task that wires them. A gate that
runs the tests and not the fitness functions verifies that the features work while the structure
they depend on is free to move.

> Naming files after the **test ID and requirement** is what makes a CI failure readable:
> `test_STEST-002_viewer_cannot_patch_task` points straight at the RBAC table row that
> broke, not at an anonymous line number.

---

> Blueprint: blueprints/03-tests/05-executable/executable-tests.md
