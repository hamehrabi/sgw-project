'use client'

/**
 * DispatchSurface — the board's frame (design screen 5): the headline sentence, four
 * stat cards, the repair queue, the situation summary and the activity rail.
 *
 * Every number is read from the data; the headline is assembled from the same counts
 * the cards show, so the two cannot disagree. The rail records human actions and system
 * events, and can never say the system decided anything — there is no free-text path
 * into it (CHG-054), and the wording arrives assembled from the server.
 */

import { useCallback, useEffect, useState } from 'react'

import { Card } from '@/components/ui/card'
import { ActivityEntry, Board, dispatch, insights } from '@/lib/api'

import { DispatchBoard } from './DispatchBoard'
import { SituationSummaryCard } from './SituationSummaryCard'

function StatCard({
  label,
  value,
  accent,
  caption,
}: {
  label: string
  value: string
  accent?: boolean
  caption: string
}) {
  return (
    <Card className={accent ? 'border-l-2 border-l-high-fg p-4' : 'p-4'}>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-[24px] font-semibold leading-none ${accent ? 'text-high-fg' : ''}`}>
        {value}
      </p>
      {/* Every number carries a small grey caption with its source and age. */}
      <p className="mt-1.5 text-[11px] text-faint">{caption}</p>
    </Card>
  )
}

export function DispatchSurface({ scenarioId }: { scenarioId: string }) {
  const [board, setBoard] = useState<Board | null>(null)
  const [activity, setActivity] = useState<ActivityEntry[]>([])
  const [readAt, setReadAt] = useState<string | null>(null)

  const read = useCallback(async () => {
    try {
      const [boardBody, feed] = await Promise.all([
        dispatch.board(scenarioId),
        insights.activity(scenarioId),
      ])
      setBoard(boardBody)
      setActivity(feed.items)
      setReadAt(new Date().toISOString().slice(11, 16))
    } catch {
      // The board component beneath carries its own error state; the frame stays quiet.
    }
  }, [scenarioId])

  useEffect(() => {
    void read()
  }, [read])

  const openJobs = board ? board.items.filter((job) => job.status !== 'done') : []
  const critical = openJobs.filter((job) => job.priority === 'High').length
  const customers = openJobs.reduce((sum, job) => sum + job.customers_out, 0)

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_280px]">
      <div className="min-w-0 space-y-5">
        {board && (
          <>
            <h1 className="text-[26px] font-semibold leading-tight tracking-tight" data-testid="dispatch-headline">
              {board.job_count === 0
                ? 'No damage reported yet.'
                : `${openJobs.length} open job(s). ${
                    critical > 0
                      ? `${critical} involve a critical facility — those are first in the queue.`
                      : 'None involves a critical facility.'
                  }`}
            </h1>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Open jobs"
                value={String(openJobs.length)}
                caption={`from the board · as of ${readAt}`}
              />
              <StatCard
                label="Reports on the list"
                value={String(board.report_count)}
                caption={`${board.dismissed_report_count} dismissed as false alarms`}
              />
              <StatCard
                label="Critical facilities"
                value={String(critical)}
                accent={critical > 0}
                caption="jobs whose reports name one"
              />
              <StatCard
                label="Customers accounted for"
                value={customers.toLocaleString()}
                caption="sum of open reports · callers' own figures"
              />
            </div>
          </>
        )}

        <DispatchBoard scenarioId={scenarioId} onChanged={() => void read()} />

        <SituationSummaryCard scenarioId={scenarioId} onChanged={() => void read()} />
      </div>

      {/* ---- Recent activity: humans deciding, and system events. Never a system
              decision — the phrasing arrives assembled from the records (CHG-054). ---- */}
      <aside aria-label="Recent activity" data-testid="activity-rail">
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-muted">
          Recent activity
        </p>
        {activity.length === 0 ? (
          <p className="text-[13px] text-muted">Nothing recorded yet for this storm.</p>
        ) : (
          <ol className="relative space-y-4 border-l border-line pl-4">
            {activity.slice(0, 12).map((entry, index) => (
              <li key={index} className="relative">
                <span
                  className={`absolute -left-[21.5px] top-1.5 h-2 w-2 rounded-full ${
                    entry.kind === 'human' ? 'bg-teal' : 'bg-faint'
                  }`}
                  aria-hidden
                />
                <p className="text-[11px] text-faint">{entry.occurred_at.slice(11, 16)}</p>
                <p className="text-[13px] leading-snug">{entry.text}</p>
              </li>
            ))}
          </ol>
        )}
      </aside>
    </div>
  )
}
