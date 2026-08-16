'use client'

/**
 * PlacementForm — record a crew placement against the ranking (REQ-F-005, US-007).
 *
 * **This is where the ranking becomes a decision** (`product-spec.md` §7). It is also the
 * control in this product most likely to be misread as an instruction that went somewhere, so
 * the confirmation says in as many words that nothing was dispatched — an operator who believes
 * a crew has been sent is a worse outcome than one who knows nothing has (BR-001).
 *
 * Four rules, and each has a specific failure it exists to prevent:
 *
 * - **Every typed value survives an error** (`frontend-component-spec.md`). A placement lost
 *   mid-storm is worse than an error message, and the retype is always shorter and vaguer than
 *   the first attempt. The crew, the note and the ticked assets are all still here after a
 *   failed write, and the button is ready to try again.
 * - **It is recorded against the revision on screen**, not against the storm's current pointer.
 *   A manager comparing orders is reading revision 0 while the storm has moved to 1, and a
 *   placement filed against the list they were not reading is the audit trail describing the
 *   wrong thing.
 * - **The "where" is a list of assets and nothing finer.** There is no address field, no
 *   coordinate field and no free-text location, because CON-003 forbids storing one and the
 *   store would refuse it (REQ-NF-007).
 * - **It is not rendered without a ranking on screen.** `ScenarioView` owns that, for the same
 *   reason it owns it for `RecommendationDecision`: a placement is a plan made against a list,
 *   and BR-001 means a person makes it while looking at one.
 *
 * It computes nothing. No score, no rank, no band — the checkbox list is the ranking's own
 * order, rendered (FF-002).
 */

import { useState } from 'react'

import { PlacementRecorded, Ranking, RequestFailed, placements } from '@/lib/api'
import { isBlank, trimBlank } from '@/lib/blank'

type State =
  | { stage: 'idle' }
  | { stage: 'saving' }
  | { stage: 'error'; message: string }

/** As long as the store will hold, so the refusal is this form's rather than a round trip's. */
const CREW_MAX = 120

