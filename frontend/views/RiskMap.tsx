'use client'

/**
 * RiskMap — asset locations as graduated dots (CHG-041).
 *
 * **Assets, never damage.** An asset coordinate comes from the utility's own registry
 * and CON-003 never forbade it; a damage report has no coordinate to plot, because the
 * store holds nothing finer than a neighbourhood — so there is nothing here to leak.
 *
 * Two renderers behind one panel:
 *
 * - With `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` set, the Google Maps JavaScript API draws a
 *   neutral, label-light base. **What leaves the browser is the viewport bounds** for
 *   tile requests; markers are placed client-side and the asset list is never sent —
 *   recorded in CHG-041, decided knowingly by the client, the second paid service under
 *   CON-006.
 * - Without a key, a plain SVG scatter of the same coordinates on a neutral ground. The
 *   screen is complete before the key exists and upgrades when it arrives.
 *
 * No storm track, no cone, no wind overlay, no legend — the product is not a weather
 * tracker, and the dots are graduated by band while the band stays a word in the table
 * beside them (colour is never the only signal).
 */

import { useEffect, useRef } from 'react'

import { Card } from '@/components/ui/card'
import { AssetPage, Ranking } from '@/lib/api'

const KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY

const DOT_FILL: Record<string, string> = {
  High: '#b91c1c',
  Medium: '#b45309',
  Low: '#047857',
  unscored: '#94a3b8',
}

interface Spot {
  lat: number
  lon: number
  band: string
  label: string
}

function spots(page: AssetPage, ranking: Ranking): Spot[] {
  const bands = new Map(ranking.items.map((item) => [item.asset_id, item.band ?? 'unscored']))
  return page.items.map((asset) => ({
    lat: asset.location.lat,
    lon: asset.location.lon,
    band: bands.get(asset.asset_id) ?? 'unscored',
    label: asset.name || asset.external_ids[0],
  }))
}

/** The offline half: a projected scatter on a neutral ground. */
function Scatter({ points }: { points: Spot[] }) {
  if (points.length === 0) return null
  const lats = points.map((p) => p.lat)
  const lons = points.map((p) => p.lon)
  const [minLat, maxLat] = [Math.min(...lats), Math.max(...lats)]
  const [minLon, maxLon] = [Math.min(...lons), Math.max(...lons)]
  const spanLat = Math.max(maxLat - minLat, 0.0001)
  const spanLon = Math.max(maxLon - minLon, 0.0001)

  return (
    <svg
      viewBox="0 0 400 300"
      role="img"
      aria-label={`${points.length} assets plotted by location, dot colour by risk band`}
      className="h-full w-full rounded-b-[7px] bg-panel"
    >
      {points.map((point, index) => (
        <circle
          key={index}
          cx={20 + ((point.lon - minLon) / spanLon) * 360}
          cy={280 - ((point.lat - minLat) / spanLat) * 260}
          r={point.band === 'High' ? 5 : point.band === 'Medium' ? 4 : 3}
          fill={DOT_FILL[point.band]}
          fillOpacity={point.band === 'unscored' ? 0.6 : 0.85}
        >
          <title>{`${point.label} — ${point.band === 'unscored' ? 'not scored' : point.band}`}</title>
        </circle>
      ))}
    </svg>
  )
}

/** The Google half, loaded only when a key exists and only on this panel. */
function GoogleMap({ points }: { points: Spot[] }) {
  const host = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!KEY || !host.current || points.length === 0) return
    let cancelled = false

    async function draw() {
      const globe = window as typeof window & { google?: any } // eslint-disable-line @typescript-eslint/no-explicit-any
      if (!globe.google?.maps) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement('script')
          script.src = `https://maps.googleapis.com/maps/api/js?key=${KEY}&loading=async&v=weekly`
          script.async = true
          script.onload = () => resolve()
          script.onerror = () => reject(new Error('maps failed to load'))
          document.head.appendChild(script)
        })
      }
      if (cancelled || !host.current) return
      const { Map: GMap } = await globe.google.maps.importLibrary('maps')
      const bounds = new globe.google.maps.LatLngBounds()
      points.forEach((p) => bounds.extend({ lat: p.lat, lng: p.lon }))
      const map = new GMap(host.current, {
        disableDefaultUI: true,
        gestureHandling: 'cooperative',
        // A neutral, label-light base: the dots are the content.
        styles: [
          { featureType: 'poi', stylers: [{ visibility: 'off' }] },
          { featureType: 'transit', stylers: [{ visibility: 'off' }] },
          { elementType: 'labels', stylers: [{ saturation: -100 }] },
          { stylers: [{ saturation: -80 }, { lightness: 20 }] },
        ],
      })
      map.fitBounds(bounds, 24)
      points.forEach((p) => {
        new globe.google.maps.Marker({
          map,
          position: { lat: p.lat, lng: p.lon },
          title: `${p.label} — ${p.band === 'unscored' ? 'not scored' : p.band}`,
          icon: {
            path: globe.google.maps.SymbolPath.CIRCLE,
            scale: p.band === 'High' ? 6 : p.band === 'Medium' ? 5 : 4,
            fillColor: DOT_FILL[p.band],
            fillOpacity: 0.85,
            strokeWeight: 0,
          },
        })
      })
    }

    void draw().catch(() => {
      // The scatter fallback cannot be swapped in mid-effect without a re-render dance;
      // an empty panel with the heading is honest enough for a tile outage.
    })
    return () => {
      cancelled = true
    }
  }, [points])

  return <div ref={host} className="h-full w-full rounded-b-[7px]" />
}

export function RiskMap({ page, ranking }: { page: AssetPage; ranking: Ranking }) {
  const points = spots(page, ranking)

  return (
    <Card data-testid="risk-map" className="overflow-hidden">
      <p className="border-b border-line px-4 py-2.5 text-[13px] font-semibold">
        Asset map
        <span className="ml-2 font-normal text-muted">
          {points.length} assets · dots by risk band
        </span>
      </p>
      <div className="h-64">
        {KEY ? <GoogleMap points={points} /> : <Scatter points={points} />}
      </div>
    </Card>
  )
}
