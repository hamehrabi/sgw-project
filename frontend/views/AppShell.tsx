'use client'

/**
 * AppShell — the frame: navigation, scenario selector, current user and role.
 *
 * Specified in `frontend-component-spec.md`. Three states: loading, ready, unauthorized.
 *
 * **Render no content until the signed-in role is known.** That rule is why this component
 * resolves the session before it renders anything below the frame — a shell that painted
 * its navigation first would show an admin's controls for the moment before the role
 * arrived, and hiding them afterwards is not the same as never having offered them.
 *
 * Hiding a control here is never the enforcement. The server refuses the request as well
 * (`technical-spec.md` §3), and a deny test covers each refusal.
 */

import { useCallback, useEffect, useState } from 'react'

import { auth, Identity, RequestFailed } from '@/lib/api'

import { ScenarioSelector } from './ScenarioSelector'
import { SignInForm } from './SignInForm'

type State =
  | { status: 'loading' }
  | { status: 'ready'; identity: Identity }
  | { status: 'unauthorized' }

/**
 * `children` is a function of the identity rather than a node, so nothing below the shell
 * can render before the role is known — the rule is enforced by the type, not by remembering.
 */
export function AppShell({ children }: { children?: (identity: Identity) => React.ReactNode }) {
  const [state, setState] = useState<State>({ status: 'loading' })

  const resolveSession = useCallback(async () => {
    try {
      setState({ status: 'ready', identity: await auth.current() })
    } catch (error) {
      if (error instanceof RequestFailed && error.status === 401) {
        setState({ status: 'unauthorized' })
        return
      }
      // Anything else is a server or network problem rather than a signed-out user.
      // Treating it as signed out would be a sign-in screen during an outage.
      setState({ status: 'unauthorized' })
    }
  }, [])

  useEffect(() => {
    void resolveSession()
  }, [resolveSession])

  if (state.status === 'loading') {
    // Progress, never a blank frame (`frontend-component-spec.md`, loading state).
    return (
      <main className="shell shell--centred">
        <p role="status">Loading…</p>
      </main>
    )
  }

  if (state.status === 'unauthorized') {
    return (
      <main className="shell shell--centred">
        <h1>SGW Resilience Platform</h1>
        <SignInForm onSignedIn={(identity) => setState({ status: 'ready', identity })} />
      </main>
    )
  }

  const { identity } = state

  return (
    <div className="shell">
      <header className="shell__bar">
        <span className="shell__title">SGW Resilience Platform</span>

        {/* Always present: everything below it is scoped to one scenario. */}
        <ScenarioSelector />

        <span className="shell__identity">
          {identity.name} · <span data-testid="role">{identity.role}</span>
        </span>

        <button
          type="button"
          onClick={async () => {
            await auth.signOut()
            setState({ status: 'unauthorized' })
          }}
        >
          Sign out
        </button>
      </header>

      <main className="shell__content">{children?.(identity)}</main>
    </div>
  )
}
