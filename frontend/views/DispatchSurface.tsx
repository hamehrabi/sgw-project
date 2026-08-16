'use client'

/**
 * DispatchSurface — the board's frame (CHG-063, to the client's reference shape): the
 * headline sentence, the how-to line, four stat cards, the situation summary, the repair
 * queue, and a self-scrolling activity timeline on the right.
 *
 * Every number is read from the data; the headline is assembled from the same counts
 * the cards show, so the two cannot disagree. The rail records human actions and system
 * events, and can never say the system decided or generated anything — there is no
 * free-text path into it (CHG-054), and the wording arrives assembled from the server.
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
      <p className="font-mono text-[10px] font-semibold uppercase tracking-wider text-muted">
        {label}
      </p>
      <p
        className={`mt-1 font-mono text-[24px] font-semibold leading-none tabular-nums ${accent ? 'text-high-fg' : ''}`}
      >
        {value}
      </p>
      {/* Every number carries a small grey caption with where it came from. */}
      <p className="mt-1.5 text-[11px] text-faint">{caption}</p>
    </Card>
  )
}

export function DispatchSurface({ scenarioId }: { scenarioId: string }) {
  const [board, setBoard] = useState<Board | null>(null)
  const [activity, setActivity] = useState<ActivityEntry[]>([])
  const [highRisk, setHighRisk] = useState<number | null>(null)

  const read = useCallback(async () => {
    const [boardBody, feed, staging] = await Promise.allSettled([
      dispatch.board(scenarioId),
      insights.activity(scenarioId),
      insights.staging(scenarioId),
    ])
    if (boardBody.status === 'fulfilled') setBoard(boardBody.value)
    if (feed.status === 'fulfilled') setActivity(feed.value.items)
    if (staging.status === 'fulfilled') setHighRisk(staging.value.high_risk_count)
    // Each panel beneath carries its own error state; the frame stays quiet.
  }, [scenarioId])

  useEffect(() => {
    void read()
  }, [read])

  const openJobs = board ? board.items.filter((job) => job.status !== 'done') : []
  const needCrew = openJobs.filter(
    (job) => !job.assigned_to && (job.report_count > 0 || job.dismissed_report_count === 0),
  )
  const critical = openJobs.filter((job) =>
    job.reports.some((report) => report.asset_is_critical),
  ).length
  const customers = openJobs.reduce((sum, job) => sum + job.customers_out, 0)

  return (
    <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0 space-y-5">
        {board && (
          <>
            <div>
              <h1
                className="text-[26px] font-semibold leading-tight tracking-tight tabular-nums"
                data-testid="dispatch-headline"
              >
                {board.job_count === 0
                  ? 'No damage reported yet.'
                  : `${needCrew.length} incident(s) need a crew. ${
                      critical > 0
                        ? `${critical} affect critical facilities — those are at the top.`
                        : 'None affects a critical facility.'
                    }`}
              </h1>
              <p className="mt-1 text-[13px] leading-relaxed text-muted">
                Work the list top down. Use <strong>Assign crew</strong> to give a job an
                owner, <strong>Dismiss</strong> on a report that is a false alarm, and{' '}
                <strong>Mark restored</strong> once service is back. Every action is
                recorded — and nothing is dispatched.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Open incidents"
                value={String(openJobs.length)}
                caption="from filed damage reports"
              />
              <StatCard
                label="Critical facilities"
                value={String(critical)}
                accent={critical > 0}
                caption="open jobs whose reports name one"
              />
              <StatCard
                label="Customers out (open)"
                value={customers.toLocaleString()}
                caption="sum of open reports · callers' own figures"
              />
              <StatCard
                label="High-risk assets"
                value={highRisk === null ? '—' : String(highRisk)}
                caption="from the current ranking — not from reports"
              />
            </div>
          </>
        )}

        <SituationSummaryCard scenarioId={scenarioId} onChanged={() => void read()} />

        <DispatchBoard scenarioId={scenarioId} onChanged={() => void read()} />
      </div>

      {/* ---- Recent activity: humans deciding, and system events. Never a system
              decision — the phrasing arrives assembled from the records (CHG-054). ---- */}
      <aside
        aria-label="Recent activity"
        data-testid="activity-rail"
        className="xl:sticky xl:top-4 xl:max-h-[calc(100vh-7rem)] xl:overflow-y-auto xl:pr-1"
      >
        <p className="mb-1 font-mono text-[11px] font-semibold uppercase tracking-widest text-muted">
          Recent activity
        </p>
        <p className="mb-3 text-[11px] leading-relaxed text-faint">
          Every entry is a recorded decision or a system event from the audit trail —
          nothing is invented.
        </p>
        {activity.length === 0 ? (
          <p className="text-[13px] text-muted">
            Nothing recorded yet for this storm. Actions taken on the board will appear
            here, newest first.
          </p>
        ) : (
          <ol className="relative space-y-4 border-l border-line pl-4">
            {activity.slice(0, 25).map((entry, index) => (
              <li key={index} className="relative">
                <span
                  className={`absolute -left-[21.5px] top-1.5 h-2 w-2 rounded-full ${
                    entry.kind === 'human' ? 'bg-teal' : 'bg-faint'
                  }`}
                  aria-hidden
                />
                <p className="font-mono text-[11px] text-faint">
                  {entry.occurred_at.slice(0, 10)} · {entry.occurred_at.slice(11, 16)}
                </p>
                <p className="text-[13px] leading-snug">{entry.text}</p>
              </li>
            ))}
          </ol>
        )}
      </aside>
    </div>
  )
}
