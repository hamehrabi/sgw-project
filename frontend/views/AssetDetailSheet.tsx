'use client'

/**
 * AssetDetailSheet — one asset's rank, reasons and provenance, with the three triage
 * actions fully visible (design screen 4; CHG-055).
 *
 * It renders from the `RiskItem` already in the ranking response — no second fetch, no
 * asset-detail endpoint — which is what makes the consistency sweep true by
 * construction: the row, this drawer and Focus Mode show the same three reasons because
 * they are the same object.
 *
 * Confidence is words, never a percentage. Accept / Adjust / Dismiss each write a
 * decision record and nothing else: no crew moves, the asset stays ranked, and the
 * confirmation says so.
 */

import { AlertTriangle } from 'lucide-react'
import { useState } from 'react'

import { Badge, BandBadge } from '@/components/ui/badge'
import { StrengthBar } from '@/components/ui/bits'
import { Button } from '@/components/ui/button'
import { Label, Textarea } from '@/components/ui/field'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import { AssetSummary, insights, RequestFailed, RiskItem } from '@/lib/api'
import { isBlank, trimBlank } from '@/lib/blank'

/** Confidence in words, derived from what the inputs actually are: an estimated or old
 *  condition reading weakens the claim, and the sentence says so instead of a number. */
function confidence(item: RiskItem): string {
  const values = item.values
  const estimated = values.some((value) => value.estimated)
  if (estimated) return 'Rests partly on an estimated value'
  return 'Computed from the storm’s own records'
}

