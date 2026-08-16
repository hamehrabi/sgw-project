'use client'

/**
 * SummaryReviewSheet — review, verify and approve one summary (design screen 8;
 * CHG-040).
 *
 * The verification table lists **every** extracted figure, not a fixed four rows — a
 * fixed table is how the fifth invention gets past a reviewer. Any mismatch **disables**
 * approval with the reason shown, and the disabled button is the door, not the lock:
 * the server re-verifies the exact text being approved and refuses on any violation, so
 * a browser that re-enabled the button changes nothing.
 *
 * Approving records the approver and the time on the row. "Approve and mark sent"
 * records that a person distributed it — the platform sends nothing anywhere (BR-001).
 */

import { CheckCircle2, XCircle } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/field'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { insights, RequestFailed, Summary, SummaryVerificationEntry } from '@/lib/api'

export function SummaryReviewSheet({
  scenarioId,
  summary,
  open,
  onOpenChange,
  onChanged,
}: {
  scenarioId: string
  summary: Summary
  open: boolean
  onOpenChange: (open: boolean) => void
  onChanged: () => void
}) {
  const [text, setText] = useState(summary.draft_text)
  const [verification, setVerification] = useState(summary.verification)
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setText(summary.draft_text)
    setVerification(summary.verification)
    setProblem(null)
  }, [summary])

  const violations = useMemo(
    () => verification.entries.filter((entry) => !entry.allowed),
    [verification],
  )
  // Edited text has not been re-judged yet; the server is the judge either way, so an
  // edit re-enables nothing until it comes back verified.
  const edited = text !== summary.draft_text

  async function approve(alsoSend: boolean) {
    setBusy(true)
    setProblem(null)
    try {
      const approved = await insights.approveSummary(scenarioId, summary.summary_id, text)
      if (alsoSend) await insights.markSummarySent(scenarioId, approved.summary_id)
      onChanged()
      onOpenChange(false)
    } catch (error) {
      if (error instanceof RequestFailed && error.code === 'verification_failed') {
        // The server's re-verification of the edited text — rendered, not paraphrased.
        const returned = error.body.verification as Summary['verification'] | undefined
        setProblem(error.message)
        if (returned) setVerification(returned)
        onChanged()
      } else {
        setProblem(
          error instanceof RequestFailed
            ? error.message
            : 'We could not record that. Nothing was changed.',
        )
      }
    } finally {
      setBusy(false)
    }
  }

  function verdictRow(entry: SummaryVerificationEntry, index: number) {
    const platform =
      entry.platform_value && typeof entry.platform_value === 'object'
        ? String((entry.platform_value as { value?: unknown }).value ?? '—')
        : String(entry.platform_value ?? '—')
    return (
      <tr key={index} className="border-b border-line/70">
        <td className="py-1.5 pr-3 capitalize text-muted">{entry.kind}</td>
        <td className="py-1.5 pr-3 font-medium">{entry.token}</td>
        <td className="py-1.5 pr-3 text-muted">{platform}</td>
        <td className="py-1.5">
          {entry.allowed ? (
            <CheckCircle2 className="h-4 w-4 text-low-fg" aria-label="matches" />
          ) : (
            <XCircle className="h-4 w-4 text-high-fg" aria-label="not in the platform data" />
          )}
        </td>
      </tr>
    )
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        title={
          <span className="flex items-center gap-2">
            Review situation summary
            <Badge variant="draft">{summary.state}</Badge>
          </span>
        }
        className="sm:max-w-xl"
      >
        <div className="flex-1 space-y-5 overflow-y-auto p-4" data-testid="summary-review">
          <p className="text-[12px] text-muted">
            {summary.label} · {summary.drafted_at.slice(11, 16)}
          </p>

          <div>
            <p className="mb-1.5 text-[13px] font-medium text-ink-secondary">Summary content</p>
            <Textarea
              rows={9}
              value={text}
              onChange={(event) => setText(event.target.value)}
              aria-label="Summary content"
            />
            {edited && (
              <p className="mt-1 text-[12px] text-muted">
                Edited — the server re-checks this exact text when you approve it.
              </p>
            )}
          </div>

          <section>
            <h3 className="text-[14px] font-semibold">Every figure, checked against the data</h3>
            <p className="mb-2 text-[12px] text-muted">
              {violations.length === 0
                ? 'Values in the summary match current platform records.'
                : `${violations.length} claim(s) are not in the platform data. Approval is blocked until they match.`}
            </p>
            <table className="w-full text-[12px]" data-testid="verification-table">
              <thead>
                <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-muted">
                  <th className="py-1.5 pr-3 font-medium">Kind</th>
                  <th className="py-1.5 pr-3 font-medium">In the summary</th>
                  <th className="py-1.5 pr-3 font-medium">In the platform</th>
                  <th className="py-1.5 font-medium">Match</th>
                </tr>
              </thead>
              <tbody>{verification.entries.map(verdictRow)}</tbody>
            </table>
          </section>

          {problem && (
            <p role="alert" className="text-[13px] text-high-fg">
              {problem}
            </p>
          )}
        </div>

        <div className="space-y-2 border-t border-line p-4">
          <div className="flex justify-end gap-2">
            <Button size="sm" onClick={() => onOpenChange(false)}>
              Save as draft
            </Button>
            <Button
              size="sm"
              variant="primary"
              data-testid="approve-summary"
              // THE BLOCK: a mismatch disables approval with the reason shown. The
              // server refuses regardless — this is the door, not the lock.
              disabled={busy || summary.state !== 'Draft' || (violations.length > 0 && !edited)}
              onClick={() => void approve(true)}
            >
              Approve and mark sent
            </Button>
          </div>
          <p className="text-right text-[11px] leading-4 text-muted">
            Approving records your name and the time. Distribution is a thing a person
            does — the platform sends nothing anywhere.
          </p>
        </div>
      </SheetContent>
    </Sheet>
  )
}
