'use client'

/**
 * ScenarioSwitcher — choose among the loaded storms (REQ-F-010, US-002).
 *
 * Specified in `frontend-component-spec.md`: *"Data needed: loaded scenarios: name, source note,
 * loaded date. States: loading, success, empty, error. The empty state reads 'no storm loaded
 * yet' and points an admin at the upload panel. It must never render as a scenario with no
 * risk."* `AppShell` keeps it present always, "because everything below it is scoped to one
 * scenario".
 *
 * Until TASK-009 only the empty state existed, and it was the only one reachable: nothing
 * listed the loaded storms. The endpoint that does is CHG-030, and it is why the other three
 * arrive now rather than earlier.
 *
 * **Three rules this component is written around.**
 *
 * *Empty and error are different facts and never share words.* *No storm is loaded* means an
 * admin should go and load one. *We could not find out which storms are loaded* means nothing
 * of the kind, and borrowing the first sentence for the second would send somebody to load a
 * storm that is already there — during a storm, on the screen that is supposed to say what is
 * happening.
 *
 * *Nothing is chosen for the reader.* A storm is selected when somebody selects it, or when
 * they have just loaded one. The alternative — quietly selecting the newest — was declined:
 * every panel below is scoped to whatever is selected, so an automatic choice puts a ranking
 * on screen that nobody asked for, and this product's whole posture is that it recommends and
 * people decide. It also has a concrete cost: a failed upload would leave the previous storm's
 * ranking on screen underneath the refusal.
 *
 * *It shows what is there, and says what is not.* A storm whose current revision has no
 * ranking behind it is labelled as such, because the switcher must never render as a scenario
 * with no risk (CHG-027's argument, one component over).
 */

import { useState } from 'react'

import { LoadedScenario } from '@/lib/api'

export type SwitcherState = 'loading' | 'ready' | 'error'

function ago(loadedAt: string): string {
  const at = new Date(loadedAt)
  return Number.isNaN(at.getTime()) ? loadedAt : at.toISOString().replace('T', ' ').slice(0, 16)
}

function Option({
  storm,
  selected,
  onSelect,
}: {
  storm: LoadedScenario
  selected: boolean
  onSelect: (id: string) => void
}) {
  return (
    <li>
      <button
        type="button"
        className={selected ? 'switcher__option switcher__option--on' : 'switcher__option'}
        aria-current={selected || undefined}
        data-testid="scenario-option"
        onClick={() => onSelect(storm.scenario_id)}
      >
        <span className="switcher__name">{storm.name}</span>
        <span className="switcher__note">{storm.source_note}</span>
        <span className="switcher__meta">
          loaded {ago(storm.loaded_at)} · {storm.asset_count} asset(s) ·{' '}
          {/* Never silently: a storm nobody has ranked is not a quiet one. */}
          {storm.ranked ? `ranked at revision ${storm.forecast_revision}` : 'not ranked yet'}
          {/* AC-010: the age is stated always, not only when it is bad. */}
          {storm.data_age_hours !== null &&
            ` · data ${storm.data_age_hours}h old${storm.stale ? ' (stale)' : ''}`}
        </span>
      </button>
    </li>
  )
}

export function ScenarioSwitcher({
  storms,
  state,
  selected,
  role,
  onSelect,
  onRetry,
}: {
  storms: LoadedScenario[]
  state: SwitcherState
  selected: string | null
  role: 'admin' | 'user'
  onSelect: (id: string) => void
  onRetry: () => void
}) {
  // The list is controlled rather than left to the browser so that choosing a storm closes it.
  // A disclosure that stays open over the storm it just switched to is a panel covering the
  // thing the reader opened it to see.
  const [open, setOpen] = useState(false)

  if (state === 'loading') {
    // Progress, never a blank frame — and never the empty state's words, which would read as
    // "no storm is loaded" for as long as the read takes.
    return (
      <span className="switcher" data-testid="scenario-switcher">
        <span role="status">Reading the loaded storms…</span>
      </span>
    )
  }

  if (state === 'error') {
    return (
      <span className="switcher switcher--error" data-testid="scenario-switcher">
        <span role="alert">We could not read which storms are loaded.</span>{' '}
        <button type="button" onClick={onRetry}>
          Retry
        </button>
      </span>
    )
  }

  if (storms.length === 0) {
    return (
      <span className="switcher" data-testid="scenario-switcher">
        <span role="status" data-testid="scenario-switcher-empty">
          No storm loaded yet.
          {/* Pointed at the panel only if they can use it: telling a dispatcher to load a
              storm is telling them to do something the server will refuse (REQ-R-001). */}
          {role === 'admin' ? ' Load a prepared storm to begin.' : ' An admin loads one.'}
        </span>
      </span>
    )
  }

  const current = storms.find((storm) => storm.scenario_id === selected)

  return (
    <details
      className="switcher"
      data-testid="scenario-switcher"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary data-testid="scenario-switcher-toggle">
        <span className="switcher__label">Storms</span>{' '}
        <span className="switcher__current" data-testid="scenario-current">
          {current ? current.name : `${storms.length} loaded · none chosen`}
        </span>
      </summary>
      <ul className="switcher__list">
        {storms.map((storm) => (
          <Option
            key={storm.scenario_id}
            storm={storm}
            selected={storm.scenario_id === selected}
            onSelect={(id) => {
              setOpen(false)
              onSelect(id)
            }}
          />
        ))}
      </ul>
    </details>
  )
}
