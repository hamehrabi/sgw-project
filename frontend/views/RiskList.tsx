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
 *   safe.** It sits at the end under its own heading — "we could not judge this" and
 *   "we judged this low" are different claims.
 *
 * **No numeric score appears in this table** — the design is right about that and the
 * old table was wrong: a number invites comparison arithmetic the bands already did,
 * and the reasons are the product. The band is the word, in its tint, never alone.
 *
 * It computes nothing. No score, no rank, no band — FF-002 fails the build if any of
 * ADR-007's constants appear anywhere in this directory.
 */

import { ArrowDown, ArrowUp } from 'lucide-react'
import { useState } from 'react'

import { Badge, BandBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Movement, Ranking, RiskItem } from '@/lib/api'

import { ReasonPanel } from './ReasonPanel'

/** Chip words per factor — the sentence lives in the panel and the drawer. */
const FACTOR_CHIPS: Record<string, string> = {
  gust_vs_design: 'Wind vs design',
  flood_zone: 'Flood zone',
  age_vs_service_life: 'Age',
  condition_decayed: 'Condition',
}

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
}: {
  item: RiskItem
  delta: number | null
  onOpen: (item: RiskItem) => void
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
      </TableRow>
      {open && (
        <tr className="border-b border-line bg-rail/40">
          <td colSpan={4} className="px-3 py-3">
            <ReasonPanel item={item} />
          </td>
        </tr>
      )}
    </>
  )
}

export function RiskList({
  ranking,
  state,
  movement,
  onOpenAsset,
  onStartTriage,
}: {
  ranking: Ranking | null
  state: 'loading' | 'ready' | 'error'
  movement: Movement | null
  onOpenAsset: (item: RiskItem) => void
  onStartTriage: () => void
}) {
  if (state === 'loading')
    return (
      <p role="status" className="text-[13px] text-muted">
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
            </TableRow>
          </TableHeader>
          <TableBody>
            {scored.map((item) => (
              <Row
                key={item.asset_id}
                item={item}
                delta={deltas.get(item.asset_id) ?? null}
                onOpen={onOpenAsset}
              />
            ))}
          </TableBody>

          {unscored.length > 0 && (
            <TableBody data-testid="unscored-group">
              <tr className="border-b border-line bg-rail">
                <th colSpan={4} className="px-3 py-2 text-left text-[12px] font-medium text-ink-secondary">
                  {unscored.length} asset(s) could not be scored — shown here rather than left
                  out. They have <strong>not</strong> been judged low risk.
                </th>
              </tr>
              {unscored.map((item) => (
                <Row key={item.asset_id} item={item} delta={null} onOpen={onOpenAsset} />
              ))}
            </TableBody>
          )}
        </Table>
      </div>
    </section>
  )
}
