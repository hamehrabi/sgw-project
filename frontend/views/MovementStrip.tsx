'use client'

/**
 * MovementStrip — "Since you last looked": the genuine diff between two delivered
 * rankings (CHG-044), never a faked delta.
 *
 * At revision 0 there is no earlier order and the strip says so plainly — inventing one
 * is the faked movement the client's own prompt forbids by name. After a forecast change
 * the four biggest risers appear, each with the movement, the factor that grew, and a
 * way to the asset.
 */

import { ArrowUp } from 'lucide-react'

import { Card } from '@/components/ui/card'
import { Movement, MovementItem, Ranking, RiskItem } from '@/lib/api'

/** The factor's short name for a card — the sentence is in the drawer. */
const FACTOR_WORDS: Record<string, string> = {
  gust_vs_design: 'Forecast gusts rose',
  flood_zone: 'Flood exposure',
  age_vs_service_life: 'Age factor',
  condition_decayed: 'Condition factor',
  unscored: 'Not scored',
}

export function MovementStrip({
  movement,
  ranking,
  onReview,
}: {
  movement: Movement | null
  ranking: Ranking
  onReview: (item: RiskItem) => void
}) {
  if (movement === null) return null

  const byAsset = new Map(ranking.items.map((item) => [item.asset_id, item]))

  return (
    <section aria-label="Since you last looked" data-testid="movement-strip">
      <p className="mb-2 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-widest text-muted">
        Since you last looked
        <span className="h-px flex-1 bg-line" aria-hidden />
      </p>

      {movement.first_ranking || movement.items.length === 0 ? (
        <p className="text-[13px] text-muted" data-testid="movement-empty">
          {movement.first_ranking
            ? 'This is the first ranking for this storm — there is no earlier order to compare against yet. Movement appears once a forecast change is applied.'
            : `Nothing moved up since ${movement.previous_label ?? 'the previous forecast'}.`}
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {movement.items.slice(0, 4).map((mover: MovementItem) => {
            const item = byAsset.get(mover.asset_id)
            const climbed = (mover.previous_rank ?? 0) - (mover.current_rank ?? 0)
            return (
              <Card key={mover.asset_id} className="p-3" data-testid="movement-card">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-[14px] font-semibold leading-5">
                    {item?.name || item?.external_ids[0] || mover.asset_id}
                  </p>
                  <span className="inline-flex shrink-0 items-center gap-0.5 rounded-full bg-high-bg px-1.5 py-0.5 text-[12px] font-semibold text-high-fg">
                    <ArrowUp className="h-3 w-3" aria-hidden />
                    {climbed}
                  </span>
                </div>
                <p className="mt-0.5 text-[12px] text-muted">
                  {FACTOR_WORDS[mover.reason_factor] ?? mover.reason_factor}
                </p>
                {item && (
                  <button
                    type="button"
                    className="mt-2 text-[13px] font-medium text-teal underline-offset-2 hover:underline"
                    onClick={() => onReview(item)}
                  >
                    Review →
                  </button>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </section>
  )
}
