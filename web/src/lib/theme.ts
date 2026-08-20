/** Colour tokens — shadcn/ui "zinc" dark + one amber accent (see docs/design.md).
 *  Validated with the dataviz skill's validate_palette.js on the card surface #18181b (dark):
 *  categorical [#d97706 amber-600, #0d9488 teal-600, #8b5cf6 violet-500, #db2777 pink-600] — every check PASS
 *  (worst adjacent CVD ΔE 10.4, normal-vision 24.3, all ≥ 3:1). Amber ramp = single-hue sequential, dim → bright. */
export const BG = '#09090b'
export const CARD = '#18181b'
export const ELEV = '#1f1f23'
export const ELEV_2 = '#27272a'
export const BORDER = '#27272a'
export const BORDER_2 = '#3f3f46'
export const INK = '#fafafa'
export const INK_2 = '#a1a1aa'
export const MUTED = '#71717a'
export const GRID = '#27272a'
/** categorical slots, fixed order: 1 = model / predicted (amber), 2 = observed / actual (teal), 3, 4 rarely used */
export const SERIES_1 = '#d97706'
export const SERIES_2 = '#0d9488'
export const SERIES_3 = '#8b5cf6'
export const SERIES_4 = '#db2777'
export const CATEGORICAL = [SERIES_1, SERIES_2, SERIES_3, SERIES_4]
export const ACCENT = '#f59e0b'
export const GOOD = '#22c55e'
export const WARNING = '#f59e0b'
export const CRITICAL = '#ef4444'
/** Typhoon-signal background bands (Case-study route). Deliberately NOT a colour-encoded series: they are
 *  labelled regions behind the delay bars, so the level is read off the T1/T3/T8/T9 chip, never off the tint.
 *  The dataviz validator's ordinal gate (ΔL >= 0.06, light end >= 2:1 vs surface) is inapplicable and does not pass
 *  for these values — a band that cleared 2:1 against the card would out-shout the bars it sits behind.
 *  Keyed by signal level; anything not listed (0) draws no band. */
export const SIGNAL_BAND: Record<number, string> = {
  1: 'rgba(250,250,250,0.040)',
  3: 'rgba(250,250,250,0.070)',
  8: 'rgba(250,250,250,0.115)',
  9: 'rgba(250,250,250,0.165)',
}
/** neutral reference line / "perfect" diagonal */
export const NEUTRAL = '#52525b'
/** P(delay > 15): single-hue amber, dim -> bright on the dark surface (amber-900 → amber-300) */
export const AMBER_RAMP = ['#78350f', '#b45309', '#d97706', '#f59e0b', '#fcd34d']
/** heatmap magnitude (delay minutes / late share) — same amber hue so "more amber = more delay" holds app-wide */
export const HEAT_RAMP = ['#2a1a08', '#6b3410', '#a85a0c', '#d98a1b', '#f7c55a']

function hex2rgb(h: string): [number, number, number] {
  const s = h.replace('#', '')
  return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)]
}

/** Interpolate a ramp at t in [0,1] -> [r,g,b]. */
export function rampRgb(ramp: string[], t: number | null | undefined): [number, number, number] {
  const x = t == null || Number.isNaN(t) ? 0 : Math.min(Math.max(t, 0), 1)
  const pos = x * (ramp.length - 1)
  const i = Math.min(Math.floor(pos), ramp.length - 2)
  const f = pos - i
  const a = hex2rgb(ramp[i])
  const b = hex2rgb(ramp[i + 1])
  return [
    Math.round(a[0] + (b[0] - a[0]) * f),
    Math.round(a[1] + (b[1] - a[1]) * f),
    Math.round(a[2] + (b[2] - a[2]) * f),
  ]
}

export function rampHex(ramp: string[], t: number | null | undefined): string {
  const [r, g, b] = rampRgb(ramp, t)
  return '#' + [r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')
}

export const amberRgb = (p: number | null | undefined) => rampRgb(AMBER_RAMP, p)
export const amberHex = (p: number | null | undefined) => rampHex(AMBER_RAMP, p)
export const heatHex = (t: number | null | undefined) => rampHex(HEAT_RAMP, t)

/** Other traffic: zinc-500 -> zinc-100 by altitude (0..40k ft), dim zinc-600 on the ground. */
export function altGrey(altFt: number, onGround: boolean): [number, number, number, number] {
  if (onGround) return [82, 82, 91, 190]
  const f = Math.min(Math.max(altFt, 0), 40000) / 40000
  const lo = [113, 113, 122]
  const hi = [244, 244, 245]
  return [
    Math.round(lo[0] + (hi[0] - lo[0]) * f),
    Math.round(lo[1] + (hi[1] - lo[1]) * f),
    Math.round(lo[2] + (hi[2] - lo[2]) * f),
    235,
  ]
}
