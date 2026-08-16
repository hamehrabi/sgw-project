'use client'

/**
 * SituationSummaryCard — the drafted summary, its label, and the way into review
 * (CHG-040).
 *
 * The label is the honesty marker and always renders: *Drafted from platform data* means
 * the model's prose survived the verifier; *Assembled from platform data* means the
 * figures wrote it themselves. The state chip is the frozen vocabulary — Draft,
 * Approved, Sent — visible wherever the summary appears.
 *
 * Regenerate is the draft endpoint pressed again: a new appended row, never a rewrite
 * of what a reader may have seen.
 */

import { useCallback, useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { insights, RequestFailed, Summary } from '@/lib/api'

import { SummaryReviewSheet } from './SummaryReviewSheet'

const STATE_VARIANT = { Draft: 'draft', Approved: 'low', Sent: 'teal' } as const

export function SituationSummaryCard({
  scenarioId,
  onChanged,
}: {
  scenarioId: string
  onChanged?: () => void
}) {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [reviewing, setReviewing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)

  const read = useCallback(async () => {
    try {
      setSummary((await insights.summary(scenarioId)).summary)
      setLoaded(true)
    } catch {
      setLoaded(true)
    }
  }, [scenarioId])

  useEffect(() => {
    void read()
  }, [read])

  async function draft() {
    setBusy(true)
    setProblem(null)
    try {
      setSummary(await insights.draftSummary(scenarioId))
      onChanged?.()
    } catch (error) {
      setProblem(
        error instanceof RequestFailed
          ? error.message
          : 'We could not draft a summary. Nothing was changed.',
      )
    } finally {
      setBusy(false)
    }
  }

  if (!loaded) return null

  const text = summary ? (summary.approved_text ?? summary.draft_text) : null

  return (
    <>
      <Card data-testid="situation-summary">
        <CardHeader className="flex-row items-center justify-between">
          <div className="flex items-center gap-2.5">
            <CardTitle>Situation summary</CardTitle>
            {summary ? (
              <Badge variant={STATE_VARIANT[summary.state]} data-testid="summary-state">
                {summary.state}
              </Badge>
            ) : (
              <Badge variant="neutral" data-testid="summary-state">
                Not drafted
              </Badge>
            )}
          </div>
          {summary && (
            <p className="text-[12px] text-muted">
              {summary.label} · {summary.drafted_at.slice(11, 16)}
            </p>
          )}
        </CardHeader>
        <CardContent>
          {summary ? (
            <div className="space-y-3 text-[14px] leading-relaxed" data-testid="summary-text">
              {text?.split('\n\n').map((paragraph, index) => <p key={index}>{paragraph}</p>)}
            </div>
          ) : (
            <p className="text-[13px] text-muted">
              No summary has been drafted for this storm. Drafting assembles it from the
              platform&rsquo;s own figures; a person reviews and approves it before it goes
              anywhere.
            </p>
          )}
          {problem && (
            <p role="alert" className="mt-2 text-[13px] text-high-fg">
              {problem}
            </p>
          )}
        </CardContent>
        <CardFooter className="justify-between">
          <div className="flex gap-2">
            {summary?.state === 'Draft' && (
              <Button variant="primary" size="sm" onClick={() => setReviewing(true)}>
                Review and approve
              </Button>
            )}
            <Button size="sm" onClick={() => void draft()} disabled={busy}>
              {busy ? 'Drafting…' : summary ? 'Regenerate' : 'Draft summary'}
            </Button>
          </div>
          <p className="text-[11px] leading-4 text-muted">
            Every figure is checked against the platform before approval. The platform
            sends nothing anywhere.
          </p>
        </CardFooter>
      </Card>

      {summary && (
        <SummaryReviewSheet
          scenarioId={scenarioId}
          summary={summary}
          open={reviewing}
          onOpenChange={setReviewing}
          onChanged={() => {
            void read()
            onChanged?.()
          }}
        />
      )}
    </>
  )
}
