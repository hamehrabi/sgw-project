'use client'

/**
 * RiskMap — every scored asset that carries coordinates, on a real basemap (CHG-058).
 *
 * **Assets, never damage.** An asset coordinate comes from the utility's own registry
 * and CON-003 never forbade it; a damage report has no coordinate to plot, because the
 * store holds nothing finer than a neighbourhood — so there is nothing here to leak.
 *
 * Leaflet with OpenStreetMap raster tiles: free, no key, no account. **What leaves the
 * browser is the viewport's tile coordinates** to the OSM tile servers; markers are
 * placed client-side and the asset list never leaves the machine (CHG-058, the same
 * disclosure class CHG-041 recorded for the provider it replaces). Attribution is
 * required and shown.
 *
 * Leaflet touches `window` at import time, so it is imported only inside the effect —
 * the render path stays clean for the Node half of FF-003(c). Offline, the circles
 * still render over an unloaded base: a degraded picture, not a broken screen.
 */

import 'leaflet/dist/leaflet.css'

import { useEffect, useMemo, useRef } from 'react'

import { Card } from '@/components/ui/card'
import { AssetPage, Ranking } from '@/lib/api'

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
  rank: number | null
  label: string
}

export function RiskMap({ page, ranking }: { page: AssetPage; ranking: Ranking }) {
  const host = useRef<HTMLDivElement>(null)

  const points = useMemo<Spot[]>(() => {
    const items = new Map(ranking.items.map((item) => [item.asset_id, item]))
    return page.items
      .filter((asset) => Number.isFinite(asset.location.lat) && Number.isFinite(asset.location.lon))
      .map((asset) => {
        const item = items.get(asset.asset_id)
        return {
          lat: asset.location.lat,
          lon: asset.location.lon,
          band: item?.band ?? 'unscored',
          rank: item?.rank ?? null,
          label: asset.name || asset.external_ids[0],
        }
      })
  }, [page, ranking])

  useEffect(() => {
    let cancelled = false
    let cleanup: (() => void) | undefined

    void (async () => {
      const node = host.current
      if (!node || points.length === 0) return
      const L = (await import('leaflet')).default
      if (cancelled || !host.current) return

      const map = L.map(node, { scrollWheelZoom: false, attributionControl: true })
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(map)

      const latLngs: [number, number][] = []
      for (const point of points) {
        latLngs.push([point.lat, point.lon])
        L.circleMarker([point.lat, point.lon], {
          radius: point.band === 'High' ? 7 : point.band === 'Medium' ? 5.5 : 4.5,
          color: DOT_FILL[point.band],
          fillColor: DOT_FILL[point.band],
          fillOpacity: 0.75,
          weight: 1,
        })
          .bindPopup(
            `<strong>${point.label}</strong><br/>` +
              (point.rank !== null
                ? `Rank ${point.rank} · ${point.band} risk`
                : 'Not scored — not judged low risk'),
          )
          .addTo(map)
      }
      map.fitBounds(L.latLngBounds(latLngs), { padding: [24, 24], maxZoom: 12 })

      cleanup = () => map.remove()
    })()

    return () => {
      cancelled = true
      cleanup?.()
    }
  }, [points])

  return (
    <Card data-testid="risk-map" className="overflow-hidden">
      <p className="border-b border-line px-4 py-2.5 text-[13px] font-semibold">
        Infrastructure risk map
        <span className="ml-2 font-normal text-muted">
          every scored asset with coordinates
        </span>
      </p>
      {points.length === 0 ? (
        <p className="p-4 text-[13px] text-muted">
          None of the loaded assets carry coordinates, so there is nothing to place on
          the map. This is a statement about the data, not about the risk.
        </p>
      ) : (
        <>
          {/* `relative z-0` is load-bearing (CHG-060): Leaflet's internal panes carry
              z-indexes in the hundreds, and without a stacking context here they paint
              over the asset drawer. This contains them at the card's own level. */}
          <div ref={host} className="relative z-0 h-64 w-full" />
          <div className="flex items-center gap-4 border-t border-line px-4 py-2.5 text-[12px] text-muted">
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: DOT_FILL.High }} />
              High
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: DOT_FILL.Medium }} />
              Medium
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: DOT_FILL.Low }} />
              Low
            </span>
            <span className="ml-auto tabular-nums" data-testid="map-count">
              {points.length} mapped
            </span>
          </div>
        </>
      )}
    </Card>
  )
}
