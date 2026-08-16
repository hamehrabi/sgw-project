'use client'

/**
 * TopRiskStrip — the four highest-ranked assets as cards, above the table (CHG-057).
 *
 * The screen opens with the answer: who is most exposed, right now, and why in one
 * sentence. Nothing is computed here — the cards render the `RiskItem`s already in the
 * ranking response, so the card, the row and the drawer are one object (the same rule
 * that keeps Focus Mode honest). The sentence is the strongest computed reason, which
 * arrives first because the server sorted reasons by contribution.
 */

import { ChevronRight } from 'lucide-react'

import { BandBadge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Ranking, RiskItem } from '@/lib/api'

export function TopRiskStrip({
  ranking,
  onReview,
}: {
  ranking: Ranking
  onReview: (item: RiskItem) => void
}) {
  const top = ranking.items.filter((item) => item.rank !== null).slice(0, 4)
  if (top.length === 0) return null

  return (
    <section data-testid="top-risk-strip">
      <p className="mb-2 border-b border-line pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted">
        Highest risk right now
      </p>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {top.map((item) => (
          <Card key={item.asset_id} className="flex flex-col p-3.5" data-testid="top-risk-card">
            <div className="mb-1.5 flex items-start justify-between gap-2">
              <p className="min-w-0 truncate text-[13px] font-semibold" title={item.name}>
                {item.name || item.external_ids[0]}
              </p>
              <span className="shrink-0 rounded-full border border-line bg-rail px-2 py-0.5 text-[11px] font-medium tabular-nums text-muted">
                #{String(item.rank).padStart(2, '0')}
              </span>
            </div>
            {item.band && <BandBadge band={item.band} className="mb-2 self-start" />}
            {/* The strongest computed reason, in its own words — never re-phrased here. */}
            <p className="line-clamp-2 text-[12px] leading-relaxed text-muted">
              {item.reasons[0]?.detail}
            </p>
            <button
              type="button"
              className="mt-auto flex items-center gap-0.5 pt-2 text-[12px] font-medium text-teal-deep hover:underline"
              onClick={() => onReview(item)}
            >
              Review <ChevronRight className="h-3.5 w-3.5" aria-hidden />
            </button>
          </Card>
        ))}
      </div>
    </section>
  )
}
