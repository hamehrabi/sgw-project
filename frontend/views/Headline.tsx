'use client'

/**
 * Headline — the screen opens with a plain-English sentence that states the answer.
 *
 * The signature element of the whole design, and every number in it is read from the
 * data, never hard-coded. The design's copy claims a 72-hour horizon; the arithmetic has
 * no horizon parameter, so the sentence says what the computation can defend — *at the
 * current forecast* — rather than the copy (CHG-044's recorded deviation).
 */

import { Movement, Ranking } from '@/lib/api'

export function Headline({
  ranking,
  movement,
}: {
  ranking: Ranking
  movement: Movement | null
}) {
  const high = ranking.items.filter((item) => item.band === 'High').length
  const total = ranking.items.length

  return (
    <div data-testid="planning-headline">
      <h1 className="text-[26px] font-semibold leading-tight tracking-tight tabular-nums">
        {high === 0
          ? `No assets of ${total} are at high risk at the current forecast.`
          : `${high} of ${total} assets ${high === 1 ? 'is' : 'are'} at high risk at the current forecast.`}
      </h1>
      {movement?.first_ranking && (
        <p className="mt-1 text-[15px] font-medium leading-snug text-muted">
          This is the first scoring run for this scenario.
        </p>
      )}
      {movement && !movement.first_ranking && movement.moved_up_high > 0 && (
        <p className="mt-1 text-[20px] font-medium leading-snug text-muted">
          {movement.moved_up_high} of them moved up since {movement.previous_label}.
        </p>
      )}
      {high === 0 && (
        <p className="mt-1 text-[14px] text-muted">
          A quiet list is a statement about this forecast, not a promise about the storm.
        </p>
      )}
    </div>
  )
}