export function AssetDetailSheet({
  scenarioId,
  forecastRevision,
  item,
  summary,
  onClose,
  onRecorded,
}: {
  scenarioId: string
  forecastRevision: number
  item: RiskItem | null
  /** The stored summary for this asset at the revision on screen, when one exists
   *  (CHG-059). Read from the store by the parent — opening the drawer infers nothing. */
  summary?: AssetSummary | null
  onClose: () => void
  onRecorded: () => void
}) {
  const [noteFor, setNoteFor] = useState<'Adjust' | 'Dismiss' | null>(null)
  const [note, setNote] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function record(action: 'Accept' | 'Adjust' | 'Dismiss') {
    if (!item) return
    // The shared alphabet, not String.prototype.trim() — the store's idea of blank is
    // the only one (CHG-039), and this note is bound for decision_records.
    if ((action === 'Adjust' || action === 'Dismiss') && isBlank(note)) {
      setNoteFor(action)
      setProblem(
        noteFor === action ? `A note is required to ${action.toLowerCase()} this rank.` : null,
      )
      return
    }
    setSaving(true)
    setProblem(null)
    try {
      const recorded = await insights.triage(
        scenarioId,
        item.asset_id,
        forecastRevision,
        action,
        trimBlank(note) || null,
      )
      setDone(
        `Recorded: ${recorded.action} for ${recorded.asset_code} against forecast revision ` +
          `${recorded.forecast_revision} at ${recorded.occurred_at}. Written to the decision ` +
          'record — no crew has been moved and the asset stays ranked.',
      )
      setNote('')
      setNoteFor(null)
      onRecorded()
    } catch (error) {
      setProblem(
        error instanceof RequestFailed
          ? error.message
          : 'We could not record that. Nothing was saved — your note is still here.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <Sheet
      open={item !== null}
      onOpenChange={(open) => {
        if (!open) {
          setDone(null)
          setProblem(null)
          setNote('')
          setNoteFor(null)
          onClose()
        }
      }}
    >
      {item && (
        <SheetContent
          title={
            <span data-testid="asset-sheet-title">
              <span className="block text-[11px] font-semibold uppercase tracking-wide text-muted">
                {item.type}
              </span>
              {item.name || item.external_ids[0]}
            </span>
          }
        >
          <div className="flex-1 space-y-5 overflow-y-auto p-4" data-testid="asset-sheet">
            {/* The band, loudly, with the confidence in words beneath it. */}
            <div
              className={cn(
                'flex items-center gap-3 rounded-card border p-3',
                item.band === 'High' && 'border-high-fg/25 bg-high-bg',
                item.band === 'Medium' && 'border-medium-fg/25 bg-medium-bg',
                item.band === 'Low' && 'border-low-fg/25 bg-low-bg',
                item.band === null && 'border-line bg-rail',
              )}
            >
              {item.band === 'High' && (
                <AlertTriangle className="h-5 w-5 shrink-0 text-high-fg" aria-hidden />
              )}
              <div>
                <p className="text-[15px] font-semibold">
                  {item.band ? <BandBadge band={item.band} /> : <Badge>Not scored</Badge>}
                  {item.rank !== null && (
                    <span className="ml-2 text-[13px] font-medium text-ink-secondary">
                      Rank {item.rank}
                    </span>
                  )}
                </p>
                <p className="mt-0.5 text-[12px] text-muted">{confidence(item)}</p>
              </div>
            </div>

            {item.score === null ? (
              <div className="text-[13px] leading-relaxed">
                <p>
                  <strong>Not scored.</strong> {item.unscored_reason}
                </p>
                <p className="mt-1 text-muted">
                  It has <strong>not</strong> been judged low risk — it needs a person to
                  supply what is missing.
                </p>
              </div>
            ) : (
              <section>
                <h3 className="mb-2.5 text-[14px] font-semibold">Why this ranking</h3>
                <ul className="space-y-3">
                  {item.reasons.map((reason) => (
                    <li key={reason.factor} className="text-[13px] leading-relaxed">
                      <div className="mb-1 flex items-center justify-between gap-3">
                        <span>{reason.detail}</span>
                        <span className="shrink-0 text-[12px] font-medium text-muted">
                          {reason.strength}
                        </span>
                      </div>
                      <StrengthBar strength={reason.strength} />
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {summary && (
              <section data-testid="sheet-summary">
                <h3 className="mb-2 text-[14px] font-semibold">Summary</h3>
                <p className="whitespace-pre-line text-[13px] leading-relaxed">
                  {summary.text}
                </p>
                <p className="mt-1.5 text-[11px] text-muted">
                  {summary.label} · verified against this asset&rsquo;s computed factors ·
                  saved for forecast revision {summary.forecast_revision}
                </p>
              </section>
            )}

            <section>
              <h3 className="mb-2 text-[14px] font-semibold">Data provenance</h3>
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-muted">
                    <th className="py-1.5 pr-3 font-medium">Field</th>
                    <th className="py-1.5 pr-3 font-medium">Value</th>
                    <th className="py-1.5 pr-3 font-medium">Source</th>
                    <th className="py-1.5 font-medium">Age</th>
                  </tr>
                </thead>
                <tbody>
                  {item.values.map((value) => (
                    <tr key={value.name} className="border-b border-line/70">
                      <td className="py-1.5 pr-3 capitalize text-muted">
                        {value.name.replace(/_/g, ' ')}
                      </td>
                      <td className="py-1.5 pr-3">
                        {value.value ?? 'not recorded'}
                        {value.estimated && <em className="text-muted"> (est.)</em>}
                      </td>
                      <td className="py-1.5 pr-3 text-teal-deep">
                        {value.source ?? 'unknown'}
                      </td>
                      <td className="py-1.5 text-muted">{value.observed_at ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            {noteFor && (
              <div>
                <Label htmlFor="triage-note">Why {noteFor.toLowerCase()}? (required)</Label>
                <Textarea
                  id="triage-note"
                  rows={3}
                  maxLength={2000}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
              </div>
            )}

            {problem && (
              <p role="alert" className="text-[13px] text-high-fg">
                {problem}
              </p>
            )}
            {done && (
              <p role="status" data-testid="triage-recorded" className="text-[13px] text-low-fg">
                {done}
              </p>
            )}
          </div>

          {/* All three, fully visible — never an overflow menu here. */}
          {item.score !== null && (
            <div className="space-y-2 border-t border-line p-4">
              <Button
                variant="primary"
                className="w-full"
                disabled={saving}
                onClick={() => void record('Accept')}
              >
                Accept ranking
              </Button>
              <div className="grid grid-cols-2 gap-2">
                <Button disabled={saving} onClick={() => void record('Adjust')}>
                  Adjust
                </Button>
                <Button
                  variant="destructive-outline"
                  disabled={saving}
                  onClick={() => void record('Dismiss')}
                >
                  Dismiss
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      )}
    </Sheet>
  )
}
