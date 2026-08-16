'use client'

/**
 * DispatchBoard — the repair queue as a worklist (REQ-F-007, CHG-063).
 *
 * **The screen a dispatcher works during the storm.** The standing rules, each naming a
 * failure it prevents:
 *
 * - **Two reports at one location render as one job, never two** (AC-007), and both
 *   reports stay visible under that job — the refusal to lose the second radio call.
 * - **The empty state reads "no damage reported", never "all clear".**
 * - **Nothing here dispatches** (BR-001): Assign crew, Mark restored and Reopen are
 *   records about a job — appended to `dispatch_actions`, phrased in the feed — and no
 *   message leaves the platform.
 * - **A false alarm is cleared per report, in one action, never anonymously**
 *   (REQ-F-008) — which is why Dismiss lives on the report line, not the job row.
 * - **The queue is ordered by impact and never by a risk score** (CHG-050).
 *
 * A location is a neighbourhood and never finer (CON-003, REQ-NF-007).
 */

import { useCallback, useEffect, useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Dialog, DialogClose, DialogContent } from '@/components/ui/dialog'
import { Input, Label } from '@/components/ui/field'
import { Board, DamageReport, RepairJob, RequestFailed, dispatch } from '@/lib/api'

import { DismissAlarmControl } from './DismissAlarmControl'

type Tab = 'needs_crew' | 'assigned' | 'closed' | 'all'

const TABS: { key: Tab; label: string }[] = [
  { key: 'needs_crew', label: 'Needs a crew' },
  { key: 'assigned', label: 'Assigned' },
  { key: 'closed', label: 'Closed / dismissed' },
  { key: 'all', label: 'All' },
]

/** The words a row's state renders as. Derived from stored facts, never typed. */
function statusOf(job: RepairJob): { word: string; closed: boolean; critical: boolean } {
  const critical = job.reports.some((report) => report.asset_is_critical)
  if (job.status === 'done') return { word: 'Restored', closed: true, critical }
  if (job.report_count === 0 && job.dismissed_report_count > 0)
    return { word: 'Dismissed', closed: true, critical }
  if (job.assigned_to) return { word: 'Assigned', closed: false, critical }
  return { word: 'Open', closed: false, critical }
}

function tabOf(job: RepairJob): Tab {
  const status = statusOf(job)
  if (status.closed) return 'closed'
  return job.assigned_to ? 'assigned' : 'needs_crew'
}

function ReportLine({ report, onDismissed }: { report: DamageReport; onDismissed: () => void }) {
  return (
    <tr data-testid="job-report" className="border-t border-line/60 bg-rail/40">
      <td />
      <td colSpan={6} className="px-3 py-1.5 text-[12px] text-muted">
        <span className="font-mono text-[11px]">{report.reported_at.slice(0, 16)}</span>
        {report.asset_name
          ? ` · ${report.asset_name}`
          : report.asset_id
            ? ` · asset ${report.asset_id}`
            : ' · no asset named'}
        {report.customers_out !== null &&
          ` · ~${report.customers_out.toLocaleString()} customers`}
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
      </td>
    </tr>
  )
}

