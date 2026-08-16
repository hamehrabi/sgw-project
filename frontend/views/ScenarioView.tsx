'use client'

/**
 * The screen TASK-002 delivers: load a storm, then read it.
 *
 * Composition only — every rule it obeys belongs to the component that owns it. The banner
 * decides staleness, the notice decides integrity, the table decides how a value renders.
 * Nothing here computes anything about an asset.
 *
 * **One failed read is one failed panel** (CHG-027). Three requests fill this screen and they
 * used to share a single `try`, so a 404 from the ranking replaced the ranking, the asset table
 * *and* the forecast control with one error message — while `RecommendationDecision` stayed on
 * screen offering accept / change / reject against a `recommendation_id` whose list was no
 * longer there. That last part is the dangerous one: a decision is a decision about a ranking,
 * and BR-001 means a person decides *while looking at it*. So each read now settles on its own,
 * a ranking that could not be read is **cleared** rather than left standing beside a newer
 * revision number, and the control stays on screen because it is the way back.
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

type Panel = 'loading' | 'ready' | 'error'

export function ScenarioView({ role }: { role: Role }) {
  const [scenarioId, setScenarioId] = useState<string | null>(null)
  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [page, setPage] = useState<AssetPage | null>(null)
  const [ranking, setRanking] = useState<Ranking | null>(null)
  const [assetState, setAssetState] = useState<Panel>('ready')
  const [rankingState, setRankingState] = useState<Panel>('ready')
  // Which forecast revision is on screen. `null` means "whichever is current" — an operator
  // who has not gone looking should always be reading the latest advice.
  const [viewing, setViewing] = useState<number | null>(null)

  const read = useCallback(async (id: string, revision: number | null) => {
    setAssetState('loading')
    setRankingState('loading')
    const [detail, assets, risks] = await Promise.allSettled([
      scenarios.read(id),
      scenarios.assets(id),
      scenarios.risks(id, revision ?? undefined),
    ])

    // The storm is still loaded; only a read failed. Never a blank frame, and never one
    // panel's failure standing in for another's.
    if (detail.status === 'fulfilled') setScenario(detail.value)
    if (assets.status === 'fulfilled') setPage(assets.value)
    setRanking(risks.status === 'fulfilled' ? risks.value : null)
    setAssetState(assets.status === 'fulfilled' ? 'ready' : 'error')
    setRankingState(risks.status === 'fulfilled' ? 'ready' : 'error')
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
          {/* Rendered from the scenario alone, and deliberately not from the ranking: it is
              the way back to an order that can be read, so it has to survive a read that
              could not be. */}
          {scenario && (
            <ForecastRevisionControl
              scenario={scenario}
              viewing={ranking?.forecast_revision ?? viewing ?? scenario.forecast_revision}
              onView={setViewing}
            />
          )}
          <RiskList ranking={ranking} state={rankingState} />
          {/* No ranking on screen, no decision offered against it (BR-001). */}
          {ranking && rankingState === 'ready' && (
            <RecommendationDecision recommendationId={ranking.recommendation_id} />
          )}

          {/* The during-storm half of the same problem, and a separate list on purpose: risk
              orders the planning list above, and nothing on the board is ordered by a score. */}
          <h2>Damage and repair</h2>
          <DispatchBoard scenarioId={scenarioId} />

          <h2>All assets</h2>
          <AssetTable page={page} state={assetState} />
        </>
      ) : (
        <p data-testid="no-storm">No storm loaded yet.</p>
      )}
    </>
  )
}
