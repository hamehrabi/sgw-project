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
    return <span className="value value--absent">not recorded</span>
  }
  return (
    <span className={value.estimated ? 'value value--estimated' : 'value'}>
      {value.value}
      {value.estimated && <span className="value__tag"> (estimated)</span>}
      {value.observed_at && <span className="value__age"> · {value.observed_at}</span>}
      {value.source && <span className="value__source"> · {value.source}</span>}
    </span>
  )
}

function Row({ asset }: { asset: Asset }) {
  return (
    <tr className={asset.match_status === 'needs_review' ? 'row--review' : undefined}>
      <td>
        {asset.name || '—'}
        <div className="row__codes">{asset.external_ids.join(' · ')}</div>
        {asset.match_status === 'needs_review' && (
          <span className="badge" data-testid="needs-review">
            needs review
          </span>
        )}
      </td>
      <td>{asset.type}</td>
      {asset.values.map((value) => (
        <td key={value.name}>
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
        <p className="review-count" data-testid="needs-review-count">
          {page.needs_review_count} record(s) could not be matched to a single asset and need
          a person to resolve them. They are listed first, and were never merged on a guess.
        </p>
      )}
      <table className="assets" data-testid="asset-table">
        <thead>
          <tr>
            <th>Asset</th>
            <th>Type</th>
            {columns.map((name) => (
              <th key={name}>{name.replace(/_/g, ' ')}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ordered.map((asset) => (
            <Row key={asset.asset_id} asset={asset} />
          ))}
        </tbody>
      </table>
    </>
  )
}
