'use client'

import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * A centred modal — the popup shape, where the Sheet is the drawer shape. The same
 * Radix dialog underneath, so focus is trapped, Esc closes, and a screen reader hears
 * it as a dialog without anyone re-implementing any of that.
 */

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogClose = DialogPrimitive.Close

export function DialogContent({
  className,
  children,
  title,
  ...props
}: Omit<React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>, 'title'> & {
  title: React.ReactNode
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-ink/20" />
      <DialogPrimitive.Content
        className={cn(
          'fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[calc(100vw-2rem)] max-w-xl',
          '-translate-x-1/2 -translate-y-1/2 flex-col rounded-card border border-line',
          'bg-background shadow-lg focus:outline-none',
          className,
        )}
        {...props}
      >
        <div className="flex items-center justify-between border-b border-line p-4">
          <DialogPrimitive.Title className="text-[16px] font-semibold">
            {title}
          </DialogPrimitive.Title>
          <DialogPrimitive.Close
            aria-label="Close"
            className="rounded-card p-1 text-muted hover:bg-panel hover:text-ink"
          >
            <X className="h-4 w-4" />
          </DialogPrimitive.Close>
        </div>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}
