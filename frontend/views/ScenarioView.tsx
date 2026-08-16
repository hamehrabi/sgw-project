'use client'

/**
 * The screen TASK-002 delivers: load a storm, then read it.
 *
 * Composition only — every rule it obeys belongs to the component that owns it. The banner
 * decides staleness, the notice decides integrity, the table decides how a value renders.
 * Nothing here computes anything about an asset.
 */

import { useCallback, useEffect, useState } from 'react'

import { AssetPage, Ranking, Role, Scenario, scenarios } from '@/lib/api'

import { AssetTable } from './AssetTable'
import { DispatchBoard } from './DispatchBoard'
import { ForecastRevisionControl } from './ForecastRevisionControl'
import { RecommendationDecision } from './RecommendationDecision'
import { RiskList } from './RiskList'
import { ScenarioIntegrityNotice } from './ScenarioIntegrityNotice'
import { ScenarioUploadPanel } from './ScenarioUploadPanel'
import { StalenessBanner } from './StalenessBanner'

export function ScenarioView({ role }: { role: Role }) {
  const [scenarioId, setScenarioId] = useState<string | null>(null)
  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [page, setPage] = useState<AssetPage | null>(null)
  const [ranking, setRanking] = useState<Ranking | null>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('ready')
  // Which forecast revision is on screen. `null` means "whichever is current" — an operator
  // who has not gone looking should always be reading the latest advice.
  const [viewing, setViewing] = useState<number | null>(null)

  const read = useCallback(async (id: string, revision: number | null) => {
    setState('loading')
    try {
      const [detail, assets, risks] = await Promise.all([
        scenarios.read(id),
        scenarios.assets(id),
        scenarios.risks(id, revision ?? undefined),
      ])
      setScenario(detail)
      setPage(assets)
      setRanking(risks)
      setState('ready')
    } catch {
      // The storm is still loaded; only this read failed. Never a blank frame.
      setState('error')
    }
  }, [])

  useEffect(() => {
    if (scenarioId) void read(scenarioId, viewing)
  }, [scenarioId, viewing, read])

  return (
    <>
      <ScenarioUploadPanel
        role={role}
        onLoaded={(id) => {
          setViewing(null)
          setScenarioId(id)
        }}
      />

      {scenario && (
        <>
          <StalenessBanner scenario={scenario} />
          <ScenarioIntegrityNotice integrity={scenario.integrity} role={role} />
        </>
      )}

      {scenarioId ? (
        <>
          {/* The ranking first: it is what the product competes on, and what an operator
              opened this screen for. The joined view is the evidence beneath it. */}
          <h2>Ranked by risk</h2>
          {scenario && ranking && (
            <ForecastRevisionControl
              scenario={scenario}
              viewing={ranking.forecast_revision}
              onView={setViewing}
            />
          )}
          <RiskList ranking={ranking} state={state} />
          {ranking && <RecommendationDecision recommendationId={ranking.recommendation_id} />}

          {/* The during-storm half of the same problem, and a separate list on purpose: risk
              orders the planning list above, and nothing on the board is ordered by a score. */}
          <h2>Damage and repair</h2>
          <DispatchBoard scenarioId={scenarioId} />

          <h2>All assets</h2>
          <AssetTable page={page} state={state} />
        </>
      ) : (
        <p data-testid="no-storm">No storm loaded yet.</p>
      )}
    </>
  )
}
