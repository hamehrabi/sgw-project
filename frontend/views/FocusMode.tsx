'use client'

/**
 * FocusMode — one asset at a time, full screen (design screen 6; CHG-055).
 *
 * The triage room: a progress bar, the band, the asset's name, exactly the same plain
 * sentences the row and the drawer show — one object, three surfaces — and three
 * actions on the keys a hand can hold: A accept, J adjust, D dismiss, ← back, Esc out.
 * No icons beside the reasons; the sentences carry themselves.
 *
 * Every action writes a decision record — this is the evidence that operators acted on
 * the rankings — and none of them moves a crew or hides an asset.
 */

import { X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { Badge, BandBadge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/bits'
import { Button } from '@/components/ui/button'
import { Label, Textarea } from '@/components/ui/field'
import { insights, RequestFailed, Ranking, RiskItem } from '@/lib/api'

export function FocusMode({
  scenarioId,
  ranking,
  onExit,
  onRecorded,
}: {
  scenarioId: string
  ranking: Ranking
  onExit: () => void
  onRecorded: () => void
}) {
  const queue = useMemo(
    () => ranking.items.filter((item) => item.score !== null),
    [ranking.items],
  )
  const [index, setIndex] = useState(0)
  const [reviewed, setReviewed] = useState(0)
  const [noteFor, setNoteFor] = useState<'Adjust' | 'Dismiss' | null>(null)
  const [note, setNote] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const item: RiskItem | undefined = queue[index]

  const advance = useCallback(() => {
    setNote('')
    setNoteFor(null)
    setProblem(null)
    setReviewed((count) => count + 1)
    if (index + 1 >= queue.length) {
      onExit()
    } else {
      setIndex(index + 1)
    }
  }, [index, queue.length, onExit])

  const record = useCallback(
    async (action: 'Accept' | 'Adjust' | 'Dismiss') => {
      if (!item || saving) return
      if ((action === 'Adjust' || action === 'Dismiss') && !note.trim()) {
        setNoteFor(action)
        return
      }
      setSaving(true)
      setProblem(null)
      try {
        await insights.triage(
          scenarioId,
          item.asset_id,
          ranking.forecast_revision,
          action,
          note.trim() || null,
        )
        onRecorded()
        advance()
      } catch (error) {
        setProblem(
          error instanceof RequestFailed
            ? error.message
            : 'We could not record that. Nothing was saved — your note is still here.',
        )
      } finally {
        setSaving(false)
      }
    },
    [item, saving, note, scenarioId, ranking.forecast_revision, onRecorded, advance],
  )

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLInputElement)
        return
      if (event.key === 'Escape') onExit()
      if (event.key === 'a' || event.key === 'A') void record('Accept')
      if (event.key === 'j' || event.key === 'J') void record('Adjust')
      if (event.key === 'd' || event.key === 'D') void record('Dismiss')
      if (event.key === 'ArrowLeft' && index > 0) {
        setIndex(index - 1)
        setNote('')
        setNoteFor(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [record, onExit, index])

  if (!item) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Focus mode triage"
      className="fixed inset-0 z-50 flex flex-col bg-background"
      data-testid="focus-mode"
    >
      {/* Top: progress and the way out. */}
      <div className="flex items-center gap-4 p-4">
        <Progress value={reviewed} max={queue.length} label="Assets reviewed" className="max-w-xs" />
        <span className="text-[12px] font-semibold uppercase tracking-wide text-muted">
          {reviewed} of {queue.length} reviewed
        </span>
        <button
          type="button"
          onClick={onExit}
          className="ml-auto flex items-center gap-1.5 rounded-card border border-line px-3 py-1.5 text-[12px] font-medium uppercase tracking-wide text-muted hover:bg-panel"
        >
          Esc to exit <X className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>

      {/* Middle: the one asset, and nothing else. */}
      <div className="flex flex-1 items-center justify-center overflow-y-auto p-6">
        <div className="w-full max-w-xl">
          {item.band && <BandBadge band={item.band} className="mb-3" />}
          <h2 className="mb-6 text-[30px] font-semibold tracking-tight">
            {item.name || item.external_ids[0]}
          </h2>

          {/* Exactly the row's sentences — the same object, no icons beside them. */}
          <ul className="space-y-4">
            {item.reasons.slice(0, 3).map((reason) => (
              <li key={reason.factor} className="text-[16px] leading-relaxed">
                {reason.detail}
              </li>
            ))}
          </ul>

          {noteFor && (
            <div className="mt-6">
              <Label htmlFor="focus-note">Why {noteFor.toLowerCase()}? (required)</Label>
              <Textarea
                id="focus-note"
                rows={3}
                maxLength={2000}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                // The textarea swallows A/J/D on purpose while typing; the buttons below
                // still work.
                autoFocus
              />
            </div>
          )}

          {problem && (
            <p role="alert" className="mt-4 text-[13px] text-high-fg">
              {problem}
            </p>
          )}
        </div>
      </div>

      {/* Bottom: the three decisions, keys shown beside their words. */}
      <div className="flex items-center justify-between border-t border-line p-4">
        <div className="flex gap-2">
          <Button disabled={saving} onClick={() => void record('Adjust')}>
            Adjust <Badge variant="outline">J</Badge>
          </Button>
          <Button
            variant="destructive-outline"
            disabled={saving}
            onClick={() => void record('Dismiss')}
          >
            Dismiss <Badge variant="outline">D</Badge>
          </Button>
        </div>
        <Button variant="primary" size="lg" disabled={saving} onClick={() => void record('Accept')}>
          Accept <Badge className="bg-white/20 text-white">A</Badge>
        </Button>
      </div>
    </div>
  )
}
