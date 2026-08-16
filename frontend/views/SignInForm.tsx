'use client'

/**
 * Sign in with an email and a password (ADR-003), or create an operator account
 * (CHG-061).
 *
 * Sign-up creates **operators only** — the server decides the role and the request has
 * no field for one. No "forgot password" link and no second factor, each absent by
 * decision rather than by omission: a reset is performed by an admin (CHG-004, A-003),
 * and a second factor is P1 rather than version one (SEC-A-006, Q-022).
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
  const [mode, setMode] = useState<'sign-in' | 'sign-up'>('sign-in')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [refusal, setRefusal] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setRefusal(null)
    try {
      onSignedIn(
        mode === 'sign-in'
          ? await auth.signIn(email, password)
          : await auth.signUp(name, email, password),
      )
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

  function switchMode(next: 'sign-in' | 'sign-up') {
    setMode(next)
    setRefusal(null)
    setPassword('')
  }

  return (
    <Card>
      <CardContent className="pt-5">
        <form onSubmit={submit} data-testid="sign-in-form" className="space-y-4">
          <p className="text-[13px] leading-relaxed text-muted">
            {mode === 'sign-in'
              ? 'Sign in to load a storm, read the ranking, and record what you decide.'
              : 'Create an operator account. Operators read rankings and record ' +
                'decisions; loading a storm needs an administrator.'}
          </p>

          {mode === 'sign-up' && (
            <div>
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                name="name"
                autoComplete="name"
                required
                maxLength={120}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
          )}

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
              autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {mode === 'sign-up' && (
              <p className="mt-1 text-[12px] text-muted">At least 12 characters.</p>
            )}
          </div>

          {refusal && (
            <p role="alert" className="text-[13px] text-high-fg">
              {refusal}
            </p>
          )}

          <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
            {submitting
              ? mode === 'sign-in'
                ? 'Signing in…'
                : 'Creating the account…'
              : mode === 'sign-in'
                ? 'Sign in'
                : 'Create account'}
          </Button>

          <p className="border-t border-line pt-3 text-[12px] leading-relaxed text-muted">
            {mode === 'sign-in' ? (
              <>
                No account yet?{' '}
                <button
                  type="button"
                  data-testid="switch-to-sign-up"
                  className="font-medium text-teal-deep hover:underline"
                  onClick={() => switchMode('sign-up')}
                >
                  Create one
                </button>{' '}
                — it signs you in as an operator. Administrator accounts and password
                resets are still an administrator&rsquo;s to make.
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button
                  type="button"
                  data-testid="switch-to-sign-in"
                  className="font-medium text-teal-deep hover:underline"
                  onClick={() => switchMode('sign-in')}
                >
                  Sign in
                </button>
                . There is no self-service password reset — an administrator sets a
                temporary one.
              </>
            )}
          </p>
        </form>
      </CardContent>
    </Card>
  )
}
