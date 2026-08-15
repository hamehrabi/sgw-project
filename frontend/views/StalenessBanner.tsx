'use client'

/**
 * StalenessBanner — states how old the data is, and says so loudly once it is old enough
 * to be wrong.
 *
 * Restated by CHG-013. Two rules, and the first is the one that is easy to get wrong:
 *
 * 1. **The age is stated always**, not only when it is bad (AC-010). A screen that mentions
 *    age only past a threshold teaches its reader that silence means fresh — so the day the
 *    banner fails to render, the absence reads as good news.
 * 2. Past `stale_after_hours` it becomes a **non-dismissible** banner. Six hours, because
 *    the National Hurricane Center issues full advisories every six: older than that and a
 *    newer forecast almost certainly exists and is not on this screen.
 *
 * It says nothing about missing files. A lost source file leaves the picture correct — that
 * is `ScenarioIntegrityNotice`'s job, and conflating them would report a screen as wrong
 * when it is right.
 */

import { Scenario } from '@/lib/api'

function describeAge(hours: number | null): string {
  if (hours === null) return 'of an unknown time'
  if (hours < 1) return `${Math.round(hours * 60)} minutes old`
  if (hours < 48) return `${hours.toFixed(1)} hours old`
  return `${Math.floor(hours / 24)} days old`
}

export function StalenessBanner({ scenario }: { scenario: Scenario }) {
  const age = describeAge(scenario.data_age_hours)
  const issued = scenario.forecast_issued_at ?? 'unknown'

  if (!scenario.stale) {
    return (
      <p className="data-age" data-testid="data-age">
        Forecast issued {issued} — {age}.
      </p>
    )
  }

  return (
    <div className="staleness" role="status" data-testid="staleness-banner">
      <strong>This picture is {age}.</strong> Forecast issued {issued}. Anything older than{' '}
      {scenario.stale_after_hours} hours means a newer forecast probably exists and is not
      shown here.
    </div>
  )
}
