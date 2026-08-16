import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * shadcn's button, tuned to the brief: primary is slate-900 ink (never the accent — the
 * accent marks navigation and progress, not actions), outline carries the 1px line, and
 * `destructive-outline` is the quiet red of "Dismiss". One primary action per screen is
 * a layout rule the variants make easy and the reviewer checks.
 */
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-card text-[14px] font-medium ' +
    'transition-colors disabled:pointer-events-none disabled:opacity-50 ' +
    'whitespace-nowrap select-none',
  {
    variants: {
      variant: {
        primary: 'bg-ink text-white hover:bg-ink-secondary',
        outline: 'border border-line bg-background text-ink hover:bg-panel',
        ghost: 'text-ink hover:bg-panel',
        link: 'text-teal underline-offset-4 hover:underline p-0 h-auto',
        'destructive-outline':
          'border border-line bg-background text-high-fg hover:bg-high-bg',
      },
      size: {
        default: 'h-9 px-4',
        sm: 'h-8 px-3 text-[13px]',
        lg: 'h-10 px-5',
      },
    },
    defaultVariants: { variant: 'outline', size: 'default' },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, type, ...props }: ButtonProps) {
  return (
    <button
      type={type ?? 'button'}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
}

export { buttonVariants }
