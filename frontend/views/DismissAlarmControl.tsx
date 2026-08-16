'use client'

/**
 * DismissAlarmControl — clear a false alarm in one action (REQ-F-008, US-010).
 *
 * `frontend-component-spec.md` gives this component one rule and it contains the whole tension
 * in the requirement: **one action, but never anonymous — it captures who dismissed it and why.**
 *
 * - **One action.** One press clears it. There is no confirmation dialog, no second screen and
 *   no "are you sure": storm alarms are cheap by design, and a dispatcher who cannot clear a
 *   false one quickly stops clearing them, at which point the board stops being the shared
 *   picture REQ-F-007 built.
 * - **Never anonymous.** *Who* is the signed-in session and is never asked for — there is no
 *   field on this form that could name somebody else. *Why* is typed here, and the button is
 *   disabled until it has been. That is a courtesy, not the rule: the server refuses a blank
 *   reason and so does the database (`damage_reports_dismissal_is_attributed`, migration 014),
 *   so a screen with this check removed still cannot record an anonymous dismissal.
 * - **The typed reason survives a failed write.** A reason typed during a storm and lost to a
 *   failed request is the failure `PlacementForm` and `DispatchBoard` are both written against.
 * - **Nothing is dispatched.** Clearing a false alarm cancels no work and stands nobody down;
 *   the repair job stays on the board, and the control says so.
 *
 * States: idle, saving, error — the three `frontend-component-spec.md` names. There is no
 * success state, because success is the report leaving the working list: the board is re-read
 * and this control goes with the row it belonged to.
 */

import { useState } from 'react'

import { DISMISSAL_REASON_MAX, RequestFailed, dispatch, trimDismissalReason } from '@/lib/api'

export function DismissAlarmControl({
  reportId,
  onDismissed,
}: {
  reportId: string
  onDismissed: () => Promise<void> | void
}) {
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setSaving(true)
    setProblem(null)
    try {
      await dispatch.dismiss(reportId, trimDismissalReason(reason))
      // Not cleared on the way in. The field goes away with the row when the board re-reads,
      // and if the write failed the words are still here.
      await onDismissed()
    } catch (error) {
      setProblem(
        error instanceof RequestFailed
          ? error.message
          : 'We could not record that. Nothing was saved — what you typed is still here.',
      )
      setSaving(false)
    }
  }

  return (
    <form className="mt-1.5 flex flex-wrap items-center gap-2" onSubmit={submit} data-testid="dismiss-control">
      <label htmlFor={`dismiss-reason-${reportId}`} className="sr-only">
        Why is this a false alarm?
      </label>
      <input
        id={`dismiss-reason-${reportId}`}
        className="h-8 w-56 rounded-card border border-line px-2.5 text-[13px]"
        data-testid="dismiss-reason"
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder="Tree was already cleared"
        maxLength={DISMISSAL_REASON_MAX}
      />
      <button
        type="submit"
        className="inline-flex h-8 items-center rounded-card border border-line px-3 text-[12px] font-medium text-high-fg hover:bg-high-bg disabled:opacity-50"
        data-testid="dismiss-submit"
        // `trimDismissalReason`, never `String.prototype.trim()`. The two disagree about a
        // no-break space, an em space, U+200B and U+FEFF, and this layer being the stricter of
        // them is what hid the hole: the button stayed disabled while the API answered `201`
        // and stored the character as somebody's reason (CHG-037).
        disabled={saving || trimDismissalReason(reason).length === 0}
      >
        {saving ? 'Recording…' : 'Dismiss as false alarm'}
      </button>
      {problem && (
        <p role="alert" data-testid="dismiss-error" className="w-full text-[12px] text-high-fg">
          {problem}
        </p>
      )}
    </form>
  )
}
