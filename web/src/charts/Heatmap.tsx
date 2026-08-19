import { useState } from 'react'
import { blueHex } from './tokens'
import { num, pct } from '@/lib/time'

/** 7 x 24 hour-by-weekday heatmap as a CSS grid (single-hue blue ramp, 2px surface gaps, every cell a focusable tooltip target). */
export function Heatmap({ dow, hours, values, counts, isMean }: { dow: string[]; hours: number[]; values: (number | null)[][]; counts: number[][]; isMean: boolean }) {
  const flat = values.flat().filter((v): v is number => v != null && !Number.isNaN(v))
  const sorted = [...flat].sort((a, b) => a - b)
  const zmax = sorted.length ? sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.97))] : 1 // p97: one outlier cell must not flatten the ramp
  const [hover, setHover] = useState<string | null>(null)
  const fmt = (v: number | null) => (v == null ? '—' : isMean ? `${num(v, 1)} min` : pct(v))
  return (
    <div>
      <div className="overflow-x-auto">
        <div className="grid gap-[2px] min-w-[560px]" style={{ gridTemplateColumns: `36px repeat(${hours.length}, minmax(0,1fr))` }} role="table" aria-label="hour by weekday heatmap">
          <div />
          {hours.map((h) => (
            <div key={h} className="text-[10px] text-muted text-center hk-num" role="columnheader">
              {String(h).padStart(2, '0')}
            </div>
          ))}
          {dow.map((d, r) => (
            <div key={d} className="contents" role="row">
              <div className="text-[11px] text-ink-2 pr-1 flex items-center" role="rowheader">
                {d}
              </div>
              {hours.map((h, c) => {
                const v = values[r]?.[c] ?? null
                const n = counts[r]?.[c] ?? 0
                const t = v == null ? null : Math.min(v / Math.max(zmax, 1e-9), 1)
                const label = `${d} ${String(h).padStart(2, '0')}:00 · ${fmt(v)} · n=${n}`
                return (
                  <div
                    key={h}
                    role="cell"
                    tabIndex={0}
                    aria-label={label}
                    title={label}
                    onMouseEnter={() => setHover(label)}
                    onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover(label)}
                    onBlur={() => setHover(null)}
                    className="h-[22px] rounded-[2px] outline-offset-[-2px]"
                    style={{ background: t == null ? '#0f1829' : blueHex(t) }}
                  />
                )
              })}
            </div>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-between mt-1.5 text-[0.72rem] text-muted">
        <span className="hk-num min-h-4">{hover ?? 'hover or focus a cell'}</span>
        <span className="inline-flex items-center gap-1.5">
          0<span className="inline-block w-[70px] h-2 rounded-full" style={{ background: 'linear-gradient(90deg,#184f95,#256abf,#3987e5,#6da7ec,#9ec5f4)' }} aria-hidden="true" />
          {fmt(zmax)}+
        </span>
      </div>
    </div>
  )
}
