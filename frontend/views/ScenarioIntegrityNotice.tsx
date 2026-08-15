'use client'

/**
 * ScenarioIntegrityNotice — a prepared file that backed this scenario is gone.
 *
 * Added by CHG-013. It is deliberately **not** a staleness warning and deliberately **not**
 * an error state: the joined view is served from stored rows, so the picture on screen is
 * still correct and saying otherwise would be a lie in the safe direction.
 *
 * What the loss actually costs is replay — `outages.csv` is what a replayed storm is scored
 * against — and recovery, since a backup is the database *plus* these files. Both are
 * admin concerns, so this renders for an admin and says which file and what it affects,
 * rather than alarming a dispatcher about a screen that is fine.
 */

import { Integrity } from '@/lib/api'

export function ScenarioIntegrityNotice({
  integrity,
  role,
}: {
  integrity: Integrity
  role: 'admin' | 'user'
}) {
  if (integrity.intact || role !== 'admin') return null

  return (
    <div className="integrity" role="status" data-testid="integrity-notice">
      <strong>Source files missing:</strong> {integrity.missing_files.join(', ')}. The picture
      below is unaffected — it is served from stored records. What this breaks is{' '}
      {integrity.affects.join(' and ')}: restore the files from backup before relying on
      either.
    </div>
  )
}
