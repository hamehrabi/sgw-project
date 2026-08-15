'use client'

/**
 * ReasonPanel — the plain-words reasons behind one rank, and the values they rest on.
 *
 * Every sentence here was produced by the same arithmetic that produced the score
 * (ADR-005), so a reader can disagree with a **specific factor** rather than with a number.
 * That is the whole point: the ranking cannot earn trust, but it can be argued with.
 *
 * The values are shown beneath the reasons with their source and age (BR-003), because
 * questioning a rank usually means questioning an input — *that inspection is six years
 * old* — and a reader who cannot see the inputs can only accept or reject the conclusion.
 *
 * Opening this is recorded: success metric 3 counts how often a rank is acted on without it
 * being opened.
 */

import { RiskItem } from '@/lib/api'

export function ReasonPanel({ item }: { item: RiskItem }) {
  if (item.score === null) {
    return (
      <div className="reasons" data-testid="reason-panel">
        <p className="reasons__unscored">
          <strong>Not scored.</strong> {item.unscored_reason}
        </p>
        <p className="reasons__unscored-note">
          This asset has not been ranked and has <strong>not</strong> been judged low risk. It
          needs a person to supply what is missing.
        </p>
      </div>
    )
  }

  return (
    <div className="reasons" data-testid="reason-panel">
      <ul className="reasons__list">
        {item.reasons.map((reason) => (
          <li key={reason.factor}>
            {/* Strength in words as well as weight — colour is never the only signal (Q-013). */}
            <span className={`strength strength--${reason.strength.toLowerCase()}`}>
              {reason.strength}
            </span>{' '}
            {reason.detail}
          </li>
        ))}
      </ul>

      <table className="reasons__values">
        <caption>The values these reasons rest on</caption>
        <tbody>
          {item.values.map((value) => (
            <tr key={value.name}>
              <th scope="row">{value.name.replace(/_/g, ' ')}</th>
              <td>
                {value.value ?? 'not recorded'}
                {value.estimated && <em> (estimated)</em>}
              </td>
              <td className="reasons__provenance">
                {value.source ?? 'source unknown'}
                {value.observed_at && ` · observed ${value.observed_at}`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
