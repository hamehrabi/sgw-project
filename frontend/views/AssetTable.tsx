'use client'

/**
 * AssetTable — the joined asset view. One record per asset, every value with its source
 * and its age.
 *
 * The five states, and the one that matters most is *empty*:
 *
 * - **empty** reads "no assets in this storm", never a blank table. Three of this product's
 *   screens look like good news when they are blank, and a silent empty table during a storm
 *   is indistinguishable from a grid with nothing wrong with it.
 * - **needs_review** rows are surfaced at the top with a badge, never quietly filtered out.
 *   AC-001 requires that records the join could not resolve reach a person; a row hidden
 *   behind a filter has not reached anyone.
 * - an **estimated** value renders visually distinct from a measured one and says so in
 *   text as well — colour is never the only signal (WCAG 2.1 AA, Q-013).
 *
 * It computes nothing. No score, no rank, no band — those come from `scoring/`, in the other
 * process, and FF-002 fails the build if any of ADR-007's constants appear in this directory.
 */

import { Asset, AssetPage, AssetValue } from '@/lib/api'

function Value({ value }: { value: AssetValue }) {
  if (value.value === null || value.value === '') {
    // Not "0", not blank. A missing measurement must not read as a good one.
    return <span className="text-faint">not recorded</span>
  }
  return (
    <span className={value.estimated ? 'italic text-ink-secondary' : undefined}>
      {value.value}
      {value.estimated && <span className="text-[11px] text-muted"> (estimated)</span>}
      {value.observed_at && <span className="text-[11px] text-muted"> · {value.observed_at}</span>}
      {value.source && <span className="text-[11px] text-muted"> · {value.source}</span>}
    </span>
  )
}

function Row({ asset }: { asset: Asset }) {
  return (
    <tr className={asset.match_status === 'needs_review' ? 'border-b border-line bg-teal-soft/40' : 'border-b border-line'}>
      <td className="px-3 py-2">
        {asset.name || '—'}
        <div className="text-[11px] text-faint">{asset.external_ids.join(' · ')}</div>
        {asset.match_status === 'needs_review' && (
          <span className="mt-0.5 inline-flex rounded-full border border-line bg-background px-2 py-0.5 text-[11px] text-muted" data-testid="needs-review">
            needs review
          </span>
        )}
      </td>
      <td className="px-3 py-2">{asset.type}</td>
      {asset.values.map((value) => (
        <td key={value.name} className="px-3 py-2">
          <Value value={value} />
        </td>
      ))}
    </tr>
  )
}

export function AssetTable({
  page,
  state,
}: {
  page: AssetPage | null
  state: 'loading' | 'ready' | 'error'
}) {
  if (state === 'loading') {
    return (
      <p role="status" data-testid="asset-table-loading">
        Loading the asset view…
      </p>
    )
  }

  if (state === 'error') {
    return (
      <p role="alert">
        We could not load the asset view. The storm is still loaded — try again.
      </p>
    )
  }

  if (!page || page.items.length === 0) {
    return (
      <p role="status" data-testid="assets-empty">
        No assets in this storm. This is not the same as no risk — if you expected assets
        here, the load did not contain them.
      </p>
    )
  }

  // Unresolved records first: they are the ones a person has to act on.
  const ordered = [...page.items].sort((a, b) =>
    a.match_status === b.match_status ? 0 : a.match_status === 'needs_review' ? -1 : 1,
  )
  const columns = page.items[0].values.map((value) => value.name)

  return (
    <>
      {page.needs_review_count > 0 && (
        <p className="rounded-card border border-line bg-rail px-3 py-2 text-[13px]" data-testid="needs-review-count">
          {page.needs_review_count} record(s) could not be matched to a single asset and need
          a person to resolve them. They are listed first, and were never merged on a guess.
        </p>
      )}
      <div className="overflow-x-auto rounded-card border border-line"><table className="w-full text-[13px]" data-testid="asset-table">
        <thead className="bg-rail">
          <tr>
            <th className="px-3 py-2 text-left text-[12px] font-medium uppercase tracking-wide text-muted">Asset</th>
            <th className="px-3 py-2 text-left text-[12px] font-medium uppercase tracking-wide text-muted">Type</th>
            {columns.map((name) => (
              <th key={name} className="px-3 py-2 text-left text-[12px] font-medium uppercase tracking-wide text-muted capitalize">{name.replace(/_/g, ' ')}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ordered.map((asset) => (
            <Row key={asset.asset_id} asset={asset} />
          ))}
        </tbody>
      </table></div>
    </>
  )
}
