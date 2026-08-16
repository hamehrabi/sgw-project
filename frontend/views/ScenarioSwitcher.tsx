'use client'

/**
 * ScenarioSwitcher — choose among the loaded storms (REQ-F-010, US-002).
 *
 * Specified in `frontend-component-spec.md`: *"Data needed: loaded scenarios: name, source note,
 * loaded date. States: loading, success, empty, error. The empty state reads 'no storm loaded
 * yet' and points an admin at the upload panel. It must never render as a scenario with no
 * risk."* `AppShell` keeps it present always, "because everything below it is scoped to one
 * scenario" — it lives in the sidebar's scenario block now, which is the same frame.
 *
 * **Three rules this component is written around.**
 *
 * *Empty and error are different facts and never share words.* *No storm is loaded* means an
 * admin should go and load one. *We could not find out which storms are loaded* means nothing
 * of the kind, and borrowing the first sentence for the second would send somebody to load a
 * storm that is already there.
 *
 * *Nothing is chosen for the reader.* A storm is selected when somebody selects it, or when
 * they have just loaded one. An automatic choice puts a ranking on screen that nobody asked
 * for — this product recommends; people decide.
 *
 * *It shows what is there, and says what is not.* A storm whose current revision has no
 * ranking behind it is labelled as such (CHG-027's argument, one component over).
 */

import { ChevronsUpDown } from 'lucide-react'
import { useState } from 'react'

import { cn } from '@/lib/utils'
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
        className={cn(
          'w-full rounded-card border border-transparent px-2.5 py-2 text-left hover:bg-panel',
          selected && 'border-teal bg-teal-soft',
        )}
        aria-current={selected || undefined}
        data-testid="scenario-option"
        onClick={() => onSelect(storm.scenario_id)}
      >
        <span className="block text-[13px] font-medium leading-5">{storm.name}</span>
        <span className="block text-[12px] text-muted">{storm.source_note}</span>
        <span className="block text-[11px] leading-4 text-faint">
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
  role: 'admin' | 'operator'
  onSelect: (id: string) => void
  onRetry: () => void
}) {
  // Controlled so that choosing a storm closes the list — a disclosure left open over
  // the storm it just switched to is a panel covering the thing the reader opened it
  // to see.
  const [open, setOpen] = useState(false)

  if (state === 'loading') {
    return (
      <span className="block text-[12px] text-muted" data-testid="scenario-switcher">
        <span role="status">Reading the loaded storms…</span>
      </span>
    )
  }

  if (state === 'error') {
    return (
      <span className="block text-[12px]" data-testid="scenario-switcher">
        <span role="alert" className="text-high-fg">
          We could not read which storms are loaded.
        </span>{' '}
        <button
          type="button"
          onClick={onRetry}
          className="font-medium text-teal underline-offset-2 hover:underline"
        >
          Retry
        </button>
      </span>
    )
  }

  if (storms.length === 0) {
    return (
      <span className="block text-[12px] text-muted" data-testid="scenario-switcher">
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
      className="group"
      data-testid="scenario-switcher"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary
        data-testid="scenario-switcher-toggle"
        className={cn(
          'flex cursor-pointer list-none items-center justify-between gap-2 rounded-card',
          'border border-line bg-background px-2.5 py-1.5 text-[12px] hover:bg-panel',
          '[&::-webkit-details-marker]:hidden',
        )}
      >
        <span>
          <span className="mr-1.5 font-medium text-muted">Storms</span>
          <span data-testid="scenario-current">
            {current ? current.name : `${storms.length} loaded · none chosen`}
          </span>
        </span>
        <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-faint" aria-hidden />
      </summary>
      <ul className="mt-1.5 space-y-0.5 rounded-card border border-line bg-background p-1">
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
