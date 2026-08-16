'use client'

/**
 * Sign in with an email and a password (ADR-003).
 *
 * There is no "create an account" link, no "forgot password" link, and no second factor.
 * Each is absent by decision rather than by omission: accounts are created on the host
 * (`security-specification.md` §7), a reset is performed by an admin (CHG-004, A-003), and
 * a second factor is P1 rather than version one (SEC-A-006, Q-022).
 *
 * The refusal shown here is whatever the server said, verbatim. Elaborating on it in the
 * browser is how "the email or password is incorrect" becomes an account oracle.
 */

import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input, Label } from '@/components/ui/field'
import { auth, Identity, RequestFailed } from '@/lib/api'

export function SignInForm({ onSignedIn }: { onSignedIn: (identity: Identity) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [refusal, setRefusal] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setRefusal(null)
    try {
      onSignedIn(await auth.signIn(email, password))
    } catch (error) {
      setRefusal(
        error instanceof RequestFailed
          ? error.message
          : 'We could not reach the server. Please try again.',
      )
      // The typed email survives a refusal; the password never does.
      setPassword('')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardContent className="pt-5">
        <form onSubmit={submit} data-testid="sign-in-form" className="space-y-4">
          <p className="text-[13px] leading-relaxed text-muted">
            Sign in to load a storm, read the ranking, and record what you decide.
          </p>

          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          {refusal && (
            <p role="alert" className="text-[13px] text-high-fg">
              {refusal}
            </p>
          )}

          <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>

          {/* Said out loud rather than left as three absent links a person hunts for. Each
              is absent by a recorded decision: accounts are created on the host
              (`security-specification.md` §7), a reset is admin-performed (CHG-004), and a
              second factor is P1 rather than version one (SEC-A-006). */}
          <p className="border-t border-line pt-3 text-[12px] leading-relaxed text-muted">
            Accounts are created by an administrator — there is no sign-up, and no
            self-service password reset. If you cannot get in, ask an administrator to set
            a temporary password.
          </p>
        </form>
      </CardContent>
    </Card>
  )
}
