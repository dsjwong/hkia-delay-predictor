import { BLUE, GRID, MUTED } from '@/lib/theme'
import { hm, pct } from '@/lib/time'

/** Tiny inline SVG line of a flight's prediction history ([epoch_s, p, pred_min]); every point also has a <title>. */
export function Sparkline({
  history,
  width = 260,
  height = 56,
}: {
  history: [number, number | null, number | null][]
  width?: number
  height?: number
}) {
  const pts = history.filter((h) => h[1] != null) as [number, number, number | null][]
  if (pts.length < 2) return <div className="text-xs text-muted">only one score so far</div>
  const t0 = pts[0][0]
  const t1 = pts[pts.length - 1][0]
  const ps = pts.map((p) => p[1])
  const yMax = Math.min(1, Math.max(0.25, Math.max(...ps) * 1.25)) // auto-scaled so small moves stay visible; never above 1
  const x = (t: number) => 4 + ((t - t0) / Math.max(t1 - t0, 1)) * (width - 8)
  const y = (p: number) => 4 + (1 - p / yMax) * (height - 12)
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ')
  return (
    <svg
      width={width}
      height={height}
      role="img"
      aria-label={`P(delay > 15) over ${pts.length} scores from ${hm(pts[0][0])} to ${hm(t1)} HKT`}
      className="block max-w-full"
    >
      {yMax >= 0.5 && <line x1={4} x2={width - 4} y1={y(0.5)} y2={y(0.5)} stroke={GRID} strokeWidth={1} />}
      <text x={width - 4} y={10} fontSize={9} fill={MUTED} textAnchor="end">
        {pct(ps[ps.length - 1])} · axis 0–{Math.round(yMax * 100)} %
      </text>
      <path d={d} fill="none" stroke={BLUE} strokeWidth={1.5} />
      {pts.map((p, i) => (
        <circle
          key={i}
          cx={x(p[0])}
          cy={y(p[1])}
          r={i === pts.length - 1 ? 3.2 : 2}
          fill={BLUE}
          stroke="#0b1220"
          strokeWidth={1}
        >
          <title>
            {hm(p[0])} HKT · P {pct(p[1])}
            {p[2] != null ? ` · ${Math.round(p[2])} min` : ''}
          </title>
        </circle>
      ))}
      <text x={4} y={height - 1} fontSize={9} fill={MUTED}>
        {hm(t0)}
      </text>
      <text x={width - 4} y={height - 1} fontSize={9} fill={MUTED} textAnchor="end">
        {hm(t1)} HKT
      </text>
    </svg>
  )
}
