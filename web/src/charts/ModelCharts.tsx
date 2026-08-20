import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AXIS, Legend, TipBox } from './theme'
import { CARD, GRID, MUTED, NEUTRAL, SERIES_1 } from './tokens'

export interface CalBin {
  bin: string
  n: number
  pred_mean: number
  obs_rate: number
}

/** Reliability diagram: mean predicted P per bin vs observed rate; marker size ~ bin count; diagonal = perfect calibration.
 *  `label` names the series because the same chart draws the held-out test bins and the live ones.
 *  `minN` bins are drawn hollow and the connecting line stops at them: joining a 6-flight bin to its neighbours turns
 *  three coin flips into a dramatic-looking zig-zag. */
export function Reliability({
  bins,
  label = 'XGBoost (test)',
  minN = 0,
}: {
  bins: CalBin[]
  label?: string
  minN?: number
}) {
  const data = bins.map((b) => ({
    ...b,
    x: b.pred_mean,
    y: b.obs_rate,
    thin: b.n < minN,
    // the line only spans the bins with enough flights to mean anything
    yLine: b.n < minN ? null : b.obs_rate,
    r: Math.min(Math.max(Math.sqrt(b.n) * 0.35, 3.5), 12),
  }))
  const thinBins = data.filter((b) => b.thin).length
  return (
    <div
      role="img"
      aria-label={`Reliability diagram. ${data
        .map(
          (b) => `bin ${b.bin}: predicted ${b.pred_mean.toFixed(2)}, observed ${b.obs_rate.toFixed(2)}, ${b.n} flights`,
        )
        .join('; ')}.`}
    >
      <Legend
        items={[
          { color: SERIES_1, label: `${label} · marker size ~ bin count`, shape: 'dot' },
          { color: NEUTRAL, label: 'perfect calibration', shape: 'line' },
          ...(thinBins ? [{ color: CARD, label: `hollow = under ${minN} flights`, shape: 'dot' as const }] : []),
        ]}
      />
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 16, left: -4 }}>
          <CartesianGrid stroke={GRID} />
          <XAxis
            type="number"
            dataKey="x"
            domain={[0, 1]}
            {...AXIS}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tickFormatter={(v: number) => String(v)}
            label={{
              value: 'mean predicted P(delay > 15)',
              position: 'insideBottom',
              dy: 14,
              fill: MUTED,
              fontSize: 11,
            }}
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={[0, 1]}
            {...AXIS}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tickFormatter={(v: number) => String(v)}
            width={44}
          />
          <ReferenceLine
            segment={[
              { x: 0, y: 0 },
              { x: 1, y: 1 },
            ]}
            stroke={NEUTRAL}
            strokeWidth={1}
          />
          <Tooltip
            cursor={false}
            content={({ active, payload }) => {
              const b = payload?.[0]?.payload as CalBin | undefined
              if (!active || !b) return null
              return (
                <TipBox
                  title={`bin ${b.bin}`}
                  rows={[
                    ['predicted', b.pred_mean.toFixed(2)],
                    ['observed', b.obs_rate.toFixed(2)],
                    ['n', `${b.n.toLocaleString()}${b.n < minN ? ' — too few to read' : ''}`],
                  ]}
                />
              )
            }}
          />
          <Line
            type="linear"
            dataKey={minN ? 'yLine' : 'y'}
            stroke={SERIES_1}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Scatter
            dataKey="y"
            fill={SERIES_1}
            shape={(p: { cx?: number; cy?: number; payload?: { r: number; thin?: boolean } }) => (
              <circle
                cx={p.cx}
                cy={p.cy}
                r={p.payload?.r ?? 4}
                fill={p.payload?.thin ? CARD : SERIES_1}
                stroke={p.payload?.thin ? SERIES_1 : CARD}
                strokeWidth={2}
              />
            )}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
