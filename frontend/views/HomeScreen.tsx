'use client'

/**
 * The composition root, on the client side of the boundary.
 *
 * `AppShell` takes its children as a *function of the identity, the chosen storm and the
 * shell's surface*, so nothing below the shell can render before the role is known and
 * nothing can render a storm the frame has not selected — the rules are held by the type
 * rather than by remembering them. A function cannot cross from a Server Component to a
 * Client Component, so the call lives here and `app/page.tsx` stays a server component.
 */

import { AppShell } from './AppShell'
import { ScenarioView } from './ScenarioView'

export function HomeScreen() {
  return (
    <AppShell>
      {(identity, storm, shell) => (
        <ScenarioView
          role={identity.role}
          scenarioId={storm.scenarioId}
          loadedCount={storm.storms.length}
          onLoaded={storm.onLoaded}
          surface={shell.surface}
          justLoaded={shell.justLoaded}
        />
      )}
    </AppShell>
  )
}
