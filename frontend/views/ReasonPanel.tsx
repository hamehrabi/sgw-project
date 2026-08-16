'use client'

/**
 * ReasonPanel — the plain-words reasons behind one rank, and the values they rest on.
 *
 * Every sentence here was produced by the same arithmetic that produced the score
 * (ADR-005), so a reader can disagree with a **specific factor** rather than with a
 * number. That is the whole point: the ranking cannot earn trust, but it can be argued
 * with.
 *
 * The strength bars use one neutral fill at varying length — deliberately not the
 * severity palette, because strength and severity are different scales — and the word
 * travels with the bar, because colour is never the only signal (Q-013).
 *
 * The values are beneath the reasons with their source and age (BR-003): questioning a
 * rank usually means questioning an input — *that inspection is six years old* — and a
 * reader who cannot see the inputs can only accept or reject the conclusion.
 */

import { StrengthBar } from '@/components/ui/bits'
import { RiskItem } from '@/lib/api'

export function ReasonPanel({ item }: { item: RiskItem }) {
  if (item.score === null) {
    return (
      <div data-testid="reason-panel" className="space-y-1.5 text-[13px]">
        <p>
          <strong>Not scored.</strong> {item.unscored_reason}
        </p>
        <p className="text-muted">
          This asset has not been ranked and has <strong>not</strong> been judged low risk. It
          needs a person to supply what is missing.
        </p>
      </div>
    )
  }

  return (
    <div data-testid="reason-panel" className="space-y-4">
      <ul className="space-y-3">
        {item.reasons.map((reason) => (
          <li key={reason.factor} className="text-[13px] leading-relaxed">
            <div className="mb-1 flex items-center justify-between gap-4">
              <span>{reason.detail}</span>
              {/* Strength in words as well as weight — never a percentage (Q-013). */}
              <span className="shrink-0 text-[12px] font-medium text-muted">
                {reason.strength}
              </span>
            </div>
            <StrengthBar strength={reason.strength} className="max-w-xs" />
          </li>
        ))}
      </ul>

      <table className="w-full text-[12px]">
        <caption className="pb-1.5 text-left font-medium text-ink-secondary">
          The values these reasons rest on
        </caption>
        <tbody>
          {item.values.map((value) => (
            <tr key={value.name} className="border-t border-line">
              <th scope="row" className="py-1.5 pr-3 text-left font-normal capitalize text-muted">
                {value.name.replace(/_/g, ' ')}
              </th>
              <td className="py-1.5 pr-3">
                {value.value ?? 'not recorded'}
                {value.estimated && <em className="text-muted"> (estimated)</em>}
              </td>
              <td className="py-1.5 text-muted">
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
