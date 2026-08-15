'use client'

/**
 * The scenario selector, in its empty state.
 *
 * `AppShell` requires it to be present always, "because everything below it is scoped to
 * one scenario". No scenario can exist yet — TASK-002 builds the upload and the parse — so
 * the only state reachable in this task is the empty one.
 *
 * The empty state reads "no storm loaded yet" and never renders as a scenario with no
 * risk. Three of this product's screens look like good news when they are blank, and that
 * is the failure `frontend-component-spec.md` names for each of them.
 *
 * `ScenarioSwitcher`'s loading, success and error states arrive with TASK-009, which is the
 * task that gives it something to switch between.
 */

export function ScenarioSelector() {
  return (
    <span className="scenario-selector" data-testid="scenario-selector">
      No storm loaded yet
    </span>
  )
}
