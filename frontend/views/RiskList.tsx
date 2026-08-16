'use client'

/**
 * RiskList — every asset ordered by risk. **The screen the product competes on.**
 *
 * Three rules, and each has a specific failure it exists to prevent:
 *
 * - **A rank never renders without its reasons** (BR-002). They arrive in the same
 *   response, so there is no state in which a rank is on screen and its reasons are
 *   still loading — and the same three reasons feed the row, the drawer and Focus Mode,
 *   because they are one object, not three renderings.
 * - **The empty state reads "no ranking computed" — never "no risk."** A blank list
 *   during a storm is indistinguishable from a grid with nothing wrong with it.
 * - **An unscored asset is shown, plainly marked, and never sorted as though it were
 *   safe.** It sits at the end under its own heading — and it renders on **every page**
 *   (CHG-057): an asset nobody could judge must never be hidden by a page boundary.
 *
 * Pagination is presentation, not a read path: `lib/api.ts` already followed the
 * cursor to the end, and slicing here cannot lose a row the way a second fetch could.
 *
 * The Summary button asks the server for the stored per-asset summary (CHG-059),
 * generating it only the first time. The popup renders what the guardrail already
 * verified — nothing here judges text, and no view imports the model (ADR-009).
 *
 * It computes nothing. No score, no rank, no band — FF-002 fails the build if any of
 * ADR-007's constants appear anywhere in this directory.
 */

import { ArrowDown, ArrowUp } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Badge, BandBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogClose, DialogContent } from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { AssetSummary, insights, Movement, Ranking, RequestFailed, RiskItem } from '@/lib/api'

import { ReasonPanel } from './ReasonPanel'

/** Chip words per factor — the sentence lives in the panel and the drawer. */
const FACTOR_CHIPS: Record<string, string> = {
  gust_vs_design: 'Wind vs design',
  flood_zone: 'Flood zone',
  age_vs_service_life: 'Age',
  condition_decayed: 'Condition',
}

const PAGE_SIZES = [25, 50, 100] as const

function MovementArrow({ delta }: { delta: number | null }) {
  if (delta === null || delta === 0) return null
  const Up = delta > 0
  return (
    <span
      className={Up ? 'text-high-fg' : 'text-muted'}
      aria-label={Up ? `up ${delta} places` : `down ${-delta} places`}
    >
      {Up ? (
        <ArrowUp className="inline h-3.5 w-3.5" aria-hidden />
      ) : (
        <ArrowDown className="inline h-3.5 w-3.5" aria-hidden />
      )}
    </span>
  )
}

function Row({
  item,
  delta,
  onOpen,
  onSummary,
  summaryState,
}: {
  item: RiskItem
  delta: number | null
  onOpen: (item: RiskItem) => void
  onSummary: (item: RiskItem) => void
  summaryState: 'stored' | 'working' | 'none'
}) {
  const [open, setOpen] = useState(false)
  const unscored = item.score === null

  return (
    <>
      <TableRow className={unscored ? 'bg-rail/60' : undefined}>
        <TableCell className="risk__rank whitespace-nowrap font-semibold">
          {item.rank ?? '—'} <MovementArrow delta={delta} />
        </TableCell>
        <TableCell>
          <button
            type="button"
            className="text-left font-medium text-ink underline-offset-2 hover:text-teal-deep hover:underline"
            onClick={() => onOpen(item)}
          >
            {item.name || item.external_ids[0]}
          </button>
          {/* The grey provenance caption: type, and the codes each source system uses.
              `row__codes` is styleless — the hook two specs read the order through. */}
          <p className="row__codes text-[12px] leading-4 text-muted">
            {item.type} · {item.external_ids.join(' · ')}
          </p>
          {item.match_status === 'needs_review' && (
            <Badge variant="outline" data-testid="needs-review">
              needs review
            </Badge>
          )}
        </TableCell>
        <TableCell>
          {unscored ? (
            <Badge variant="neutral" className="band--unscored">Not scored</Badge>
          ) : (
            item.band && <BandBadge band={item.band} />
          )}
        </TableCell>
        <TableCell>
          <div className="flex flex-wrap items-center gap-1.5">
            {item.reasons.slice(0, 2).map((reason) => (
              <Badge key={reason.factor} variant="outline">
                {FACTOR_CHIPS[reason.factor] ?? reason.factor}
              </Badge>
            ))}
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-1.5 text-[12px] text-teal"
              onClick={() => setOpen(!open)}
              aria-expanded={open}
            >
              {open ? 'Hide why' : 'Why?'}
            </Button>
          </div>
        </TableCell>
        <TableCell className="whitespace-nowrap">
          <Button
            variant="outline"
            size="sm"
            className="h-7 px-2.5 text-[12px]"
            data-testid="asset-summary-button"
            disabled={summaryState === 'working'}
            onClick={() => onSummary(item)}
          >
            {summaryState === 'working' ? 'Summarising…' : 'Summary'}
          </Button>
        </TableCell>
      </TableRow>
      {open && (
        <tr className="border-b border-line bg-rail/40">
          <td colSpan={5} className="px-3 py-3">
            <ReasonPanel item={item} />
          </td>
        </tr>
      )}
    </>
  )
}

