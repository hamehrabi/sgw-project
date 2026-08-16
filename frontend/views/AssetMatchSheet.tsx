'use client'

/**
 * AssetMatchSheet — the review queue for withheld merges (CHG-048, AC-001).
 *
 * The loader's rule put these here: a wrong merge deletes an asset from the ranking
 * invisibly, a wrong split costs ten seconds in this queue, so the tie went to not
 * merging — and this drawer is the ten seconds. Two comparison cards, the differing
 * fields on a neutral tint (a difference is a fact, not an alarm), confidence stated in
 * words and never as a percentage, and the two answers on keys M and N because a person
 * clearing seventeen of these should not need the mouse.
 *
 * "Finish later" preserves work by doing nothing: every resolution was recorded the
 * moment it was chosen, so closing the drawer loses nothing.
 */

import { Landmark, Users } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/bits'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import { insights, MatchCandidate, MatchRecord, RequestFailed } from '@/lib/api'

const FIELDS: { key: keyof MatchRecord; label: string }[] = [
  { key: 'id', label: 'ID' },
  { key: 'name', label: 'Name' },
  { key: 'type', label: 'Type' },
  { key: 'condition_observed_at', label: 'Last inspected' },
  { key: 'install_year', label: 'Installed' },
]

function RecordCard({
  heading,
  icon: Icon,
  record,
  other,
  accent,
}: {
  heading: string
  icon: typeof Landmark
  record: MatchRecord
  other: MatchRecord
  accent?: boolean
}) {
  return (
    <div
      className={cn(
        'rounded-card border border-line bg-background',
        accent && 'border-l-2 border-l-teal',
      )}
    >
      <p className="flex items-center gap-2 border-b border-line px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {heading}
      </p>
      <dl className="space-y-1.5 p-3">
        {FIELDS.map(({ key, label }) => {
          const value = record[key]
          if (value === null || value === undefined || value === '') return null
          const differs = String(value) !== String(other[key] ?? '')
          return (
            <div key={key} className="flex items-baseline gap-3 text-[13px]">
              <dt className="w-24 shrink-0 text-muted">{label}</dt>
              {/* A neutral tint, deliberately: the difference is what the person is here
                  to judge, not a mistake to be alarmed about. */}
              <dd className={cn('rounded px-1', differs && 'bg-teal-soft')}>{String(value)}</dd>
            </div>
          )
        })}
      </dl>
    </div>
  )
}

export function AssetMatchSheet({
  scenarioId,
  open,
  onOpenChange,
}: {
  scenarioId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [queue, setQueue] = useState<MatchCandidate[]>([])
  const [total, setTotal] = useState(0)
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const read = useCallback(async () => {
    try {
      const body = await insights.matches(scenarioId)
      setQueue(body.items)
      setTotal(body.total)
      setProblem(null)
    } catch {
      setProblem('We could not load the review queue.')
    }
  }, [scenarioId])

  useEffect(() => {
    if (open) void read()
  }, [open, read])

  const pending = queue.filter((candidate) => candidate.resolution === 'pending')
  const reviewed = total - pending.length
  const current = pending[0] ?? null

  const resolve = useCallback(
    async (resolution: 'match' | 'not_match') => {
      if (!current || busy) return
      setBusy(true)
      try {
        await insights.resolveMatch(scenarioId, current.candidate_id, resolution)
        await read()
      } catch (error) {
        setProblem(
          error instanceof RequestFailed
            ? error.message
            : 'We could not record that. Nothing was saved.',
        )
      } finally {
        setBusy(false)
      }
    },
    [current, busy, scenarioId, read],
  )

  // M and N, only while the drawer is open and only when nothing else has focus claims.
  useEffect(() => {
    if (!open) return
    function onKey(event: KeyboardEvent) {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement)
        return
      if (event.key === 'm' || event.key === 'M') void resolve('match')
      if (event.key === 'n' || event.key === 'N') void resolve('not_match')
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, resolve])

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent title="Review asset matches" onFinishLater={() => onOpenChange(false)}>
        <div className="border-b border-line px-4 py-3">
          <p className="mb-2 text-[13px] text-muted">
            {reviewed} of {total} reviewed
          </p>
          <Progress value={reviewed} max={total} label="Matches reviewed" />
        </div>

        <div className="flex-1 overflow-y-auto p-4" data-testid="match-queue">
          {problem && (
            <p role="alert" className="mb-3 text-[13px] text-high-fg">
              {problem}
            </p>
          )}

          {current ? (
            <>
              <p className="mb-3 text-[13px] leading-relaxed">
                <strong className="font-semibold">
                  {current.confidence === 'high' ? 'High confidence' : 'Moderate confidence'}
                </strong>{' '}
                — these records share a site and an asset type, and their names disagree.
                The loader never merges on a guess; this is yours to decide.
              </p>
              <div className="space-y-3" data-testid="match-candidate">
                <RecordCard
                  heading="Registry record"
                  icon={Landmark}
                  record={current.map_record}
                  other={current.candidate_record}
                />
                <RecordCard
                  heading="Unmatched candidate"
                  icon={Users}
                  record={current.candidate_record}
                  other={current.map_record}
                  accent
                />
              </div>
            </>
          ) : (
            <p role="status" className="text-[13px] text-muted">
              {total === 0
                ? 'Nothing was withheld for review in this storm.'
                : 'Every withheld match has been reviewed. The queue is clear.'}
            </p>
          )}
        </div>

        {current && (
          <div className="flex items-center justify-between gap-3 border-t border-line p-4">
            <Button
              onClick={() => void resolve('not_match')}
              disabled={busy}
              data-testid="match-not-a-match"
            >
              Not a match <Badge variant="outline">N</Badge>
            </Button>
            <Button
              variant="primary"
              onClick={() => void resolve('match')}
              disabled={busy}
              data-testid="match-confirm"
            >
              Match <Badge className="bg-white/20 text-white">M</Badge>
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
