'use client'

/**
 * PasswordChangeForm — the one screen a temporary password can reach (CHG-053).
 *
 * The shell shows this and nothing else while `must_change_password` is set; the server
 * refuses every other route regardless, so this screen is the door and the guard is the
 * lock. The current password is asked for even here: a session cookie left on a shared
 * machine must not be enough to change the credential behind it.
 */

import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Label } from '@/components/ui/field'
import { auth, RequestFailed } from '@/lib/api'

export function PasswordChangeForm({ onChanged }: { onChanged: () => void }) {
  const [current, setCurrent] = useState('')
  const [replacement, setReplacement] = useState('')
  const [refusal, setRefusal] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setSaving(true)
    setRefusal(null)
    try {
      await auth.changePassword(current, replacement)
      onChanged()
    } catch (error) {
      setRefusal(
        error instanceof RequestFailed
          ? error.message
          : 'We could not reach the server. Please try again.',
      )
      setReplacement('')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Set a new password</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} data-testid="password-change-form" className="space-y-4">
          <p className="text-[13px] leading-relaxed text-muted">
            Your password is a temporary one set by an administrator. Choose your own
            before doing anything else — nothing answers until you have.
          </p>

          <div>
            <Label htmlFor="current-password">Temporary password</Label>
            <Input
              id="current-password"
              type="password"
              autoComplete="current-password"
              required
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
            />
          </div>

          <div>
            <Label htmlFor="new-password">New password</Label>
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              value={replacement}
              onChange={(event) => setReplacement(event.target.value)}
            />
            <p className="mt-1 text-[12px] text-muted">At least 12 characters.</p>
          </div>

          {refusal && (
            <p role="alert" className="text-[13px] text-high-fg">
              {refusal}
            </p>
          )}

          <Button type="submit" variant="primary" className="w-full" disabled={saving}>
            {saving ? 'Saving…' : 'Save new password'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
