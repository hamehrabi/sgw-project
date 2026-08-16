import * as React from 'react'

import { cn } from '@/lib/utils'

/** Input, Textarea and Label share one border-and-focus language. */

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn('mb-1.5 block text-[13px] font-medium text-ink-secondary', className)}
      {...props}
    />
  )
}

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'h-9 w-full rounded-card border border-line bg-background px-3 text-[14px]',
        'placeholder:text-faint focus-visible:border-teal',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
}

export function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        'w-full rounded-card border border-line bg-background p-3 text-[14px]',
        'placeholder:text-faint focus-visible:border-teal',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
}