function JobRows({
  job,
  index,
  nextUp,
  onDismissed,
  onAssign,
  onAct,
  busy,
}: {
  job: RepairJob
  index: number
  nextUp: boolean
  onDismissed: () => void
  onAssign: (job: RepairJob) => void
  onAct: (job: RepairJob, action: 'restore' | 'reopen') => void
  busy: string | null
}) {
  const status = statusOf(job)
  return (
    <tbody data-testid="job" className="border-t border-line">
      <tr className="align-top">
        <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[12px] text-muted">
          {String(index + 1).padStart(2, '0')}
          {nextUp && (
            <span className="block text-[10px] font-medium uppercase tracking-wide text-teal-deep">
              next up
            </span>
          )}
        </td>
        <td className="whitespace-nowrap px-3 py-2.5">
          <Badge variant={status.closed ? 'neutral' : status.critical ? 'high' : 'outline'}>
            {status.word}
            {status.critical && !status.closed && ' · critical'}
          </Badge>
        </td>
        <td className="px-3 py-2.5">
          <strong className="text-[13px]" data-testid="job-location">
            {job.location.neighbourhood ?? 'Location not recorded'}
          </strong>
          <span className="block text-[11px] text-muted" data-testid="job-count">
            {job.report_count} report(s) — one job for this location
          </span>
          {job.dismissed_report_count > 0 && (
            <span className="block text-[11px] text-muted" data-testid="job-dismissed">
              {job.dismissed_report_count} dismissed as a false alarm
            </span>
          )}
        </td>
        <td className="whitespace-nowrap px-3 py-2.5 text-right font-mono text-[12px] tabular-nums">
          {job.customers_out > 0 ? job.customers_out.toLocaleString() : '—'}
        </td>
        <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[12px] text-muted">
          {job.created_at.slice(0, 16)}
        </td>
        <td className="whitespace-nowrap px-3 py-2.5 text-[12px]">
          {job.assigned_to ?? <span className="text-faint">—</span>}
        </td>
        <td className="whitespace-nowrap px-3 py-2.5">
          <div className="flex flex-wrap justify-end gap-1.5">
            {!status.closed && (
              <Button
                size="sm"
                variant={job.assigned_to ? 'outline' : 'primary'}
                className="h-7 px-2.5 text-[12px]"
                data-testid="assign-crew"
                disabled={busy === job.job_id}
                onClick={() => onAssign(job)}
              >
                {job.assigned_to ? 'Reassign' : 'Assign crew'}
              </Button>
            )}
            {!status.closed && job.assigned_to && (
              <Button
                size="sm"
                variant="outline"
                className="h-7 px-2.5 text-[12px]"
                data-testid="mark-restored"
                disabled={busy === job.job_id}
                onClick={() => onAct(job, 'restore')}
              >
                Mark restored
              </Button>
            )}
            {job.status === 'done' && (
              <Button
                size="sm"
                variant="outline"
                className="h-7 px-2.5 text-[12px]"
                data-testid="reopen-job"
                disabled={busy === job.job_id}
                onClick={() => onAct(job, 'reopen')}
              >
                Reopen
              </Button>
            )}
          </div>
        </td>
      </tr>
      {job.reports.map((report) => (
        <ReportLine key={report.report_id} report={report} onDismissed={onDismissed} />
      ))}
    </tbody>
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
  const [tab, setTab] = useState<Tab>('needs_crew')
  const [query, setQuery] = useState('')
  const [assigning, setAssigning] = useState<RepairJob | null>(null)
  const [crew, setCrew] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [neighbourhood, setNeighbourhood] = useState('')
  const [customers, setCustomers] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const read = useCallback(async () => {
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

  const counts = useMemo(() => {
    const jobs = board?.items ?? []
    return {
      needs_crew: jobs.filter((job) => tabOf(job) === 'needs_crew').length,
      assigned: jobs.filter((job) => tabOf(job) === 'assigned').length,
      closed: jobs.filter((job) => tabOf(job) === 'closed').length,
      all: jobs.length,
    }
  }, [board])

  const visible = useMemo(() => {
    const jobs = board?.items ?? []
    const needle = query.trim().toLowerCase()
    return jobs
      .filter((job) => tab === 'all' || tabOf(job) === tab)
      .filter(
        (job) =>
          !needle ||
          (job.location.neighbourhood ?? '').toLowerCase().includes(needle) ||
          (job.assigned_to ?? '').toLowerCase().includes(needle),
      )
  }, [board, tab, query])

  async function act(job: RepairJob, action: 'restore' | 'reopen') {
    setBusy(job.job_id)
    setNotice(null)
    try {
      if (action === 'restore') await dispatch.markRestored(job.job_id)
      else await dispatch.reopenJob(job.job_id)
      setNotice(
        action === 'restore'
          ? `Marked the job at ${job.location.neighbourhood ?? 'the recorded location'} restored. Recorded — nothing was sent anywhere.`
          : `Reopened the job at ${job.location.neighbourhood ?? 'the recorded location'}. Recorded — nothing was sent anywhere.`,
      )
      await refresh()
    } catch (error) {
      setNotice(
        error instanceof RequestFailed
          ? error.message
          : 'We could not record that. Nothing was changed.',
      )
    } finally {
      setBusy(null)
    }
  }

  async function assign(event: React.FormEvent) {
    event.preventDefault()
    if (!assigning) return
    setBusy(assigning.job_id)
    setNotice(null)
    try {
      await dispatch.assignCrew(assigning.job_id, crew)
      setNotice(
        `Assigned ${crew.trim()} to the job at ${assigning.location.neighbourhood ?? 'the recorded location'}. ` +
          'Recorded in the audit trail — no message left the platform.',
      )
      setAssigning(null)
      setCrew('')
      await refresh()
    } catch (error) {
      setNotice(
        error instanceof RequestFailed
          ? error.message
          : 'We could not record that. Nothing was changed — the crew label is still here.',
      )
    } finally {
      setBusy(null)
    }
  }

  async function submitReport(event: React.FormEvent) {
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

  const total = board?.items.length ?? 0

  return (
    <section data-testid="dispatch-board" className="space-y-4">
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

      {state === 'ready' && board && (
        <Card className="overflow-hidden">
          <div className="space-y-2.5 border-b border-line p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="font-mono text-[13px] font-semibold">
                Repair queue — {visible.length} shown of {total}
              </p>
              <div className="flex items-center gap-2">
                <Input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search location or crew"
                  aria-label="Search location or crew"
                  className="h-8 w-56 text-[12px]"
                />
                {query && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 px-2 text-[12px]"
                    onClick={() => setQuery('')}
                  >
                    Clear search
                  </Button>
                )}
              </div>
            </div>
            <p className="text-[12px] text-muted" data-testid="board-summary">
              One row per repair job — from the dataset&rsquo;s outage records and filed
              reports, worst first: a critical facility, then customers accounted for,
              never a risk score. Row 1 is the next job to hand out. {board.report_count}{' '}
              report(s) across {board.job_count} job(s); two reports at one location are
              one job.
            </p>
            <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter">
              <span className="mr-1 font-mono text-[10px] uppercase tracking-wider text-muted">
                Show
              </span>
              {TABS.map((entry) => (
                <button
                  key={entry.key}
                  type="button"
                  data-testid={`queue-tab-${entry.key}`}
                  aria-pressed={tab === entry.key}
                  onClick={() => setTab(entry.key)}
                  className={
                    tab === entry.key
                      ? 'rounded-card bg-ink px-2.5 py-1 text-[12px] font-medium text-background'
                      : 'rounded-card border border-line bg-background px-2.5 py-1 text-[12px] hover:bg-panel'
                  }
                >
                  {entry.label} ({counts[entry.key]})
                </button>
              ))}
            </div>
            {notice && (
              <p role="status" data-testid="queue-notice" className="text-[12px] text-teal-deep">
                {notice}
              </p>
            )}
          </div>

          {/* Empty means nothing on the board at all — including a report no job was
              raised for. `items.length` alone would call the board empty while work sat
              on it (CHG-022). */}
          {total === 0 && board.unattached_reports.length === 0 ? (
            <p role="status" data-testid="board-empty" className="p-4 text-[13px]">
              <strong>No damage reported.</strong> Nothing has been called in yet — this is
              not a statement that the network is all clear.
            </p>
          ) : visible.length === 0 ? (
            <p role="status" data-testid="queue-filter-empty" className="p-4 text-[13px]">
              Nothing matches this view. {total} job(s) sit under the other tabs — switch
              tabs{query ? ' or clear the search' : ''}.
            </p>
          ) : (
            <div className="max-h-[65vh] overflow-auto">
              <table className="w-full border-collapse text-left">
                <thead className="sticky top-0 z-10 bg-rail">
                  <tr className="font-mono text-[10px] uppercase tracking-wider text-muted">
                    <th className="px-3 py-2 font-medium">#</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2 font-medium">Location</th>
                    <th className="px-3 py-2 text-right font-medium">Customers</th>
                    <th className="px-3 py-2 font-medium">Reported</th>
                    <th className="px-3 py-2 font-medium">Crew</th>
                    <th className="px-3 py-2 text-right font-medium">What you can do</th>
                  </tr>
                </thead>
                {visible.map((job, index) => (
                  <JobRows
                    key={job.job_id}
                    job={job}
                    index={index}
                    nextUp={index === 0 && tab === 'needs_crew'}
                    onDismissed={() => void refresh()}
                    onAssign={(chosen) => {
                      setCrew(chosen.assigned_to ?? '')
                      setAssigning(chosen)
                    }}
                    onAct={(chosen, action) => void act(chosen, action)}
                    busy={busy}
                  />
                ))}
              </table>
            </div>
          )}

          {/* Reports that belong to no repair job are still work and still on this board
              (CHG-022) — a report nobody can find is a lost radio call. */}
          {board.unattached_reports.length > 0 && (
            <section className="border-t border-line bg-rail p-3" data-testid="board-unattached">
              <h3 className="text-[13px] font-medium">
                {board.unattached_reports.length} report(s) with no repair job raised yet —
                still work, still on this board
              </h3>
              <table className="w-full">
                <tbody>
                  {board.unattached_reports.map((report) => (
                    <ReportLine
                      key={report.report_id}
                      report={report}
                      onDismissed={() => void refresh()}
                    />
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {/* Filing a report is AC-007's first half and stays on the board it feeds. */}
          <form onSubmit={submitReport} className="flex flex-wrap items-end gap-3 border-t border-line p-4">
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
              A neighbourhood, never a street or a household — the record is kept at the
              level the decision needs and no finer. Adding a report sends nobody anywhere.
            </p>
            {problem && (
              <p role="alert" data-testid="board-error" className="w-full text-[13px] text-high-fg">
                {problem}
              </p>
            )}
          </form>
        </Card>
      )}

      {/* Assign / Reassign — a crew label people chose, recorded. Nothing is sent. */}
      <Dialog open={assigning !== null} onOpenChange={(open) => !open && setAssigning(null)}>
        {assigning && (
          <DialogContent
            title={`Assign a crew — ${assigning.location.neighbourhood ?? 'location not recorded'}`}
          >
            <form onSubmit={assign} className="space-y-3 p-4" data-testid="assign-dialog">
              <div>
                <Label htmlFor="crew-label">Crew</Label>
                <Input
                  id="crew-label"
                  value={crew}
                  onChange={(event) => setCrew(event.target.value)}
                  placeholder="Line crew 2"
                  maxLength={120}
                  autoFocus
                />
              </div>
              <p className="text-[12px] leading-relaxed text-muted">
                This records who owns the job. No message is sent to the crew, and nothing
                is dispatched — the platform has no path that could (BR-001).
              </p>
              <div className="flex justify-end gap-2">
                <DialogClose asChild>
                  <Button type="button" variant="outline" size="sm">
                    Cancel
                  </Button>
                </DialogClose>
                <Button type="submit" variant="primary" size="sm" data-testid="assign-submit">
                  Record assignment
                </Button>
              </div>
            </form>
          </DialogContent>
        )}
      </Dialog>
    </section>
  )
}
