'use client'

/**
 * DispatchBoard — the shared damage and repair job list (REQ-F-007).
 *
 * **The screen a dispatcher works during the storm.** Five rules, each naming a failure:
 *
 * - **Two reports at one location render as one job, never two** (AC-007). The grouping
 *   is the server's; this list only shows it.
 * - **Both reports stay visible under that job** — the refusal to lose the second radio
 *   call.
 * - **The empty state reads "no damage reported", never "all clear".**
 * - **Nothing here dispatches** (BR-001, BR-005), and the form says so.
 * - **A false alarm is cleared in one action and never anonymously** (REQ-F-008).
 *
 * **The queue is ordered by impact and never by a risk score** (CHG-050): a critical
 * facility first, then customers accounted for — the order arrives from the server, and
 * the priority word is the frozen vocabulary in its tint. Risk orders the planning list;
 * folding it into this queue is how a computed number starts moving crews.
 *
 * A location is a neighbourhood and never finer (CON-003, REQ-NF-007).
 */

import { useCallback, useEffect, useState } from 'react'

import { Badge, BandBadge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input, Label } from '@/components/ui/field'
import { Board, DamageReport, RepairJob, RequestFailed, dispatch } from '@/lib/api'

import { DismissAlarmControl } from './DismissAlarmControl'

function Report({ report, onDismissed }: { report: DamageReport; onDismissed: () => void }) {
  return (
    <li data-testid="job-report" className="border-t border-line/70 py-2 text-[12px] text-muted">
      <span>{report.reported_at}</span>
      {report.asset_id ? ` · asset ${report.asset_id}` : ' · no asset named'}
      {report.customers_out !== null && ` · ~${report.customers_out.toLocaleString()} customers`}
      {report.asset_is_critical && (
        <Badge variant="high" className="ml-1.5">
          critical facility
        </Badge>
      )}
      {report.status !== 'open' && (
        <Badge variant="outline" className="ml-1.5">
          {report.status}
        </Badge>
      )}
      <DismissAlarmControl reportId={report.report_id} onDismissed={onDismissed} />
    </li>
  )
}

function Job({ job, onDismissed }: { job: RepairJob; onDismissed: () => void }) {
  return (
    <li className="rounded-card border border-line bg-background p-3" data-testid="job">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        {/* Impact priority, in the frozen vocabulary and its tint — never "Critical",
            never "Standard", and never a risk score. */}
        <BandBadge band={job.priority} />
        <strong className="text-[14px]" data-testid="job-location">
          {job.location.neighbourhood ?? 'Location not recorded'}
        </strong>
        <span className="text-[12px] text-muted">{job.status.replace('_', ' ')}</span>
        {job.customers_out > 0 && (
          <span className="text-[12px] text-muted">
            · ~{job.customers_out.toLocaleString()} customers accounted for
          </span>
        )}
        <span className="text-[12px] text-muted" data-testid="job-count">
          · {job.report_count} report(s) — one job for this location
        </span>
        {/* A job whose reports have all been dismissed still has a place and a history —
            it reads as explained, never as empty. */}
        {job.dismissed_report_count > 0 && (
          <span className="text-[12px] text-muted" data-testid="job-dismissed">
            · {job.dismissed_report_count} dismissed as a false alarm
          </span>
        )}
      </div>
      <ul className="mt-1.5">
        {job.reports.map((report) => (
          <Report key={report.report_id} report={report} onDismissed={onDismissed} />
        ))}
      </ul>
    </li>
  )
}

function Unattached({
  reports,
  onDismissed,
}: {
  reports: DamageReport[]
  onDismissed: () => void
}) {
  if (reports.length === 0) return null
  return (
    <section
      className="rounded-card border border-line bg-rail p-3"
      data-testid="board-unattached"
    >
      <h3 className="text-[13px] font-medium">
        {reports.length} report(s) with no repair job raised yet — still work, still on this
        board
      </h3>
      <ul>
        {reports.map((report) => (
          <Report key={report.report_id} report={report} onDismissed={onDismissed} />
        ))}
      </ul>
    </section>
  )
}

