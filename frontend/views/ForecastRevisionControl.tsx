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
 * - **Every revision the storm carries stays selectable, by its forecast time.** That is the
 *   *comparison* half, and it is the reason this is a list rather than a single button: an
 *   operator who placed a crew against revision 0 has to be able to go back and see what they
 *   were looking at when they did.
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

  return (
    <section className="revisions" data-testid="forecast-revisions">
      <div>
        <strong>Forecast revision {scenario.forecast_revision}</strong>
        {viewing !== scenario.forecast_revision && (
          <span data-testid="viewing-earlier">
            {' '}
            — you are reading revision {viewing}, kept for comparison. It has not changed.
          </span>
        )}
      </div>

      <button
        type="button"
        onClick={apply}
        disabled={state === 'applying' || nothingFurther}
        data-testid="apply-forecast"
      >
        {state === 'applying' ? 'Re-ranking…' : 'Apply the next forecast change'}
      </button>

      {nothingFurther && (
        <p data-testid="no-further-forecast">
          This storm carries no forecast after revision {scenario.forecast_revision}. A newer
          forecast arrives by loading a newer prepared scenario.
        </p>
      )}

      {state === 'error' && (
        <p role="alert" data-testid="forecast-error">
          {message}
        </p>
      )}

      <ul className="revisions__list">
        {scenario.forecast_revisions.map((entry) => (
          <li key={entry.forecast_revision}>
            <button
              type="button"
              onClick={() => onView(entry.forecast_revision)}
              aria-current={entry.forecast_revision === viewing}
              data-testid={`view-revision-${entry.forecast_revision}`}
            >
              Revision {entry.forecast_revision}
            </button>{' '}
            <span className="revisions__time">forecast for {entry.valid_time}</span>
            {entry.forecast_revision === scenario.forecast_revision && (
              <span className="badge"> current</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