export function RiskList({
  scenarioId,
  ranking,
  state,
  movement,
  summaries,
  onSummaryStored,
  onOpenAsset,
  onStartTriage,
}: {
  scenarioId: string
  ranking: Ranking | null
  state: 'loading' | 'ready' | 'error'
  movement: Movement | null
  /** Stored summaries for the revision on screen, keyed by asset (CHG-059). */
  summaries: Map<string, AssetSummary>
  onSummaryStored: (summary: AssetSummary) => void
  onOpenAsset: (item: RiskItem) => void
  onStartTriage: () => void
}) {
  // 25 by default (CHG-060) — a screenful to read, expandable to 50 or 100.
  const [perPage, setPerPage] = useState<number>(25)
  const [pageIndex, setPageIndex] = useState(0)
  const [reading, setReading] = useState<RiskItem | null>(null)
  const [working, setWorking] = useState<string | null>(null)
  const [summaryProblem, setSummaryProblem] = useState<string | null>(null)

  // A new order restarts the pages — page 3 of the previous forecast is not a place.
  useEffect(() => {
    setPageIndex(0)
  }, [ranking?.forecast_revision, ranking?.scenario_id, perPage])

  if (state === 'loading')
    return (
      <p role="status" data-testid="risk-list-loading" className="text-[13px] text-muted">
        Working out the ranking…
      </p>
    )

  if (state === 'error') {
    return (
      <p role="alert" className="text-[13px] text-high-fg">
        We could not load the ranking. The storm is still loaded — try again. This is not a
        statement that nothing is at risk.
      </p>
    )
  }

  if (!ranking || ranking.items.length === 0) {
    return (
      <p role="status" data-testid="ranking-empty" className="text-[13px]">
        <strong>No ranking computed.</strong> This does not mean there is no risk — it means
        nothing has been scored yet.
      </p>
    )
  }

  const scored = ranking.items.filter((item) => item.score !== null)
  const unscored = ranking.items.filter((item) => item.score === null)
  const deltas = new Map(
    (movement?.items ?? []).map((mover) => [
      mover.asset_id,
      (mover.previous_rank ?? 0) - (mover.current_rank ?? 0),
    ]),
  )

  const pages = Math.max(1, Math.ceil(scored.length / perPage))
  const page = Math.min(pageIndex, pages - 1)
  const start = page * perPage
  const visible = scored.slice(start, start + perPage)

  async function openSummary(item: RiskItem) {
    setSummaryProblem(null)
    const stored = summaries.get(item.asset_id)
    if (stored) {
      setReading(item)
      return
    }
    setWorking(item.asset_id)
    try {
      const summary = await insights.generateAssetSummary(
        scenarioId,
        item.asset_id,
        ranking!.forecast_revision,
      )
      onSummaryStored(summary)
      setReading(item)
    } catch (error) {
      setSummaryProblem(
        error instanceof RequestFailed
          ? error.message
          : 'We could not produce the summary. The ranking itself is unaffected.',
      )
      setReading(item)
    } finally {
      setWorking(null)
    }
  }

  const readingSummary = reading ? (summaries.get(reading.asset_id) ?? null) : null

  return (
    <section data-testid="risk-list" className="space-y-3">
      {/* Standing, not a footnote: a confidently wrong ranking is more persuasive than a
          wrong model, not less (ADR-005). */}
      {!ranking.weights_calibrated && (
        <div
          className="rounded-card border border-medium-fg/25 bg-medium-bg px-4 py-3 text-[13px] leading-relaxed text-medium-fg"
          role="status"
          data-testid="uncalibrated-notice"
        >
          <strong>These weights have not been calibrated.</strong> The ranking is computed from
          an agreed rule ({ranking.weight_set_version}), not from SGW&rsquo;s own failure
          history — nobody has yet checked it against a real storm. Read the reasons beside each
          rank and disagree with them where they are wrong.
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <p className="text-[13px] text-muted">
          <span className="font-semibold text-ink">Assets by risk</span>
          <Badge variant="neutral" className="ml-2">
            {scored.length} ranked
          </Badge>
        </p>
        {/* The screen's one primary action. */}
        <Button variant="primary" onClick={onStartTriage} data-testid="start-triage">
          Start triage
        </Button>
      </div>

      <div className="overflow-x-auto rounded-card border border-line">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-rail">
              <TableHead className="w-16">Rank</TableHead>
              <TableHead>Asset</TableHead>
              <TableHead className="w-24">Risk</TableHead>
              <TableHead>Why</TableHead>
              <TableHead className="w-28">Summary</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.map((item) => (
              <Row
                key={item.asset_id}
                item={item}
                delta={deltas.get(item.asset_id) ?? null}
                onOpen={onOpenAsset}
                onSummary={(chosen) => void openSummary(chosen)}
                summaryState={
                  working === item.asset_id
                    ? 'working'
                    : summaries.has(item.asset_id)
                      ? 'stored'
                      : 'none'
                }
              />
            ))}
          </TableBody>

          {/* On every page, deliberately: paging must never hide the unjudged. */}
          {unscored.length > 0 && (
            <TableBody data-testid="unscored-group">
              <tr className="border-b border-line bg-rail">
                <th colSpan={5} className="px-3 py-2 text-left text-[12px] font-medium text-ink-secondary">
                  {unscored.length} asset(s) could not be scored — shown here rather than left
                  out. They have <strong>not</strong> been judged low risk.
                </th>
              </tr>
              {unscored.map((item) => (
                <Row
                  key={item.asset_id}
                  item={item}
                  delta={null}
                  onOpen={onOpenAsset}
                  onSummary={(chosen) => void openSummary(chosen)}
                  summaryState={
                    working === item.asset_id
                      ? 'working'
                      : summaries.has(item.asset_id)
                        ? 'stored'
                        : 'none'
                  }
                />
              ))}
            </TableBody>
          )}
        </Table>
      </div>

      {/* CHG-057: pages over the whole stored order, stated as such. */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 text-[12px] text-muted"
        data-testid="risk-pagination"
      >
        <p className="tabular-nums">
          Showing {scored.length === 0 ? 0 : start + 1}–{Math.min(start + perPage, scored.length)}{' '}
          of {scored.length} ranked
        </p>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1" role="group" aria-label="Rows per page">
            Per page
            {PAGE_SIZES.map((size) => (
              <button
                key={size}
                type="button"
                data-testid={`per-page-${size}`}
                aria-pressed={perPage === size}
                onClick={() => setPerPage(size)}
                className={
                  perPage === size
                    ? 'rounded-card border border-teal bg-teal-soft px-2 py-0.5 font-medium text-teal-deep'
                    : 'rounded-card border border-line bg-background px-2 py-0.5 hover:bg-panel'
                }
              >
                {size}
              </button>
            ))}
          </span>
          <span className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2.5 text-[12px]"
              data-testid="page-previous"
              disabled={page === 0}
              onClick={() => setPageIndex(page - 1)}
            >
              Previous
            </Button>
            <span className="tabular-nums">
              Page {page + 1} of {pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2.5 text-[12px]"
              data-testid="page-next"
              disabled={page >= pages - 1}
              onClick={() => setPageIndex(page + 1)}
            >
              Next
            </Button>
          </span>
        </div>
      </div>

      {/* The summary popup (CHG-059). What it shows was verified server-side before it
          was stored; the label says which path wrote it, always. */}
      <Dialog open={reading !== null} onOpenChange={(open) => !open && setReading(null)}>
        {reading && (
          <DialogContent
            title={
              <span data-testid="summary-dialog-title">
                {reading.name || reading.external_ids[0]}
              </span>
            }
          >
            <div className="space-y-3 overflow-y-auto p-4" data-testid="summary-dialog">
              {summaryProblem ? (
                <p role="alert" className="text-[13px] text-high-fg">
                  {summaryProblem}
                </p>
              ) : readingSummary ? (
                <>
                  <p className="whitespace-pre-line text-[13px] leading-relaxed">
                    {readingSummary.text}
                  </p>
                  <p className="text-[11px] text-muted">
                    {readingSummary.label} · verified against this asset&rsquo;s computed
                    factors · saved for forecast revision {readingSummary.forecast_revision}
                  </p>
                </>
              ) : (
                <p role="status" className="text-[13px] text-muted">
                  Reading the stored summary…
                </p>
              )}
            </div>
            <div className="flex justify-end border-t border-line p-3">
              <DialogClose asChild>
                <Button variant="outline" size="sm" data-testid="summary-dialog-close">
                  Close
                </Button>
              </DialogClose>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </section>
  )
}
