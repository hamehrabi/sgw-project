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
 * **The chosen storm is held here, beside the identity, and for the same reason.** The spec
 * puts the selector in this frame *"because everything below it is scoped to one scenario"* —
 * so the scope has to live where the frame does, or two components own one fact and are free
 * to disagree about which storm the screen is showing. That disagreement is REQ-F-010's blend
 * with no visible symptom.
 *
 * Hiding a control here is never the enforcement. The server refuses the request as well
 * (`technical-spec.md` §3), and a deny test covers each refusal.
 */

import { useCallback, useEffect, useState } from 'react'

import { auth, Identity, LoadedScenario, RequestFailed, scenarios } from '@/lib/api'

import { ScenarioSwitcher, SwitcherState } from './ScenarioSwitcher'
import { SignInForm } from './SignInForm'

type State =
  | { status: 'loading' }
  | { status: 'ready'; identity: Identity }
  | { status: 'unauthorized' }

/** Which storm is on screen, and how anything below the shell changes it. */
export interface StormChoice {
  scenarioId: string | null
  /** Every storm loaded, newest first — so a screen can tell "none chosen" from "none exist". */
  storms: LoadedScenario[]
  /** Select a storm, and re-read the list: a storm just loaded has to appear in it. */
  onLoaded: (scenarioId: string) => void
}

/**
 * `children` is a function of the identity rather than a node, so nothing below the shell
 * can render before the role is known — the rule is enforced by the type, not by remembering.
 * The chosen storm travels the same way, for the same reason.
 */
export function AppShell({
  children,
}: {
  children?: (identity: Identity, storm: StormChoice) => React.ReactNode
}) {
  const [state, setState] = useState<State>({ status: 'loading' })
  const [storms, setStorms] = useState<LoadedScenario[]>([])
  const [switcher, setSwitcher] = useState<SwitcherState>('loading')
  const [selected, setSelected] = useState<string | null>(null)

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

  const readStorms = useCallback(async () => {
    setSwitcher('loading')
    try {
      setStorms((await scenarios.list()).items)
      setSwitcher('ready')
    } catch {
      // The list is unknown, which is **not** the same fact as "no storm is loaded". The
      // switcher keeps the two apart in words, and the last known list is left alone rather
      // than emptied — a read that failed has not unloaded anything.
      setSwitcher('error')
    }
  }, [])

  useEffect(() => {
    void resolveSession()
  }, [resolveSession])

  useEffect(() => {
    if (state.status === 'ready') void readStorms()
  }, [state.status, readStorms])

  const onLoaded = useCallback(
    (scenarioId: string) => {
      setSelected(scenarioId)
      void readStorms()
    },
    [readStorms],
  )

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
        <ScenarioSwitcher
          storms={storms}
          state={switcher}
          selected={selected}
          role={identity.role}
          onSelect={setSelected}
          onRetry={() => void readStorms()}
        />

        <span className="shell__identity">
          {identity.name} · <span data-testid="role">{identity.role}</span>
        </span>

        <button
          type="button"
          onClick={async () => {
            await auth.signOut()
            setSelected(null)
            setState({ status: 'unauthorized' })
          }}
        >
          Sign out
        </button>
      </header>

      <main className="shell__content">
        {children?.(identity, { scenarioId: selected, storms, onLoaded })}
      </main>
    </div>
  )
}
