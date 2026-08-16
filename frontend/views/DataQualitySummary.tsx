'use client'

/**
 * DataQualitySummary — what the parse found, sized for a person (CHG-047).
 *
 * The rule is the screen's, and it is a hard one: **at most three findings that need a
 * human decision are visible**, each with one action, and everything the loader already
 * handled collapses behind one line. A wall of warnings is how the three that matter get
 * missed. Every finding names the file the parse actually reported it against — read
 * from the stored row, never hard-coded here.
 *
 * Read from stored rows, so this screen works tomorrow, and after FF-003 has deleted
 * every source file.
 */

import { AlertTriangle, Info } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Finding, insights, RequestFailed } from '@/lib/api'

/** The one action each decidable defect offers, in the button's own words. */
const ACTIONS: Record<number, string> = {
  1: 'Review',
  3: 'OK, use forecast',
  4: 'OK, exclude',
}

export function DataQualitySummary({
  scenarioId,
  assetCount,
  onReviewMatches,
}: {
  scenarioId: string
  assetCount: number | null
  onReviewMatches: () => void
}) {
  const [findings, setFindings] = useState<Finding[] | null>(null)
  const [problem, setProblem] = useState<string | null>(null)

  const read = useCallback(async () => {
    try {
      setFindings((await insights.findings(scenarioId)).items)
      setProblem(null)
    } catch {
      setProblem('We could not load the data-quality findings. The storm itself is unaffected.')
    }
  }, [scenarioId])

  useEffect(() => {
    void read()
  }, [read])

  async function resolve(group: Finding[]) {
    if (group[0].defect === 1) {
      // Defect 1's action is a review, not a resolution — the queue is the answer.
      onReviewMatches()
      return
    }
    try {
      // One human decision answers the whole group — recorded on every row it covers,
      // so each stays traceable to its subject.
      for (const finding of group) {
        await insights.resolveFinding(scenarioId, finding.finding_id, ACTIONS[finding.defect])
      }
      await read()
    } catch (error) {
      setProblem(
        error instanceof RequestFailed
          ? error.message
          : 'We could not record that. Nothing was saved.',
      )
    }
  }

  if (findings === null) {
    return (
      <p role="status" className="text-[13px] text-muted">
        Reading the data-quality findings…
      </p>
    )
  }

  const open = findings.filter((finding) => finding.needs_decision && !finding.resolution)
  const handled = findings.filter((finding) => !finding.needs_decision || finding.resolution)

  // One question per DEFECT, not per row: the Delia pack carries ~80 zero-total rows,
  // and eighty identical cards each demanding a click is a wall, not a decision. Each
  // group is one card — the count, one representative sentence, one action that answers
  // the whole group — and the three-row rule then caps the groups, not the rows.
  const groups = new Map<number, Finding[]>()
  for (const finding of open) {
    groups.set(finding.defect, [...(groups.get(finding.defect) ?? []), finding])
  }
  const visible = Array.from(groups.values()).slice(0, 3)

  return (
    <Card data-testid="data-quality-summary">
      <CardHeader>
        <CardTitle>Data quality summary</CardTitle>
        <CardDescription>
          {assetCount !== null ? `${assetCount} assets loaded. ` : ''}5 files matched.{' '}
          {visible.length > 0 ? (
            <span className="font-medium text-high-fg">
              {visible.length === 1
                ? 'One thing needs your eye.'
                : `${visible.length} things need your eye.`}
            </span>
          ) : (
            'Nothing needs a decision.'
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {problem && (
          <p role="alert" className="text-[13px] text-high-fg">
            {problem}
          </p>
        )}

        {visible.map((group) => (
          <div
            key={group[0].defect}
            className="flex items-center justify-between gap-4 rounded-card border border-line p-3"
            data-testid="finding-needs-decision"
          >
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-high-fg" aria-hidden />
              <p className="text-[13px] leading-relaxed">
                {group.length > 1 && (
                  <span className="font-medium">{group.length} findings like this: </span>
                )}
                {group[0].message}{' '}
                <span className="text-muted">({group[0].affected_file})</span>
              </p>
            </div>
            <Button size="sm" className="shrink-0" onClick={() => void resolve(group)}>
              {ACTIONS[group[0].defect] ?? 'Noted'}
            </Button>
          </div>
        ))}

        {handled.length > 0 && (
          <details className="rounded-card border border-line bg-rail">
            <summary className="cursor-pointer px-3 py-2 text-[13px] text-muted hover:text-ink">
              {handled.length} issue(s) handled automatically — see details
            </summary>
            <ul className="space-y-2 border-t border-line p-3">
              {handled.map((finding) => (
                <li key={finding.finding_id} className="flex items-start gap-2.5">
                  <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" aria-hidden />
                  <p className="text-[12px] leading-relaxed text-muted">
                    {finding.message} <span className="text-faint">({finding.affected_file})</span>
                    {finding.resolution && (
                      <span className="text-low-fg"> — {finding.resolution}</span>
                    )}
                  </p>
                </li>
              ))}
            </ul>
          </details>
        )}
      </CardContent>
    </Card>
  )
}
