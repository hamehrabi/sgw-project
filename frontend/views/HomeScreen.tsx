'use client'

/**
 * The composition root, on the client side of the boundary.
 *
 * `AppShell` takes its children as a *function of the identity*, so that nothing below the
 * shell can render before the role is known — the rule is held by the type rather than by
 * remembering it. A function cannot cross from a Server Component to a Client Component, so
 * the call lives here rather than in `app/page.tsx`, which stays a server component.
 */

import { AppShell } from './AppShell'
import { ScenarioView } from './ScenarioView'

export function HomeScreen() {
  return <AppShell>{(identity) => <ScenarioView role={identity.role} />}</AppShell>
}
