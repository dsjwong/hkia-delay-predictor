import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
// maplibre-gl >= 6 is ESM-only and resolves its tile-parsing worker with `new URL('./maplibre-gl-worker.mjs', import.meta.url)`,
// which does not survive bundling (the file is not emitted next to the chunk, so tiles never load and the map stays blank).
// Let Vite bundle the worker as its own entry and hand maplibre the resulting URL.
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { MapboxOverlay } from '@deck.gl/mapbox'
import { IconLayer, PolygonLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers'
import type { PickingInfo } from '@deck.gl/core'
import { HKIA, circle, deadReckon } from '@/lib/geo'
import { RADIUS_NM } from '@/lib/adsb'
import { altGrey, amberRgb } from '@/lib/theme'
import { hm, pct } from '@/lib/time'
import { PLANE_ATLAS, PLANE_MAPPING } from './plane-icon'
import type { TrackedAircraft } from './match'

export const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'
maplibregl.setWorkerUrl(maplibreWorkerUrl)

interface Props {
  aircraft: TrackedAircraft[]
  selectedHex: string | null
  onSelect: (hex: string | null) => void
  /** HKT label for the footer */
  className?: string
}

interface Plotted extends TrackedAircraft {
  pos: [number, number]
  color: [number, number, number, number]
  size: number
}

function tooltipHtml(d: Plotted): string {
  const head = `<b>${d.callsign || '—'}</b> ${d.reg} ${d.type}<br/>${d.onGround ? 'ground' : Math.round(d.altFt).toLocaleString() + ' ft'} · ${d.gsKt == null ? '' : Math.round(d.gsKt) + ' kt'}`
  if (!d.flight) return `${head}<br/><span style="color:#71717a">not an HKIA departure we track</span>`
  const f = d.flight
  const pred = f.pred_min == null ? '' : ` · pred ${Math.round(f.pred_min)} min`
  return `${head}<br/>${f.flight_no} → ${d.destLabel} · ${d.airlineName}<br/>sched ${hm(f.sched_ts)} · actual ${hm(f.actual_ts)}<br/>P(delay > 15) ${f.p == null ? 'not scored' : pct(f.p)}${pred}`
}

export function MapView({ aircraft, selectedHex, onSelect, className }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const overlay = useRef<MapboxOverlay | null>(null)
  const data = useRef<TrackedAircraft[]>(aircraft)
  const sel = useRef<string | null>(selectedHex)
  const onSelectRef = useRef(onSelect)
  const hover = useRef<string | null>(null)
  useEffect(() => {
    data.current = aircraft
    sel.current = selectedHex
    onSelectRef.current = onSelect
  }, [aircraft, selectedHex, onSelect])

  useEffect(() => {
    if (!el.current) return
    const m = new maplibregl.Map({
      container: el.current,
      style: MAP_STYLE,
      center: [HKIA.lon, HKIA.lat + 0.05],
      zoom: 7.4,
      minZoom: 5,
      maxZoom: 13,
      attributionControl: false,
    })
    m.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left')
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    m.keyboard.enable()
    const ov = new MapboxOverlay({
      interleaved: false,
      getTooltip: (info: PickingInfo) =>
        info.object && (info.object as Plotted).callsign !== undefined
          ? {
              html: `<div style="font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;line-height:1.5">${tooltipHtml(info.object as Plotted)}</div>`,
              style: {
                backgroundColor: 'rgba(31,31,35,0.92)',
                color: '#fafafa',
                border: '1px solid #3f3f46',
                borderRadius: '8px',
                padding: '6px 10px',
                backdropFilter: 'blur(8px)',
              },
            }
          : null,
      onClick: (info: PickingInfo) => {
        const o = info.object as Plotted | undefined
        onSelectRef.current(o ? o.hex : null)
      },
      onHover: (info: PickingInfo) => {
        const o = info.object as Plotted | undefined
        hover.current = o ? o.hex : null
      },
    })
    m.addControl(ov)
    map.current = m
    overlay.current = ov

    const rings = new PolygonLayer({
      id: 'rings',
      data: [{ poly: circle(HKIA.lat, HKIA.lon, RADIUS_NM) }, { poly: circle(HKIA.lat, HKIA.lon, 50) }],
      getPolygon: (d: { poly: [number, number][] }) => d.poly,
      stroked: true,
      filled: false,
      getLineColor: [161, 161, 170, 55],
      lineWidthMinPixels: 1,
      pickable: false,
    })
    const hkia = new ScatterplotLayer({
      id: 'hkia',
      data: [{ pos: [HKIA.lon, HKIA.lat] }],
      getPosition: (d: { pos: [number, number] }) => d.pos,
      getRadius: 900,
      getFillColor: [245, 158, 11, 60],
      getLineColor: [245, 158, 11, 200],
      stroked: true,
      lineWidthMinPixels: 1.5,
      pickable: false,
    })
    const label = new TextLayer({
      id: 'hkia-label',
      data: [{ pos: [HKIA.lon, HKIA.lat - 0.07], txt: 'VHHH  HKIA  RWY 07L/25R 07R/25L' }],
      getPosition: (d: { pos: [number, number] }) => d.pos,
      getText: (d: { txt: string }) => d.txt,
      getColor: [161, 161, 170, 255],
      getSize: 11,
      getAlignmentBaseline: 'top',
      fontFamily: 'ui-monospace, Menlo, Consolas, monospace',
      pickable: false,
    })

    // prefers-reduced-motion: no gliding — positions jump on each poll (1 fps redraw) instead of 10 fps dead-reckoning
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    const frameMs = reduce ? 1000 : 100
    let raf = 0
    let last = 0
    const frame = (t: number) => {
      raf = requestAnimationFrame(frame)
      if (t - last < frameMs) return // ~10 fps is plenty for gliding icons
      last = t
      const now = Date.now()
      const plotted: Plotted[] = data.current.map((a) => {
        const p = deadReckon(
          { lat: a.lat, lon: a.lon, gsKt: a.onGround || reduce ? 0 : a.gsKt, trackDeg: a.trackDeg, t: a.posAt },
          (now - a.posAt) / 1000,
          90,
        )
        let color: [number, number, number, number]
        let size: number
        if (a.flight && a.flight.p != null) {
          const [r, g, b] = amberRgb(a.flight.p)
          color = [r, g, b, 255]
          size = 30
        } else if (a.flight) {
          color = [250, 250, 250, 255]
          size = 28
        } else {
          color = altGrey(a.altFt, a.onGround)
          size = 17
        }
        return { ...a, pos: [p.lon, p.lat], color, size }
      })
      const others = plotted.filter((d) => !d.flight)
      const tracked = plotted.filter((d) => !!d.flight)
      const selected = plotted.filter((d) => d.hex === sel.current)
      const hovered = plotted.filter((d) => d.hex === hover.current && d.hex !== sel.current)
      const common = {
        iconAtlas: PLANE_ATLAS,
        iconMapping: PLANE_MAPPING,
        getIcon: () => 'plane',
        getPosition: (d: Plotted) => d.pos,
        getAngle: (d: Plotted) => -(d.trackDeg ?? 0),
        getColor: (d: Plotted) => d.color,
        getSize: (d: Plotted) => d.size,
        sizeUnits: 'pixels' as const,
        billboard: false,
        pickable: true,
        updateTriggers: { getPosition: now, getColor: now, getAngle: now },
      }
      ov.setProps({
        layers: [
          rings,
          hkia,
          label,
          new ScatterplotLayer({
            id: 'hovered',
            data: hovered,
            getPosition: (d: Plotted) => d.pos,
            getRadius: 18,
            radiusUnits: 'pixels',
            stroked: true,
            filled: false,
            getLineColor: [250, 250, 250, 160],
            lineWidthMinPixels: 1,
            pickable: false,
            updateTriggers: { getPosition: now },
          }),
          new ScatterplotLayer({
            id: 'selected',
            data: selected,
            getPosition: (d: Plotted) => d.pos,
            getRadius: 22,
            radiusUnits: 'pixels',
            stroked: true,
            filled: false,
            getLineColor: [245, 158, 11, 230],
            lineWidthMinPixels: 2,
            pickable: false,
            updateTriggers: { getPosition: now },
          }),
          new IconLayer({ id: 'others', data: others, sizeMinPixels: 10, sizeMaxPixels: 22, ...common }),
          new IconLayer({ id: 'tracked', data: tracked, sizeMinPixels: 18, sizeMaxPixels: 36, ...common }),
        ],
      })
    }
    raf = requestAnimationFrame(frame)
    return () => {
      cancelAnimationFrame(raf)
      m.remove()
      map.current = null
      overlay.current = null
    }
  }, [])

  // fly to the selected aircraft when it changes (keeps the user oriented)
  useEffect(() => {
    if (!selectedHex || !map.current) return
    const a = data.current.find((x) => x.hex === selectedHex)
    if (a) map.current.easeTo({ center: [a.lon, a.lat], duration: 600 })
  }, [selectedHex])

  // maplibre's own CSS sets .maplibregl-map { position: relative }, so the sized box is the wrapper, not the map element
  return (
    <div className={className} role="region" aria-label="Live aircraft map around HKIA">
      <div ref={el} style={{ position: 'absolute', inset: 0 }} />
    </div>
  )
}
