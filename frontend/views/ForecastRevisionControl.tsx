'use client'

/**
 * ForecastRevisionControl — apply the scenario's next forecast change, and compare orders.
 *
 * `frontend-component-spec.md`: *"The previous order stays reachable after re-ranking
 * (AC-005). Re-ranking never destroys what was shown before."* Both halves are visible here
 * rather than implied:
 *
 * - **Applying is one action**, and it is disabled while it runs and once the storm has no
 *   forecast left. A control that stayed live after the last revision would offer an action
 *   whose only possible answer is a refusal.
 * - **Every revision that has been ranked stays selectable, by its forecast time.** That is the
 *   *comparison* half, and it is the reason this is a list rather than a single button: an
 *   operator who placed a crew against revision 0 has to be able to go back and see what they
 *   were looking at when they did.
 *
 * **A forecast the storm carries is not the same thing as an order that can be read back**
 * (CHG-027). `GET /scenarios/{id}` lists the revisions in the prepared **file** — all of them,
 * from the moment the storm is loaded — and this list used to draw one selectable button per
 * entry. Pressing *Revision 2* on a freshly loaded storm therefore asked for a ranking that had
 * never been computed; the server answered the 404 `technical-spec.md` §7.3 requires, and
 * `ScenarioView` put the whole screen into an error state it never left: no ranking, no asset
 * table, the control still reading *revision 0 · current*, and accept / change / reject still
 * offered beside a list that was not there. A control must not offer an action whose only
 * possible answer is a refusal — the same rule the apply button already followed for the end of
 * the series. An unapplied revision is shown, and shown as **coming**: hiding it would lose the
 * one thing the operator most wants to know, which is that the weather moves again at 12:00.
 *
 * It computes nothing. The order, the scores and the bands all arrive from the server already
 * decided — no view imports the scoring module, and none reimplements it (FF-002).
 */

import { useState } from 'react'

import { RequestFailed, Scenario, scenarios } from '@/lib/api'

export function ForecastRevisionControl({
  scenario,
  viewing,
  onView,
}: {
  scenario: Scenario
  /** The revision currently on screen — not always the storm's current one. */
  viewing: number
  onView: (revision: number) => void
}) {
  const [state, setState] = useState<'idle' | 'applying' | 'error'>('idle')
  const [message, setMessage] = useState<string | null>(null)

  const nothingFurther = scenario.next_forecast_revision === null

  async function apply() {
    setState('applying')
    setMessage(null)
    try {
      const applied = await scenarios.applyNextForecast(scenario.scenario_id)
      setState('idle')
      // Move the reader onto the ranking they just asked for. The one they were reading is
      // still there, one button away — that is the whole of AC-005's second half.
      onView(applied.forecast_revision)
    } catch (failure) {
      // The storm still ranks at the revision it did before — the write is one transaction,
      // so a failure leaves no half-applied forecast behind.
      setState('error')
      setMessage(
        failure instanceof RequestFailed
          ? failure.message
          : 'We could not apply the forecast change. The current ranking is unaffected.',
      )
    }
  }

  // Forecasts the storm carries that nobody has applied. Real, and not comparable yet.
  const pending = scenario.forecast_revisions.filter((entry) => !entry.ranked)

  return (
    <section className="rounded-card border border-line bg-rail p-3 text-[13px]" data-testid="forecast-revisions">
      {/* CHG-057: one line, not a wall. The current revision, the one action, and the
          pending count — everything else waits behind the disclosure below. */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <strong>Forecast revision {scenario.forecast_revision}</strong>
        <button
          type="button"
          onClick={apply}
          disabled={state === 'applying' || nothingFurther}
          data-testid="apply-forecast"
          className="inline-flex h-8 items-center rounded-card border border-line bg-background px-3 text-[13px] font-medium hover:bg-panel disabled:pointer-events-none disabled:opacity-50"
        >
          {state === 'applying' ? 'Re-ranking…' : 'Apply the next forecast change'}
        </button>
        {/* The unapplied forecasts are still stated — CHG-027's point stands: a forecast
            that is coming is a real fact. Stated as a count, the size the fact deserves. */}
        {pending.length > 0 && (
          <span className="text-[12px] text-muted" data-testid="revisions-pending">
            {pending.length} of this storm&rsquo;s {scenario.forecast_revisions.length} forecasts
            not yet applied — the weather moves again.
          </span>
        )}
      </div>

      {viewing !== scenario.forecast_revision && (
        <p className="mt-2" data-testid="viewing-earlier">
          You are reading revision {viewing}, kept for comparison. It has not changed.
        </p>
      )}

      {nothingFurther && (
        <p data-testid="no-further-forecast" className="mt-2 text-[12px] text-muted">
          This storm carries no forecast after revision {scenario.forecast_revision}. A newer
          forecast arrives by loading a newer prepared scenario.
        </p>
      )}

      {state === 'error' && (
        <p role="alert" data-testid="forecast-error" className="mt-2 text-[12px] text-high-fg">
          {message}
        </p>
      )}

      {/* **Every revision the file carries stays reachable** — CHG-027's decision, one
        * click deeper (CHG-057): the two or three comparable orders matter on the day a
        * person comes back to compare, and the other twenty were burying the table the
        * rest of the time. A revision without an order behind it is offered only as
        * disabled, exactly as before — only the *comparison* does not exist yet. */}
      <details className="mt-2" data-testid="forecast-history">
        <summary
          className="cursor-pointer text-[12px] font-medium text-teal-deep hover:underline"
          data-testid="forecast-history-toggle"
        >
          Compare an earlier ranking
        </summary>
        <ul className="mt-2 flex max-h-24 flex-wrap items-center gap-x-3 gap-y-1.5 overflow-y-auto pr-1">
          {scenario.forecast_revisions.map((entry) => (
            <li key={entry.forecast_revision}>
              <button
                type="button"
                onClick={() => onView(entry.forecast_revision)}
                // Not yet applied means there is no stored ranking to fetch. Disabled rather
                // than hidden: the forecast is real and coming, and it is only the *comparison*
                // that does not exist yet.
                disabled={!entry.ranked}
                aria-current={entry.forecast_revision === viewing}
                title={`forecast for ${entry.valid_time}`}
                className={
                  entry.forecast_revision === viewing
                    ? 'inline-flex items-center rounded-full border border-teal bg-teal-soft px-2.5 py-0.5 text-[12px] font-medium text-teal-deep'
                    : 'inline-flex items-center rounded-full border border-line bg-background px-2.5 py-0.5 text-[12px] hover:bg-panel disabled:opacity-50'
                }
                data-testid={`view-revision-${entry.forecast_revision}`}
              >
                Rev {entry.forecast_revision}
                {entry.forecast_revision === scenario.forecast_revision && ' · current'}
              </button>
              <span className="ml-1 text-[11px] text-faint">{entry.valid_time}</span>
              {!entry.ranked && (
                <span
                  className="ml-1 text-[11px] italic text-faint"
                  data-testid={`revision-not-applied-${entry.forecast_revision}`}
                >
                  no order to compare
                </span>
              )}
            </li>
          ))}
        </ul>
      </details>
    </section>
  )
}
