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
    <form onSubmit={submit} className="sign-in">
      <label htmlFor="email">Email</label>
      <input
        id="email"
        name="email"
        type="email"
        autoComplete="username"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />

      <label htmlFor="password">Password</label>
      <input
        id="password"
        name="password"
        type="password"
        autoComplete="current-password"
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />

      {refusal && (
        <p role="alert" className="sign-in__refusal">
          {refusal}
        </p>
      )}

      <button type="submit" disabled={submitting}>
        {submitting ? 'Signing in…' : 'Sign in'}
      </button>
    </form>
  )
}
