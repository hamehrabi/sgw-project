'use client'

/**
 * ScenarioView — composition root for the three surfaces: Load, Storm Planning,
 * Dispatch Board.
 *
 * Composition only — every rule it obeys belongs to the component that owns it. The
 * banner decides staleness, the notice decides integrity, the table decides how a value
 * renders. Nothing here computes anything about an asset.
 *
 * **One failed read is one failed panel** (CHG-027). Each read settles on its own; a
 * ranking that could not be read is cleared rather than left standing beside a newer
 * revision number, and the forecast control stays on screen because it is the way back.
 *
 * **Which storm is on screen comes from the shell** (TASK-009): two owners of one scope
 * is how two storms end up blended into one view (REQ-F-010).
 *
 * *Changing storm clears the screen first* — storm A's table under storm B's name while
 * B's reads are in flight is REQ-F-010's blend for as long as the network takes. *A
 * superseded read is discarded* — the generation counter makes the last switch the one
 * that wins, rather than the last response.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  AssetPage,
  AssetSummary,
  Movement,
  Ranking,
  RiskItem,
  Role,
  Scenario,
  insights,
  scenarios,
} from '@/lib/api'

import { Button } from '@/components/ui/button'

import { AssetDetailSheet } from './AssetDetailSheet'
import { AssetMatchSheet } from './AssetMatchSheet'
import { AssetTable } from './AssetTable'
import { CrewStagingPlan } from './CrewStagingPlan'
import { DataQualitySummary } from './DataQualitySummary'
import { DispatchSurface } from './DispatchSurface'
import { FocusMode } from './FocusMode'
import { ForecastRevisionControl } from './ForecastRevisionControl'
import { Headline } from './Headline'
import { RiskList } from './RiskList'
import { RiskMap } from './RiskMap'
import { ScenarioIntegrityNotice } from './ScenarioIntegrityNotice'
import { ScenarioUploadPanel } from './ScenarioUploadPanel'
import { StalenessBanner } from './StalenessBanner'
import { TopRiskStrip } from './TopRiskStrip'
import type { Surface } from './AppShell'

type Panel = 'loading' | 'ready' | 'error'

export function ScenarioView({
  role,
  scenarioId,
  loadedCount,
  onLoaded,
  surface,
  onFinish,
}: {
  role: Role
  scenarioId: string | null
  /** How many storms are loaded — so *none chosen* never renders as *none exist*. */
  loadedCount: number
  onLoaded: (scenarioId: string) => void
  surface: Surface
  /** "Finish and continue" — the Load surface's one door into the dashboards. */
  onFinish: () => void
}) {
  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [page, setPage] = useState<AssetPage | null>(null)
  const [ranking, setRanking] = useState<Ranking | null>(null)
  const [movement, setMovement] = useState<Movement | null>(null)
  // Every stored per-asset summary for this storm (CHG-059) — read with the ranking, so
  // a summary generated last session opens without a request, let alone an inference.
  const [storedSummaries, setStoredSummaries] = useState<AssetSummary[]>([])
  const [assetState, setAssetState] = useState<Panel>('ready')
  const [rankingState, setRankingState] = useState<Panel>('ready')
  // Which forecast revision is on screen. `null` means "whichever is current".
  const [viewing, setViewing] = useState<number | null>(null)
  const [openAsset, setOpenAsset] = useState<RiskItem | null>(null)
  const [triaging, setTriaging] = useState(false)
  const [reviewingMatches, setReviewingMatches] = useState(false)
  // Which read is the current one. A response whose generation is stale is dropped.
  const generation = useRef(0)

  const read = useCallback(async (id: string, revision: number | null) => {
    const mine = (generation.current += 1)
    setAssetState('loading')
    setRankingState('loading')
    const [detail, assets, risks, moved, summaries] = await Promise.allSettled([
      scenarios.read(id),
      scenarios.assets(id),
      scenarios.risks(id, revision ?? undefined),
      insights.movement(id),
      insights.assetSummaries(id),
    ])
    // A newer storm or revision was chosen while these were in flight (REQ-F-010).
    if (generation.current !== mine) return

    if (detail.status === 'fulfilled') setScenario(detail.value)
    if (assets.status === 'fulfilled') setPage(assets.value)
    setRanking(risks.status === 'fulfilled' ? risks.value : null)
    setMovement(moved.status === 'fulfilled' ? moved.value : null)
    setStoredSummaries(summaries.status === 'fulfilled' ? summaries.value.items : [])
    setAssetState(assets.status === 'fulfilled' ? 'ready' : 'error')
    setRankingState(risks.status === 'fulfilled' ? 'ready' : 'error')
  }, [])

  // The storm changed: nothing belonging to the previous one may stay on screen.
  useEffect(() => {
    generation.current += 1
    setScenario(null)
    setPage(null)
    setRanking(null)
    setMovement(null)
    setStoredSummaries([])
    setViewing(null)
    setOpenAsset(null)
    setTriaging(false)
    setAssetState('loading')
    setRankingState('loading')
  }, [scenarioId])

  useEffect(() => {
    if (scenarioId) void read(scenarioId, viewing)
  }, [scenarioId, viewing, read])

  // The stored summaries for the revision on screen, keyed by asset (CHG-059) — the
  // table's popup and the drawer read from one map, so they can never disagree.
  const summariesOnScreen = useMemo(() => {
    const map = new Map<string, AssetSummary>()
    const revision = ranking?.forecast_revision
    if (revision === undefined) return map
    for (const summary of storedSummaries) {
      if (summary.forecast_revision === revision) map.set(summary.asset_id, summary)
    }
    return map
  }, [storedSummaries, ranking?.forecast_revision])

  const keepSummary = useCallback((summary: AssetSummary) => {
    setStoredSummaries((current) =>
      current.some((held) => held.asset_summary_id === summary.asset_summary_id)
        ? current
        : [...current, summary],
    )
  }, [])

  // ---- Load surface -----------------------------------------------------------------

  if (surface === 'load' || !scenarioId) {
    return (
      <div className="mx-auto max-w-3xl space-y-5">
        <ScenarioUploadPanel role={role} onLoaded={onLoaded} />

        {!scenarioId && (
          <p data-testid="no-storm" className="text-[13px] text-muted">
            {/* Two different facts, never one sentence: *nothing is loaded* is something
                an admin can fix; *nothing is chosen* is one click away. */}
            {loadedCount === 0
              ? 'No storm loaded yet.'
              : `${loadedCount} storm(s) are loaded. Choose one in the sidebar to work on it.`}
          </p>
        )}

        {scenarioId && (
          <>
            <DataQualitySummary
              scenarioId={scenarioId}
              assetCount={page?.items.length ?? null}
              onReviewMatches={() => setReviewingMatches(true)}
            />
            <AssetMatchSheet
              scenarioId={scenarioId}
              open={reviewingMatches}
              onOpenChange={setReviewingMatches}
            />
            {/* The one door forward. The quality summary above is mandatory reading —
                this button sits below it so the path runs through the findings, and
                the dashboards' nav items do not exist until a storm is chosen. */}
            <div className="flex justify-end">
              <Button variant="primary" data-testid="finish-continue" onClick={onFinish}>
                Finish and continue
              </Button>
            </div>
          </>
        )}
      </div>
    )
  }

  // ---- Dispatch surface ---------------------------------------------------------------

  if (surface === 'dispatch') {
    return (
      <div data-testid="scenario-data" className="space-y-4">
        {scenario && (
          <>
            <StalenessBanner scenario={scenario} />
            <ScenarioIntegrityNotice integrity={scenario.integrity} role={role} />
          </>
        )}
        <DispatchSurface scenarioId={scenarioId} />
      </div>
    )
  }

  // ---- Storm Planning -------------------------------------------------------------------

  return (
    <div data-testid="scenario-data" className="space-y-5">
      {scenario && (
        <>
          <StalenessBanner scenario={scenario} />
          <ScenarioIntegrityNotice integrity={scenario.integrity} role={role} />
        </>
      )}

      {ranking && rankingState === 'ready' && (
        <Headline ranking={ranking} movement={movement} />
      )}

      {/* The answer first (CHG-057): who is most exposed right now, and why in one line.
          Movement is not a section of its own any more (CHG-060) — it stays as the arrows
          beside each rank and the headline's "moved up" sentence. */}
      {ranking && rankingState === 'ready' && (
        <TopRiskStrip ranking={ranking} onReview={setOpenAsset} />
      )}

      {/* Rendered from the scenario alone, deliberately not from the ranking: it is the
          way back to an order that can be read, so it survives a read that could not be. */}
      {scenario && (
        <ForecastRevisionControl
          scenario={scenario}
          viewing={ranking?.forecast_revision ?? viewing ?? scenario.forecast_revision}
          onView={setViewing}
        />
      )}

      <div className="grid gap-6 xl:grid-cols-[1fr_300px]">
        <div className="min-w-0 space-y-5">
          <RiskList
            scenarioId={scenarioId}
            ranking={ranking}
            state={rankingState}
            movement={movement}
            summaries={summariesOnScreen}
            onSummaryStored={keepSummary}
            onOpenAsset={setOpenAsset}
            onStartTriage={() => setTriaging(true)}
          />

          {/* CHG-060: the whole-ranking decision form and the placement form are gone
              from this screen at the client's instruction. The decision surface is
              per-asset triage — the drawer and Focus Mode — and each action writes a
              decision record naming the revision it was taken against. */}

          <section>
            <h2 className="mb-2 text-[15px] font-semibold">All assets</h2>
            <AssetTable page={page} state={assetState} />
          </section>
        </div>

        <div className="space-y-4">
          {page && ranking && rankingState === 'ready' && (
            <RiskMap page={page} ranking={ranking} />
          )}
          <CrewStagingPlan
            scenarioId={scenarioId}
            forecastRevision={ranking?.forecast_revision ?? scenario?.forecast_revision ?? 0}
          />
          <p className="text-[11px] leading-4 text-faint">
            Re-ranking after a forecast change takes under five seconds at demo scale. The
            previous order stays readable for comparison.
          </p>
        </div>
      </div>

      <AssetDetailSheet
        scenarioId={scenarioId}
        forecastRevision={ranking?.forecast_revision ?? 0}
        item={openAsset}
        summary={openAsset ? (summariesOnScreen.get(openAsset.asset_id) ?? null) : null}
        onClose={() => setOpenAsset(null)}
        onRecorded={() => undefined}
      />

      {triaging && ranking && (
        <FocusMode
          scenarioId={scenarioId}
          ranking={ranking}
          onExit={() => setTriaging(false)}
          onRecorded={() => undefined}
        />
      )}
    </div>
  )
}
