'use client'

/**
 * RiskList — every asset ordered by risk. **The screen the product competes on.**
 *
 * Three rules, and each has a specific failure it exists to prevent:
 *
 * - **A rank never renders without its reasons** (BR-002). They arrive in the same response,
 *   so there is no state in which a rank is on screen and its reasons are still loading.
 * - **The empty state reads "no ranking computed" — never "no risk."** A blank list during a
 *   storm is indistinguishable from a grid with nothing wrong with it, and the consequence of
 *   that confusion is a crew not sent.
 * - **An unscored asset is shown, plainly marked, and never sorted as though it were safe.**
 *   It sits at the end of the list under its own heading rather than mixed into the low
 *   scores, because "we could not judge this" and "we judged this low" are different claims.
 *
 * It computes nothing. No score, no rank, no band — FF-002 fails the build if any of ADR-007's
 * constants appear anywhere in this directory.
 */

import { useState } from 'react'

import { Ranking, RiskItem } from '@/lib/api'

import { ReasonPanel } from './ReasonPanel'

function Row({ item }: { item: RiskItem }) {
  const [open, setOpen] = useState(false)
  const unscored = item.score === null

  return (
    <>
      <tr className={unscored ? 'risk--unscored' : undefined}>
        <td className="risk__rank">{item.rank ?? '—'}</td>
        <td>
          {item.name || item.external_ids[0]}
          <div className="row__codes">{item.external_ids.join(' · ')}</div>
          {item.match_status === 'needs_review' && <span className="badge">needs review</span>}
        </td>
        <td>{item.type}</td>
        <td className="risk__score">
          {unscored ? (
            <span className="band band--unscored">Not scored</span>
          ) : (
            <>
              <span className={`band band--${item.band?.toLowerCase()}`}>{item.band}</span>{' '}
              {item.score?.toFixed(1)}
            </>
          )}
        </td>
        <td>
          <button type="button" onClick={() => setOpen(!open)} aria-expanded={open}>
            {open ? 'Hide why' : 'Why?'}
          </button>
        </td>
      </tr>
      {open && (
        <tr>
          <td colSpan={5}>
            <ReasonPanel item={item} />
          </td>
        </tr>
      )}
    </>
  )
}

export function RiskList({
  ranking,
  state,
}: {
  ranking: Ranking | null
  state: 'loading' | 'ready' | 'error'
}) {
  if (state === 'loading') return <p role="status">Working out the ranking…</p>

  if (state === 'error') {
    return (
      <p role="alert">
        We could not load the ranking. The storm is still loaded — try again. This is not a
        statement that nothing is at risk.
      </p>
    )
  }

  if (!ranking || ranking.items.length === 0) {
    return (
      <p role="status" data-testid="ranking-empty">
        <strong>No ranking computed.</strong> This does not mean there is no risk — it means
        nothing has been scored yet.
      </p>
    )
  }

  const scored = ranking.items.filter((item) => item.score !== null)
  const unscored = ranking.items.filter((item) => item.score === null)

  return (
    <section data-testid="risk-list">
      {/* Standing, not a footnote: a confidently wrong ranking is more persuasive than a
          wrong model, not less (ADR-005). */}
      {!ranking.weights_calibrated && (
        <div className="uncalibrated" role="status" data-testid="uncalibrated-notice">
          <strong>These weights have not been calibrated.</strong> The ranking is computed from
          an agreed rule ({ranking.weight_set_version}), not from SGW&rsquo;s own failure
          history — nobody has yet checked it against a real storm. Read the reasons beside each
          rank and disagree with them where they are wrong.
        </div>
      )}

      <table className="assets">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Asset</th>
            <th>Type</th>
            <th>Risk</th>
            <th>Reasons</th>
          </tr>
        </thead>
        <tbody>
          {scored.map((item) => (
            <Row key={item.asset_id} item={item} />
          ))}
        </tbody>

        {unscored.length > 0 && (
          <tbody data-testid="unscored-group">
            <tr>
              <th colSpan={5} className="risk__group">
                {unscored.length} asset(s) could not be scored — shown here rather than left out.
                They have <strong>not</strong> been judged low risk.
              </th>
            </tr>
            {unscored.map((item) => (
              <Row key={item.asset_id} item={item} />
            ))}
          </tbody>
        )}
      </table>
    </section>
  )
}
