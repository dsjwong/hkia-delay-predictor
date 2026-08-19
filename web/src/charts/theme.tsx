import type { ReactNode } from 'react'
import { GRID, INK, INK_2, MUTED, SURFACE_3 } from './tokens'

export const AXIS = { stroke: GRID, tick: { fill: MUTED, fontSize: 11 }, tickLine: false as const, axisLine: { stroke: GRID } }
export const GRID_PROPS = { stroke: GRID, strokeDasharray: undefined, vertical: false }
export const CURSOR = { fill: 'rgba(255,255,255,0.04)' }

/** Shared tooltip card for every Recharts chart (same chrome as the map tooltip). */
export function TipBox({ title, rows }: { title?: ReactNode; rows: [ReactNode, ReactNode][] }) {
  return (
    <div style={{ background: SURFACE_3, border: '1px solid rgba(255,255,255,0.08)', borderRadius: 6, padding: '6px 9px', color: INK, fontSize: 12, lineHeight: 1.45 }}>
      {title && <div style={{ fontWeight: 600, marginBottom: 2 }}>{title}</div>}
      {rows.map(([k, v], i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 14 }}>
          <span style={{ color: INK_2 }}>{k}</span>
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>{v}</span>
        </div>
      ))}
    </div>
  )
}

/** Chart title + optional right-side control, consistent across pages. */
export function ChartHead({ title, sub, right }: { title: string; sub?: string; right?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 mb-1">
      <div>
        <h3 className="text-[0.92rem] font-semibold text-ink leading-5">{title}</h3>
        {sub && <p className="text-xs text-muted">{sub}</p>}
      </div>
      {right}
    </div>
  )
}

/** Tiny legend for >= 2 series; swatch + label. */
export function Legend({ items }: { items: { color: string; label: string; shape?: 'line' | 'dot' | 'square' }[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-[0.72rem] text-ink-2 mb-1" aria-label="legend">
      {items.map((it) => (
        <span key={it.label} className="inline-flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block"
            style={{
              background: it.color,
              width: it.shape === 'line' ? 14 : 9,
              height: it.shape === 'line' ? 2 : 9,
              borderRadius: it.shape === 'dot' ? '50%' : it.shape === 'line' ? 1 : 2,
            }}
          />
          {it.label}
        </span>
      ))}
    </div>
  )
}
