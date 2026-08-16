'use client'

/**
 * DispatchBoard — the shared damage and repair job list (REQ-F-007).
 *
 * **The screen a dispatcher works during the storm**, replacing a picture assembled in one
 * person's head from radio, alarms and a whiteboard. Four rules, and each names a failure:
 *
 * - **Two reports at one location render as one job, never two** (AC-007). The grouping is the
 *   server's — the database refuses a second job for a location — and this list only shows it.
 *   A client-side merge would be a second implementation of the rule, free to disagree.
 * - **Both reports stay visible under that job.** One job is the de-duplication; both visible
 *   is the refusal to lose the second radio call. A board that shows one is worse than useless
 *   during the ten minutes somebody rings back about the same street.
 * - **The empty state reads "no damage reported", never "all clear".** An empty board during a
 *   storm is indistinguishable from a network with nothing wrong with it.
 * - **Nothing here dispatches.** Filing a report records that work exists. No crew is moved and
 *   no message leaves the platform (BR-001, BR-005), and the form says so.
 * - **A false alarm is cleared in one action and never anonymously** (REQ-F-008). Every open
 *   report carries a `DismissAlarmControl`; clearing one takes it off the working list and
 *   leaves the job it was filed against on the board, reading *explained* rather than *empty*
 *   (CHG-020). Nothing is cancelled and nobody is stood down.
 *
 * A location is a neighbourhood and never finer — the field accepts nothing else, and the
 * server refuses an address (CON-003, REQ-NF-007). It computes no score, rank or band.
 */

import { useCallback, useEffect, useState } from 'react'

import { Board, DamageReport, RepairJob, RequestFailed, dispatch } from '@/lib/api'

import { DismissAlarmControl } from './DismissAlarmControl'

/**
 * One report on the board, with the one-action way to clear it if it was a false alarm
 * (REQ-F-008). The control sits on the report rather than on the job, because a job may answer
 * several calls and clearing one of them is not a judgement about the others.
 */
function Report({ report, onDismissed }: { report: DamageReport; onDismissed: () => void }) {
  return (
    <li data-testid="job-report">
      <span className="job__time">{report.reported_at}</span>
      {report.asset_id ? ` · asset ${report.asset_id}` : ' · no asset named'}
      {report.status !== 'open' && <span className="badge"> {report.status}</span>}
      <DismissAlarmControl reportId={report.report_id} onDismissed={onDismissed} />
    </li>
  )
}

function Job({ job, onDismissed }: { job: RepairJob; onDismissed: () => void }) {
  return (
    <li className="job" data-testid="job">
      <div className="job__head">
        <strong data-testid="job-location">
          {job.location.neighbourhood ?? 'Location not recorded'}
        </strong>{' '}
        <span className="job__status">{job.status.replace('_', ' ')}</span>
        <span className="job__count" data-testid="job-count">
          {' '}
          · {job.report_count} report(s) — one job for this location
        </span>
        {/* A job whose reports have all been dismissed still has a place and a history. An
            empty job with no explanation beside it is one of the three states on this screen
            that read as good news when they are not. */}
        {job.dismissed_report_count > 0 && (
          <span className="job__dismissed" data-testid="job-dismissed">
            {' '}
            · {job.dismissed_report_count} dismissed as a false alarm
          </span>
        )}
      </div>
      <ul className="job__reports">
        {job.reports.map((report) => (
          <Report key={report.report_id} report={report} onDismissed={onDismissed} />
        ))}
      </ul>
    </li>
  )
}

/**
 * Reports that belong to no repair job (CHG-022).
 *
 * `repair_job_id` is optional in the schema, so this state exists — and a board that renders
 * only jobs puts those reports on no screen at all. A shared dispatch board that silently drops
 * work is the one thing `frontend-component-spec.md` says this screen must never do, and an
 * empty screen must never read as safety.
 */
function Unattached({
  reports,
  onDismissed,
}: {
  reports: DamageReport[]
  onDismissed: () => void
}) {
  if (reports.length === 0) return null
  return (
    <section className="board__unattached" data-testid="board-unattached">
      <h3>
        {reports.length} report(s) with no repair job raised yet — still work, still on this
        board
      </h3>
      <ul className="job__reports">
        {reports.map((report) => (
          <Report key={report.report_id} report={report} onDismissed={onDismissed} />
        ))}
      </ul>
    </section>
  )
}

export function DispatchBoard({ scenarioId }: { scenarioId: string }) {
  const [board, setBoard] = useState<Board | null>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [neighbourhood, setNeighbourhood] = useState('')
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

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!neighbourhood.trim()) {
      setProblem('Which neighbourhood is this report for?')
      return
    }
    setSaving(true)
    setProblem(null)
    try {
      await dispatch.fileReport(scenarioId, neighbourhood.trim(), null)
      // Cleared only after the write succeeded. A report typed during a storm and lost to a
      // failed request is the thing this screen exists to stop happening.
      setNeighbourhood('')
      await read()
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
    <section className="board" data-testid="dispatch-board">
      <form className="board__form" onSubmit={submit}>
        <label htmlFor="damage-neighbourhood">Report damage in a neighbourhood</label>
        <input
          id="damage-neighbourhood"
          value={neighbourhood}
          onChange={(event) => setNeighbourhood(event.target.value)}
          placeholder="Northgate"
          maxLength={120}
        />
        <button type="submit" disabled={saving}>
          {saving ? 'Recording…' : 'Add report'}
        </button>
        <p className="board__note">
          A neighbourhood, never a street or a household — the record is kept at the level the
          decision needs and no finer. Adding a report sends nobody anywhere.
        </p>
        {problem && (
          <p role="alert" data-testid="board-error">
            {problem}
          </p>
        )}
      </form>

      {state === 'loading' && <p role="status">Loading the board…</p>}

      {state === 'error' && (
        <p role="alert">
          We could not load the board. The storm is still loaded — try again. This is not a
          statement that nothing has been reported.
        </p>
      )}

      {/* Empty means nothing on the board at all — including a report no job was raised for.
          Testing `items.length` alone would call the board empty while work sat on it. */}
      {state === 'ready' &&
        board &&
        board.items.length === 0 &&
        board.unattached_reports.length === 0 && (
          <p role="status" data-testid="board-empty">
            <strong>No damage reported.</strong> Nothing has been called in yet — this is not a
            statement that the network is all clear.
          </p>
        )}

      {state === 'ready' &&
        board &&
        (board.items.length > 0 || board.unattached_reports.length > 0) && (
          <>
            <p className="board__summary" data-testid="board-summary">
              {board.report_count} report(s) across {board.job_count} job(s). Two reports at one
              location are one job, so no crew is sent where another already is.
            </p>
            <ul className="board__jobs">
              {board.items.map((job) => (
                <Job key={job.job_id} job={job} onDismissed={() => void read()} />
              ))}
            </ul>
            <Unattached
              reports={board.unattached_reports}
              onDismissed={() => void read()}
            />
          </>
        )}
    </section>
  )
}
