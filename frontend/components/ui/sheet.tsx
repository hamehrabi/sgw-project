'use client'

import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * The right-hand drawer both review flows use (match review, asset detail, summary
 * review) — Radix dialog underneath, so focus is trapped, Esc closes, and a screen
 * reader hears it as a dialog without anyone re-implementing any of that.
 */

export const Sheet = DialogPrimitive.Root
export const SheetTrigger = DialogPrimitive.Trigger
export const SheetClose = DialogPrimitive.Close

export function SheetContent({
  className,
  children,
  title,
  onFinishLater,
  ...props
}: Omit<React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>, 'title'> & {
  title: React.ReactNode
  onFinishLater?: () => void
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-ink/20" />
      <DialogPrimitive.Content
        className={cn(
          'fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-line',
          'bg-background focus:outline-none sm:max-w-lg',
          className,
        )}
        {...props}
      >
        <div className="flex items-center justify-between border-b border-line p-4">
          <DialogPrimitive.Title className="text-[17px] font-semibold">
            {title}
          </DialogPrimitive.Title>
          <div className="flex items-center gap-3">
            {onFinishLater && (
              <DialogPrimitive.Close
                className="text-[13px] text-muted hover:text-ink"
                onClick={onFinishLater}
              >
                Finish later
              </DialogPrimitive.Close>
            )}
            <DialogPrimitive.Close
              aria-label="Close"
              className="rounded-card p-1 text-muted hover:bg-panel hover:text-ink"
            >
              <X className="h-4 w-4" />
            </DialogPrimitive.Close>
          </div>
        </div>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}