export function PlacementForm({
  scenarioId,
  ranking,
}: {
  scenarioId: string
  ranking: Ranking
}) {
  const [state, setState] = useState<State>({ stage: 'idle' })
  const [crew, setCrew] = useState('')
  const [note, setNote] = useState('')
  const [chosen, setChosen] = useState<string[]>([])
  const [recorded, setRecorded] = useState<PlacementRecorded[]>([])

  /** The prepared-file code a person reads off the list, for an id the API answers with. */
  function codeOf(assetId: string): string {
    const item = ranking.items.find((row) => row.asset_id === assetId)
    return item ? item.external_ids[0] : assetId
  }

  function toggle(assetId: string) {
    setChosen((current) =>
      current.includes(assetId)
        ? current.filter((id) => id !== assetId)
        : [...current, assetId],
    )
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    // The `validating` state: said here rather than after a round trip, so a mistake costs no
    // time during a storm. The server refuses the same things and the store refuses them again.
    // `isBlank`, never `String.prototype.trim()`. The two disagree about U+200B, and the
    // disagreement was answered `201` and written into `decision_records` (CHG-039).
    if (isBlank(crew)) {
      setState({ stage: 'error', message: 'Name the crew before recording where it waits.' })
      return
    }
    if (chosen.length === 0) {
      setState({
        stage: 'error',
        message: 'Choose at least one asset — a placement is a crew and the assets it waits at.',
      })
      return
    }
    setState({ stage: 'saving' })
    try {
      const placement = await placements.record(
        scenarioId,
        trimBlank(crew),
        chosen,
        ranking.forecast_revision,
        trimBlank(note) || null,
      )
      setRecorded((current) => [placement, ...current])
      setState({ stage: 'idle' })
    } catch (error) {
      // Nothing is cleared. Not the crew, not the note, not the ticked assets — this is the
      // whole of FTEST-005's screen half, and the one thing this component exists to get right.
      setState({
        stage: 'error',
        message:
          error instanceof RequestFailed
            ? `${error.message} Nothing was recorded — what you typed is still here.`
            : 'We could not record that. Nothing was recorded — what you typed is still here.',
      })
    }
  }

  return (
    <section className="space-y-3">
      {recorded.length > 0 && (
        <div className="space-y-2 rounded-card border border-low-fg/25 bg-low-bg p-4 text-[13px] leading-relaxed text-low-fg" role="status" data-testid="placement-recorded">
          {recorded.map((placement) => (
            <p key={placement.placement_id}>
              <strong>Recorded: {placement.crew}</strong> at{' '}
              {placement.asset_ids.map(codeOf).join(', ')}, against{' '}
              <strong>forecast revision {placement.forecast_revision}</strong>, at{' '}
              {placement.occurred_at}. <em>No crew has been moved and nothing was dispatched</em> —
              this is written down so the storm can be explained afterwards, and it cannot be
              edited. A correction is a new placement.
            </p>
          ))}
        </div>
      )}

      <form onSubmit={submit} data-testid="placement-form" className="space-y-3 rounded-card border border-line p-4">
        <h3 className="text-[14px] font-semibold">Record a crew placement</h3>
        <p className="text-[13px] text-muted">
          Against the ranking you are reading — <strong>forecast revision{' '}
          {ranking.forecast_revision}</strong>.
        </p>

        <label htmlFor="placement-crew" className="block text-[13px] font-medium text-ink-secondary">Crew</label>
        <input
          className="h-9 w-full max-w-sm rounded-card border border-line px-3 text-[14px]"
          id="placement-crew"
          data-testid="placement-crew"
          maxLength={CREW_MAX}
          value={crew}
          onChange={(event) => setCrew(event.target.value)}
          placeholder="North team"
        />

        <fieldset className="max-h-72 space-y-1 overflow-y-auto rounded-card border border-line p-3">
          {/* Deliberately not "which assets is this crew waiting at" — an accessible name
              containing the word would collide with the field labelled Crew above. */}
          <legend className="mb-1 text-[13px] font-medium text-ink-secondary">Which assets is this placement for?</legend>
          {ranking.items.map((item) => (
            <label key={item.asset_id} className="flex items-center gap-2 py-0.5 text-[13px]">
              <input
                type="checkbox"
                data-testid={`placement-asset-${item.external_ids[0]}`}
                checked={chosen.includes(item.asset_id)}
                onChange={() => toggle(item.asset_id)}
              />{' '}
              {item.rank ?? '—'} · {item.name || item.external_ids[0]}{' '}
              <span className="text-[11px] text-faint">{item.external_ids.join(' · ')}</span>
              {/* An asset that could not be scored is on this list too. It is in the ranking and
                  not ranked, and planning around it is the reason it was kept (FTEST-004). */}
              {item.score === null && <span className="ml-1 rounded-full bg-panel px-2 py-0.5 text-[11px] font-medium text-ink-secondary">Not scored</span>}
            </label>
          ))}
        </fieldset>

        <label htmlFor="placement-note" className="block text-[13px] font-medium text-ink-secondary">Why here? (optional)</label>
        <textarea
          className="w-full rounded-card border border-line p-3 text-[14px]"
          rows={2}
          id="placement-note"
          data-testid="placement-note"
          maxLength={2000}
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />

        {state.stage === 'error' && (
          <p role="alert" data-testid="placement-error" className="text-[13px] text-high-fg">
            {state.message}
          </p>
        )}

        <button type="submit" data-testid="placement-submit" disabled={state.stage === 'saving'} className="inline-flex h-9 items-center rounded-card border border-line bg-background px-4 text-[14px] font-medium hover:bg-panel disabled:opacity-50">
          {state.stage === 'saving' ? 'Recording…' : 'Record placement'}
        </button>
        <p className="text-[12px] leading-relaxed text-muted">
          Recording a placement changes nothing in the field. No crew is moved and no message
          leaves this platform — it is written down so the decision sits beside the evidence for
          it.
        </p>
      </form>
    </section>
  )
}
