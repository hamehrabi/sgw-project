'use client'

/**
 * RecommendationDecision — accept, change, or reject the ranking the system produced.
 *
 * **This component is where BR-001 is visible to a person.** The product recommends; a person
 * decides. Nothing here dispatches anything, and the confirmation says so in as many words —
 * an operator who believes a crew has been sent is a worse outcome than one who knows nothing
 * has.
 *
 * Three rules from `frontend-component-spec.md` and BR-004:
 *
 * - **Change and reject require a note.** The note is why the record is worth keeping.
 * - **A second decision shows the first rather than overwriting it.** The server returns 409;
 *   this renders what already happened instead of pretending the click failed.
 * - **A failed write keeps the typed note on screen** (FTEST-005). An operator typing a reason
 *   during a storm should never have to remember it twice, and the retype is always shorter.
 */

import { useState } from 'react'

import { RequestFailed, recommendations } from '@/lib/api'

type Kind = 'accept' | 'change' | 'reject'

type State =
  | { stage: 'idle' }
  | { stage: 'saving' }
  | { stage: 'decided'; kind: string; at: string }
  | { stage: 'already'; message: string }
  | { stage: 'error'; message: string }

export function RecommendationDecision({ recommendationId }: { recommendationId: string }) {
  const [state, setState] = useState<State>({ stage: 'idle' })
  const [kind, setKind] = useState<Kind>('accept')
  const [note, setNote] = useState('')

  const noteRequired = kind === 'change' || kind === 'reject'

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (noteRequired && !note.trim()) {
      setState({ stage: 'error', message: `A note is required when you ${kind} a ranking.` })
      return
    }
    setState({ stage: 'saving' })
    try {
      const recorded = await recommendations.decide(recommendationId, kind, note.trim() || null)
      setState({ stage: 'decided', kind: recorded.decision, at: recorded.occurred_at })
    } catch (error) {
      if (error instanceof RequestFailed && error.status === 409) {
        setState({ stage: 'already', message: error.message })
        return
      }
      // The note is deliberately NOT cleared. It is the operator's reasoning about a live
      // storm, and a failed write must not cost it.
      setState({
        stage: 'error',
        message:
          error instanceof RequestFailed
            ? error.message
            : 'We could not record that. Nothing was saved — your note is still here.',
      })
    }
  }

  if (state.stage === 'decided') {
    return (
      <div className="rounded-card border border-low-fg/25 bg-low-bg p-4 text-[13px] leading-relaxed text-low-fg" role="status" data-testid="decision-recorded">
        <strong>Recorded: {state.kind}.</strong> This was written to the decision record at{' '}
        {state.at} and cannot be edited — a correction is a new entry.{' '}
        <em>No crew has been moved and nothing has been dispatched.</em>
      </div>
    )
  }

  if (state.stage === 'already') {
    return (
      <div className="rounded-card border border-line bg-rail p-4 text-[13px] leading-relaxed" role="status" data-testid="decision-already">
        {state.message}
      </div>
    )
  }

  return (
    <form className="space-y-3 rounded-card border border-line p-4" onSubmit={submit} data-testid="decision-form">
      <fieldset className="flex flex-wrap items-center gap-4">
        <legend className="mb-1.5 w-full text-[14px] font-semibold">Your decision on this ranking</legend>
        {(['accept', 'change', 'reject'] as Kind[]).map((option) => (
          <label key={option} className="flex items-center gap-1.5 text-[13px] capitalize">
            <input
              type="radio"
              name="decision"
              value={option}
              checked={kind === option}
              onChange={() => setKind(option)}
            />{' '}
            {option}
          </label>
        ))}
      </fieldset>

      <label htmlFor="decision-note" className="block text-[13px] font-medium text-ink-secondary">
        Note {noteRequired ? '(required)' : '(optional)'}
      </label>
      <textarea
        className="w-full rounded-card border border-line p-3 text-[14px]"
        rows={3}
        id="decision-note"
        maxLength={2000}
        value={note}
        onChange={(event) => setNote(event.target.value)}
        placeholder={noteRequired ? 'Why are you changing or rejecting this ranking?' : ''}
      />

      {state.stage === 'error' && (
        <p role="alert" data-testid="decision-error" className="text-[13px] text-high-fg">
          {state.message}
        </p>
      )}

      <button type="submit" disabled={state.stage === 'saving'} className="inline-flex h-9 items-center rounded-card bg-ink px-4 text-[14px] font-medium text-white hover:bg-ink-secondary disabled:opacity-50">
        {state.stage === 'saving' ? 'Recording…' : 'Record decision'}
      </button>
      <p className="text-[12px] leading-relaxed text-muted">
        Recording a decision changes nothing in the field. It is written down so the storm can
        be explained afterwards.
      </p>
    </form>
  )
}
