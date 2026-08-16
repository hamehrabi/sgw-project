'use client'

/**
 * CrewStagingPlan — counts per depot that a person chose (CHG-049).
 *
 * A record and never an action: saving writes a row and nothing else. No crew is moved,
 * no roster is touched, no message leaves the platform, and there is no Apply button
 * because there is nothing for one to do.
 *
 * **No per-depot recommendation**, because none can be defended — assets carry no
 * service-area column, and inventing a mapping would be geography wearing arithmetic's
 * clothes. The high-band count is stated as context; the numbers are the operator's.
 */

import { Minus, Plus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { insights, RequestFailed, StagingPlan } from '@/lib/api'

export function CrewStagingPlan({
  scenarioId,
  forecastRevision,
}: {
  scenarioId: string
  forecastRevision: number
}) {
  const [plan, setPlan] = useState<StagingPlan | null>(null)
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)

  const read = useCallback(async () => {
    try {
      const body = await insights.staging(scenarioId)
      setPlan(body)
      setCounts(Object.fromEntries(body.depots.map((depot) => [depot.service_area_id, depot.crews])))
      setDirty(false)
    } catch {
      setProblem('We could not load the staging plan.')
    }
  }, [scenarioId])

  useEffect(() => {
    void read()
  }, [read])

  function nudge(areaId: string, by: number) {
    setCounts((current) => ({
      ...current,
      [areaId]: Math.max(0, (current[areaId] ?? 0) + by),
    }))
    setDirty(true)
  }

  async function save() {
    setSaving(true)
    setProblem(null)
    try {
      await insights.recordStaging(
        scenarioId,
        forecastRevision,
        Object.entries(counts).map(([service_area_id, crews]) => ({ service_area_id, crews })),
      )
      await read()
    } catch (error) {
      setProblem(
        error instanceof RequestFailed
          ? error.message
          : 'We could not record that. Nothing was saved — your counts are still here.',
      )
    } finally {
      setSaving(false)
    }
  }

  if (plan === null) {
    return (
      <p role="status" className="text-[13px] text-muted">
        Loading the staging plan…
      </p>
    )
  }
  if (plan.depots.length === 0) return null

  return (
    <Card data-testid="crew-staging">
      <CardHeader>
        <CardTitle>Crew staging plan</CardTitle>
        <p className="text-[12px] leading-relaxed text-muted">
          Where your crews wait before the storm arrives. Set a count per depot with the
          + and − controls, then <strong>Record plan</strong> — the plan becomes the crew
          total the Dispatch Board and the situation summary state, so those figures have
          an author instead of an assumption.
        </p>
        <p className="text-[12px] text-muted">
          {plan.high_risk_count} asset(s) rated High in the current ranking — context, not
          a recommendation. The counts are yours.
        </p>
        {plan.recorded_at && (
          <p className="text-[11px] text-faint">Last recorded {plan.recorded_at}.</p>
        )}
      </CardHeader>
      <CardContent className="space-y-2.5">
        {plan.depots.map((depot) => (
          <div key={depot.service_area_id} className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13px] font-medium leading-5">{depot.name}</p>
              <p className="text-[11px] text-muted">
                {depot.customer_count.toLocaleString()} customers served
              </p>
            </div>
            <div className="flex items-center rounded-card border border-line">
              <button
                type="button"
                aria-label={`Fewer at ${depot.name}`}
                className="px-2 py-1.5 text-muted hover:text-ink"
                onClick={() => nudge(depot.service_area_id, -1)}
              >
                <Minus className="h-3.5 w-3.5" aria-hidden />
              </button>
              <span className="w-8 text-center text-[14px] font-semibold">
                {counts[depot.service_area_id] ?? 0}
              </span>
              <button
                type="button"
                aria-label={`More at ${depot.name}`}
                className="px-2 py-1.5 text-muted hover:text-ink"
                onClick={() => nudge(depot.service_area_id, 1)}
              >
                <Plus className="h-3.5 w-3.5" aria-hidden />
              </button>
            </div>
          </div>
        ))}
        {problem && (
          <p role="alert" className="text-[12px] text-high-fg">
            {problem}
          </p>
        )}
      </CardContent>
      <CardFooter className="justify-between">
        <p className="text-[11px] leading-4 text-muted">
          Saving records the plan. No crew is moved and nothing is dispatched.
        </p>
        <Button size="sm" onClick={() => void save()} disabled={!dirty || saving}>
          {saving ? 'Recording…' : 'Record plan'}
        </Button>
      </CardFooter>
    </Card>
  )
}
