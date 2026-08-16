import * as React from 'react'

import { cn } from '@/lib/utils'
import type { ReasonStrength } from '@/lib/vocabulary'

/** The small shared pieces: alert, progress, strength bar, provenance caption. */

export function Alert({
  className,
  tone = 'info',
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { tone?: 'info' | 'warning' | 'danger' }) {
  return (
    <div
      role={tone === 'danger' ? 'alert' : 'status'}
      className={cn(
        'rounded-card border p-3 text-[13px] leading-relaxed',
        tone === 'info' && 'border-line bg-rail text-ink-secondary',
        tone === 'warning' && 'border-medium-fg/30 bg-medium-bg text-medium-fg',
        tone === 'danger' && 'border-high-fg/30 bg-high-bg text-high-fg',
        className,
      )}
      {...props}
    />
  )
}

export function Progress({
  value,
  max,
  className,
  label,
}: {
  value: number
  max: number
  className?: string
  label?: string
}) {
  const share = max > 0 ? Math.min(value / max, 1) : 0
  return (
    <div
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-label={label}
      className={cn('h-1.5 w-full overflow-hidden rounded-full bg-strength-track', className)}
    >
      {/* Progress is the accent's job — one of the three things teal marks. */}
      <div className="h-full bg-teal" style={{ width: `${share * 100}%` }} />
    </div>
  )
}

/**
 * A reason's weight, drawn in ONE neutral fill at varying length. Deliberately not the
 * severity palette: strength and severity are different scales, and colouring a Strong
 * reason red would teach the reader it means High risk. The word travels with the bar,
 * because the bar alone is decoration and the word alone is the fact.
 */
export function StrengthBar({
  strength,
  className,
}: {
  strength: ReasonStrength
  className?: string
}) {
  const widths: Record<ReasonStrength, string> = {
    Strong: 'w-full',
    Moderate: 'w-1/2',
    Slight: 'w-1/6',
  }
  return (
    <div className={cn('h-1.5 w-full rounded-full bg-strength-track', className)}>
      <div className={cn('h-full rounded-full bg-strength', widths[strength])} />
    </div>
  )
}

/** The grey line under every value: where it came from, and how old it is (BR-003). */
export function Provenance({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-[12px] leading-5 text-muted', className)} {...props} />
}