export function DispatchBoard({
  scenarioId,
  onChanged,
}: {
  scenarioId: string
  /** The stat cards and the rail read the same facts; a write here refreshes them. */
  onChanged?: () => void
}) {
  const [board, setBoard] = useState<Board | null>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [neighbourhood, setNeighbourhood] = useState('')
  const [customers, setCustomers] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const read = useCallback(async () => {
    setState('loading')
    try {
      setBoard(await dispatch.board(scenarioId))
      setState('ready')
    } catch {
      setState('error')
    }
  }, [scenarioId])

  useEffect(() => {
    void read()
  }, [read])

  const refresh = useCallback(async () => {
    await read()
    onChanged?.()
  }, [read, onChanged])

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!neighbourhood.trim()) {
      setProblem('Which neighbourhood is this report for?')
      return
    }
    setSaving(true)
    setProblem(null)
    try {
      await dispatch.fileReport(
        scenarioId,
        neighbourhood.trim(),
        null,
        customers.trim() ? Number(customers) : null,
      )
      // Cleared only after the write succeeded. A report typed during a storm and lost
      // to a failed request is the thing this screen exists to stop happening.
      setNeighbourhood('')
      setCustomers('')
      await refresh()
    } catch (error) {
      setProblem(
        error instanceof RequestFailed
          ? error.message
          : 'We could not record that. Nothing was saved — what you typed is still here.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <section data-testid="dispatch-board" className="space-y-4">
      <Card className="p-4">
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          <div className="min-w-56 flex-1">
            <Label htmlFor="damage-neighbourhood">Report damage in a neighbourhood</Label>
            <Input
              id="damage-neighbourhood"
              value={neighbourhood}
              onChange={(event) => setNeighbourhood(event.target.value)}
              placeholder="Northgate"
              maxLength={120}
            />
          </div>
          <div className="w-40">
            <Label htmlFor="damage-customers">Customers out (if known)</Label>
            <Input
              id="damage-customers"
              type="number"
              min={0}
              value={customers}
              onChange={(event) => setCustomers(event.target.value)}
              placeholder="unknown"
            />
          </div>
          <Button type="submit" disabled={saving}>
            {saving ? 'Recording…' : 'Add report'}
          </Button>
          <p className="w-full text-[12px] leading-relaxed text-muted">
            A neighbourhood, never a street or a household — the record is kept at the level the
            decision needs and no finer. Adding a report sends nobody anywhere.
          </p>
          {problem && (
            <p role="alert" data-testid="board-error" className="w-full text-[13px] text-high-fg">
              {problem}
            </p>
          )}
        </form>
      </Card>

      {state === 'loading' && (
        <p role="status" className="text-[13px] text-muted">
          Loading the board…
        </p>
      )}

      {state === 'error' && (
        <p role="alert" className="text-[13px] text-high-fg">
          We could not load the board. The storm is still loaded — try again. This is not a
          statement that nothing has been reported.
        </p>
      )}

      {/* Empty means nothing on the board at all — including a report no job was raised
          for. Testing `items.length` alone would call the board empty while work sat on it. */}
      {state === 'ready' &&
        board &&
        board.items.length === 0 &&
        board.unattached_reports.length === 0 && (
          <p role="status" data-testid="board-empty" className="text-[13px]">
            <strong>No damage reported.</strong> Nothing has been called in yet — this is not a
            statement that the network is all clear.
          </p>
        )}

      {state === 'ready' &&
        board &&
        (board.items.length > 0 || board.unattached_reports.length > 0) && (
          <>
            <p className="text-[13px] text-muted" data-testid="board-summary">
              {board.report_count} report(s) across {board.job_count} job(s). Two reports at one
              location are one job, so no crew is sent where another already is. Ordered by
              impact — never by a risk score.
            </p>
            <ul className="space-y-2">
              {board.items.map((job) => (
                <Job key={job.job_id} job={job} onDismissed={() => void refresh()} />
              ))}
            </ul>
            <Unattached reports={board.unattached_reports} onDismissed={() => void refresh()} />
          </>
        )}
    </section>
  )
}
