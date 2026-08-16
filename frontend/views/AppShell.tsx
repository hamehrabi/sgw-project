'use client'

/**
 * AppShell — the frame: sidebar, top bar, current user and role.
 *
 * Specified in `frontend-component-spec.md`, reshaped to the eight-screen design: a left
 * sidebar carrying the scenario context and exactly two navigation items — Storm
 * Planning and Dispatch Board — and a top bar stating the platform's posture in one
 * line: how many prepared files stand behind the screen, that no live system is
 * connected, and when the forecast was issued. No bell, no gear, no avatar.
 *
 * **Render no content until the signed-in role is known.** The shell resolves the
 * session before painting anything below the frame — a shell that painted its
 * navigation first would show an admin's controls for the moment before the role
 * arrived, and hiding them afterwards is not the same as never having offered them.
 *
 * **The chosen storm is held here, beside the identity, and for the same reason.** The
 * spec puts the selector in this frame *"because everything below it is scoped to one
 * scenario"* — so the scope lives where the frame does, or two components own one fact
 * and are free to disagree about which storm the screen is showing (REQ-F-010).
 *
 * Hiding a control here is never the enforcement. The server refuses the request as
 * well (`technical-spec.md` §3), and a deny test covers each refusal.
 */

import { LayoutGrid, Tornado, Upload } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { cn } from '@/lib/utils'
import { auth, Identity, LoadedScenario, RequestFailed, scenarios } from '@/lib/api'

import { PasswordChangeForm } from './PasswordChangeForm'
import { ScenarioSwitcher, SwitcherState } from './ScenarioSwitcher'
import { SignInForm } from './SignInForm'

type State =
  | { status: 'loading' }
  | { status: 'ready'; identity: Identity }
  | { status: 'unauthorized' }

/** The three surfaces below the frame. Load is a surface, not a nav item — the design
 *  carries exactly two nav items, and loading is how a storm ARRIVES, not a place work
 *  happens. */
export type Surface = 'load' | 'planning' | 'dispatch'

export interface StormChoice {
  scenarioId: string | null
  storms: LoadedScenario[]
  onLoaded: (scenarioId: string) => void
}

export interface ShellControls {
  surface: Surface
  setSurface: (surface: Surface) => void
}

function clock(issuedAt: string | null | undefined): string | null {
  if (!issuedAt) return null
  const at = new Date(issuedAt)
  return Number.isNaN(at.getTime()) ? null : at.toISOString().slice(11, 16)
}

