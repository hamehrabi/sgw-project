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
 *
 * **Which storm is on screen comes from the shell** (TASK-009). It is not this component's
 * state, because `frontend-component-spec.md` puts the selector in the frame *"because
 * everything below it is scoped to one scenario"* — and two owners of one scope is how two
 * storms end up blended into one view.
 *
 * **Two rules exist here for that reason, and neither is a nicety.**
 *
 * *Changing storm clears the screen first.* Storm A's asset table left standing under storm B's
 * name while B's reads are in flight is REQ-F-010's blend for as long as the network takes —
 * and `security-review.md` §4 is explicit that it has no visible symptom. So is the forecast
 * revision being read: a revision number means nothing in a different storm.
 *
 * *A superseded read is discarded.* Switching from A to B while A's reads are outstanding
 * would otherwise let A's slower response arrive last and paint A's rows under B's name. The
 * generation counter is what makes the last switch the one that wins, rather than the last
 * response.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import { AssetPage, Ranking, Role, Scenario, scenarios } from '@/lib/api'

import { AssetTable } from './AssetTable'
import { DispatchBoard } from './DispatchBoard'
import { ForecastRevisionControl } from './ForecastRevisionControl'
import { PlacementForm } from './PlacementForm'
import { RecommendationDecision } from './RecommendationDecision'
import { RiskList } from './RiskList'
import { ScenarioIntegrityNotice } from './ScenarioIntegrityNotice'
import { ScenarioUploadPanel } from './ScenarioUploadPanel'
import { StalenessBanner } from './StalenessBanner'

type Panel = 'loading' | 'ready' | 'error'

export function ScenarioView({
  role,
  scenarioId,
  loadedCount,
  onLoaded,
}: {
  role: Role
  scenarioId: string | null
  /** How many storms are loaded — so *none chosen* never renders as *none exist*. */
  loadedCount: number
  onLoaded: (scenarioId: string) => void
}) {
  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [page, setPage] = useState<AssetPage | null>(null)
  const [ranking, setRanking] = useState<Ranking | null>(null)
  const [assetState, setAssetState] = useState<Panel>('ready')
  const [rankingState, setRankingState] = useState<Panel>('ready')
  // Which forecast revision is on screen. `null` means "whichever is current" — an operator
  // who has not gone looking should always be reading the latest advice.
  const [viewing, setViewing] = useState<number | null>(null)
  // Which read is the current one. Incremented by every read; a response whose generation is
  // no longer the latest is dropped rather than rendered.
  const generation = useRef(0)

  const read = useCallback(async (id: string, revision: number | null) => {
    const mine = (generation.current += 1)
    setAssetState('loading')
    setRankingState('loading')
    const [detail, assets, risks] = await Promise.allSettled([
      scenarios.read(id),
      scenarios.assets(id),
      scenarios.risks(id, revision ?? undefined),
    ])
    // A newer storm or revision was chosen while these were in flight. Painting them now would
    // put one storm's rows under another storm's name (REQ-F-010).
    if (generation.current !== mine) return

    // The storm is still loaded; only a read failed. Never a blank frame, and never one
    // panel's failure standing in for another's.
    if (detail.status === 'fulfilled') setScenario(detail.value)
    if (assets.status === 'fulfilled') setPage(assets.value)
    setRanking(risks.status === 'fulfilled' ? risks.value : null)
    setAssetState(assets.status === 'fulfilled' ? 'ready' : 'error')
    setRankingState(risks.status === 'fulfilled' ? 'ready' : 'error')
  }, [])

  // The storm changed: nothing belonging to the previous one may stay on screen, and the
  // revision being read is one of the things that belonged to it.
  useEffect(() => {
    generation.current += 1
    setScenario(null)
    setPage(null)
    setRanking(null)
    setViewing(null)
    setAssetState('loading')
    setRankingState('loading')
  }, [scenarioId])

  useEffect(() => {
    if (scenarioId) void read(scenarioId, viewing)
  }, [scenarioId, viewing, read])

  return (
    <>
      <ScenarioUploadPanel role={role} onLoaded={onLoaded} />

      {scenario && (
        <>
          <StalenessBanner scenario={scenario} />
          <ScenarioIntegrityNotice integrity={scenario.integrity} role={role} />
        </>
      )}

      {scenarioId ? (
        <div data-testid="scenario-data">
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
          {/* No ranking on screen, no decision offered against it, and no placement made
              against it either (BR-001). Both are decisions about a list, and a person takes
              them while looking at one.

              Both are keyed by the storm and the revision, so switching to another storm — or
              to an earlier order for comparison — starts a fresh form rather than carrying a
              half-typed placement across to a list it was never meant for. */}
          {ranking && rankingState === 'ready' && (
            <>
              <RecommendationDecision
                key={`decision-${scenarioId}-${ranking.forecast_revision}`}
                recommendationId={ranking.recommendation_id}
              />
              <PlacementForm
                key={`placement-${scenarioId}-${ranking.forecast_revision}`}
                scenarioId={scenarioId}
                ranking={ranking}
              />
            </>
          )}

          {/* The during-storm half of the same problem, and a separate list on purpose: risk
              orders the planning list above, and nothing on the board is ordered by a score. */}
          <h2>Damage and repair</h2>
          <DispatchBoard key={`board-${scenarioId}`} scenarioId={scenarioId} />

          <h2>All assets</h2>
          <AssetTable page={page} state={assetState} />
        </div>
      ) : (
        <p data-testid="no-storm">
          {/* Two different facts, and they must not share a sentence. *Nothing is loaded* is
              something an admin can fix; *nothing is chosen* is one click away, and telling a
              reader the second in the first's words would send them to load a storm that is
              already there. */}
          {loadedCount === 0
            ? 'No storm loaded yet.'
            : `${loadedCount} storm(s) are loaded. Choose one above to work on it.`}
        </p>
      )}
    </>
  )
}
