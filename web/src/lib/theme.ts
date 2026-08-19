/** Palette tokens shared with app/theme.py; validated with the dataviz skill's validate_palette.js on #0b1220 (dark):
 *  categorical #3987e5 #d95926 #199e70 #c98500 (adjacent pairs PASS), amber ramp (ordinal PASS), blue ramp (PASS). */
export const SURFACE = '#0b1220'
export const SURFACE_2 = '#121c2e'
export const BORDER = 'rgba(255,255,255,0.08)'
export const INK = '#e6ebf2'
export const INK_2 = '#b4bdcc'
export const MUTED = '#8a94a6'
export const GRID = '#1c2739'
export const BLUE = '#3987e5'
export const ORANGE = '#d95926'
export const AQUA = '#199e70'
export const YELLOW = '#c98500'
export const GREY = '#5b6577'
export const GOOD = '#0ca30c'
export const WARNING = '#fab219'
export const CRITICAL = '#d03b3b'
export const CATEGORICAL = [BLUE, ORANGE, AQUA, YELLOW]
/** P(delay > 15): single-hue amber, dim -> bright on the dark surface */
export const AMBER_RAMP = ['#6b4608', '#94620a', '#bd7f0c', '#e39d14', '#ffbf3d']
/** heatmap magnitude: single-hue blue */
export const BLUE_RAMP = ['#184f95', '#256abf', '#3987e5', '#6da7ec', '#9ec5f4']

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
export const blueHex = (t: number | null | undefined) => rampHex(BLUE_RAMP, t)

/** Other traffic: grey -> white by altitude (0..40k ft), dim grey on the ground. */
export function altGrey(altFt: number, onGround: boolean): [number, number, number, number] {
  if (onGround) return [95, 104, 122, 200]
  const f = Math.min(Math.max(altFt, 0), 40000) / 40000
  const lo = [120, 130, 150]
  const hi = [236, 240, 246]
  return [
    Math.round(lo[0] + (hi[0] - lo[0]) * f),
    Math.round(lo[1] + (hi[1] - lo[1]) * f),
    Math.round(lo[2] + (hi[2] - lo[2]) * f),
    230,
  ]
}