export function AppShell({
  children,
}: {
  children?: (identity: Identity, storm: StormChoice, shell: ShellControls) => React.ReactNode
}) {
  const [state, setState] = useState<State>({ status: 'loading' })
  const [storms, setStorms] = useState<LoadedScenario[]>([])
  const [switcher, setSwitcher] = useState<SwitcherState>('loading')
  const [selected, setSelected] = useState<string | null>(null)
  const [surface, setSurface] = useState<Surface>('load')
  // Shown after a click on a locked dashboard tab — the click gets an answer, not silence.
  const [lockedHint, setLockedHint] = useState(false)

  const resolveSession = useCallback(async () => {
    try {
      setState({ status: 'ready', identity: await auth.current() })
    } catch (error) {
      if (error instanceof RequestFailed && error.status === 401) {
        setState({ status: 'unauthorized' })
        return
      }
      setState({ status: 'unauthorized' })
    }
  }, [])

  const readStorms = useCallback(async () => {
    setSwitcher('loading')
    try {
      setStorms((await scenarios.list()).items)
      setSwitcher('ready')
    } catch {
      // The list is unknown — NOT the same fact as "no storm is loaded". The last known
      // list is left alone: a read that failed has not unloaded anything.
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
      // The storm is selected but the person STAYS on the Load surface: the data
      // quality summary is mandatory reading, and "Finish and continue" is the door
      // to the dashboards — never a silent redirect past the findings.
      setSelected(scenarioId)
      void readStorms()
    },
    [readStorms],
  )

  const choose = useCallback((scenarioId: string) => {
    // A storm picked from the switcher was processed when it was loaded; its quality
    // summary stays one click away behind "Load storm data".
    setSelected(scenarioId)
    setSurface((current) => (current === 'load' ? 'planning' : current))
  }, [])

  if (state.status === 'loading') {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p role="status" className="text-muted">
          Loading…
        </p>
      </main>
    )
  }

  if (state.status === 'unauthorized') {
    return (
      <main className="flex min-h-screen items-center justify-center bg-rail p-6">
        <div className="w-full max-w-sm">
          <h1 className="mb-6 text-center text-[22px] font-semibold tracking-tight">
            SGW Resilience Platform
          </h1>
          <SignInForm onSignedIn={(identity) => setState({ status: 'ready', identity })} />
        </div>
      </main>
    )
  }

  const { identity } = state

  // CHG-053: a temporary password buys the change screen and nothing else. The server
  // refuses every other route regardless — this is the door, not the lock.
  if (identity.must_change_password) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-rail p-6">
        <div className="w-full max-w-sm">
          <h1 className="mb-6 text-center text-[22px] font-semibold tracking-tight">
            SGW Resilience Platform
          </h1>
          <PasswordChangeForm
            onChanged={() =>
              setState({
                status: 'ready',
                identity: { ...identity, must_change_password: false },
              })
            }
          />
        </div>
      </main>
    )
  }

  const current = storms.find((storm) => storm.scenario_id === selected)
  const forecastAt = clock(current?.forecast_issued_at)

  const navigation: { surface: Surface; label: string; icon: typeof Tornado }[] = [
    { surface: 'planning', label: 'Storm Planning', icon: Tornado },
    { surface: 'dispatch', label: 'Dispatch Board', icon: LayoutGrid },
  ]

  return (
    <div className="flex min-h-screen">
      {/* ---- Sidebar: scenario context and exactly two navigation items ---- */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-line bg-rail">
        <div className="border-b border-line p-4">
          {current ? (
            <>
              <p className="text-[17px] font-semibold leading-snug">
                Scenario: {current.name}
              </p>
              <p className="mt-0.5 text-[12px] text-muted">{current.source_note}</p>
            </>
          ) : (
            <p className="text-[15px] font-semibold text-muted">No scenario chosen</p>
          )}
          <div className="mt-3">
            <ScenarioSwitcher
              storms={storms}
              state={switcher}
              selected={selected}
              role={identity.role}
              onSelect={choose}
              onRetry={() => void readStorms()}
            />
          </div>
        </div>

        <nav className="flex flex-col gap-1 p-3">
          {/* Loading is the onboarding, so its entry leads the list. */}
          {identity.role === 'admin' && (
            <button
              type="button"
              onClick={() => setSurface('load')}
              aria-current={surface === 'load' || undefined}
              className={cn(
                'flex items-center gap-2.5 rounded-card border-l-2 border-transparent px-3 py-2',
                'text-left text-[14px] font-medium text-ink-secondary hover:bg-panel',
                surface === 'load' && 'border-teal bg-teal-soft text-teal-deep',
              )}
            >
              <Upload className="h-4 w-4" aria-hidden />
              Load storm data
            </button>
          )}

          {/* Both dashboards stay visible so the shape of the product is legible from the
              first minute — greyed until a storm is loaded, processed and chosen, and a
              click on a locked one SAYS why instead of doing nothing. A nav item pointing
              at an empty ranking would be the empty screen that reads as safety. */}
          {navigation.map(({ surface: item, label, icon: Icon }) => (
            <button
              key={item}
              type="button"
              aria-disabled={!selected || undefined}
              onClick={() => {
                if (selected) {
                  setLockedHint(false)
                  setSurface(item)
                } else {
                  setLockedHint(true)
                }
              }}
              aria-current={surface === item || undefined}
              className={cn(
                'flex items-center gap-2.5 rounded-card border-l-2 border-transparent px-3 py-2',
                'text-left text-[14px] font-medium',
                selected
                  ? 'text-ink-secondary hover:bg-panel'
                  : 'cursor-not-allowed text-faint',
                selected && surface === item && 'border-teal bg-teal-soft text-teal-deep',
              )}
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </button>
          ))}

          {lockedHint && !selected && (
            <p role="status" className="px-3 py-1.5 text-[12px] leading-relaxed text-muted">
              Load and process a storm to open Storm Planning and the Dispatch Board.
            </p>
          )}
        </nav>
      </aside>

      {/* ---- Top bar and content ---- */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-background px-5">
          <span className="text-[15px] font-semibold tracking-tight">
            SGW Resilience Platform
          </span>
          <div className="flex items-center gap-5 text-[13px]">
            <span className="text-muted">
              {/* The posture line: what stands behind this screen, and what does not. */}
              {current ? '5 files loaded' : 'no storm loaded'} · no live system connections
            </span>
            {forecastAt && (
              <span className="font-medium">Forecast issued {forecastAt}</span>
            )}
            <span className="text-muted">
              {identity.name} · <span data-testid="role">{identity.role}</span>
            </span>
            <button
              type="button"
              className="text-muted underline-offset-4 hover:text-ink hover:underline"
              onClick={async () => {
                await auth.signOut()
                setSelected(null)
                setState({ status: 'unauthorized' })
              }}
            >
              Sign out
            </button>
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-x-hidden p-6">
          {children?.(
            identity,
            { scenarioId: selected, storms, onLoaded },
            { surface, setSurface },
          )}
        </main>
      </div>
    </div>
  )
}
