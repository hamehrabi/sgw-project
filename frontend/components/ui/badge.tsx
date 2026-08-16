import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'

import { cn } from '@/lib/utils'
import type { RiskBand } from '@/lib/vocabulary'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-[12px] font-medium leading-5',
  {
    variants: {
      variant: {
        neutral: 'bg-panel text-ink-secondary',
        outline: 'border border-line text-muted bg-background',
        teal: 'bg-teal-soft text-teal-deep',
        high: 'bg-high-bg text-high-fg',
        medium: 'bg-medium-bg text-medium-fg',
        low: 'bg-low-bg text-low-fg',
        draft: 'bg-medium-bg text-medium-fg',
      },
    },
    defaultVariants: { variant: 'neutral' },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

/**
 * The one legal way to render a band: the frozen word, in its tint. Takes the type, so
 * "HIGH", "Critical" and a score have no way in — the mockup's `HIGH` badges are a
 * recorded deviation (CHG register), and this component is where the correction lives.
 */
export function BandBadge({ band, className }: { band: RiskBand; className?: string }) {
  const variant = band.toLowerCase() as 'high' | 'medium' | 'low'
  return (
    <Badge variant={variant} className={cn('band', className)}>
      {band}
    </Badge>
  )
}
