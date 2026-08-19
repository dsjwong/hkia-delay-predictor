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
import { BLUE, GREY, GRID } from './tokens'

export interface CalBin {
  bin: string
  n: number
  pred_mean: number
  obs_rate: number
}

/** Reliability diagram: mean predicted P per bin vs observed rate; marker size ~ bin count; diagonal = perfect calibration. */
export function Reliability({ bins }: { bins: CalBin[] }) {
  const data = bins.map((b) => ({
    ...b,
    x: b.pred_mean,
    y: b.obs_rate,
    r: Math.min(Math.max(Math.sqrt(b.n) * 0.35, 3.5), 12),
  }))
  return (
    <div>
      <Legend
        items={[
          { color: BLUE, label: 'XGBoost (test) · marker size ~ bin count', shape: 'dot' },
          { color: GREY, label: 'perfect calibration', shape: 'line' },
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
            tickFormatter={(v) => v.toFixed(1)}
            label={{
              value: 'mean predicted P(delay > 15)',
              position: 'insideBottom',
              dy: 14,
              fill: '#8a94a6',
              fontSize: 11,
            }}
          />
          <YAxis type="number" dataKey="y" domain={[0, 1]} {...AXIS} tickFormatter={(v) => v.toFixed(1)} width={44} />
          <ReferenceLine
            segment={[
              { x: 0, y: 0 },
              { x: 1, y: 1 },
            ]}
            stroke={GREY}
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
                    ['n', b.n.toLocaleString()],
                  ]}
                />
              )
            }}
          />
          <Line type="linear" dataKey="y" stroke={BLUE} strokeWidth={2} dot={false} isAnimationActive={false} />
          <Scatter
            dataKey="y"
            fill={BLUE}
            shape={(p: { cx?: number; cy?: number; payload?: { r: number } }) => (
              <circle cx={p.cx} cy={p.cy} r={p.payload?.r ?? 4} fill={BLUE} stroke="#0b1220" strokeWidth={2} />
            )}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
