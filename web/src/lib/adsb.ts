/** Live aircraft within ~100 nm of HKIA from the free adsb.lol community feed (no key).
 *
 *  CORS: api.adsb.lol (like adsb.fi / airplanes.live / anonymous OpenSky) sends no Access-Control-Allow-Origin header, so a
 *  browser on another origin cannot read it directly (verified 2026-08-19 with curl + a real Chrome tab: "Failed to fetch").
 *  Strategy, in order: VITE_ADSB_URL if set (e.g. your own Cloudflare Worker, see web/worker/), then the direct URL (in case
 *  CORS gets enabled upstream), then the public CORS proxy api.cors.lol. Whichever works is kept; polling is gentle (8 s)
 *  and positions are dead-reckoned between polls so the planes glide. */
import { HKIA, haversineNm } from './geo'

export const RADIUS_NM = 100
export const DIRECT_URL = `https://api.adsb.lol/v2/lat/${HKIA.lat}/lon/${HKIA.lon}/dist/${RADIUS_NM}`
export const PROXY_URL = `https://api.cors.lol/?url=${encodeURIComponent(DIRECT_URL)}`
export const POLL_MS = 8000

export interface Aircraft {
  hex: string
  callsign: string
  lat: number
  lon: number
  altFt: number
  onGround: boolean
  gsKt: number | null
  trackDeg: number | null
  type: string
  reg: string
  distNm: number
  seenAt: number
  /** ms epoch of the position report (now - seen_pos) */
  posAt: number
}

interface RawAc {
  hex?: string
  flight?: string
  lat?: number
  lon?: number
  alt_baro?: number | string
  gs?: number
  track?: number
  t?: string
  r?: string
  dst?: number
  seen_pos?: number
}

export function normalise(raw: { ac?: RawAc[]; now?: number }, fetchedAt = Date.now()): Aircraft[] {
  const out: Aircraft[] = []
  for (const a of raw.ac ?? []) {
    if (typeof a.lat !== 'number' || typeof a.lon !== 'number' || !a.hex) continue
    const onGround = String(a.alt_baro).toLowerCase() === 'ground'
    const alt = typeof a.alt_baro === 'number' ? Math.max(a.alt_baro, 0) : 0
    out.push({
      hex: a.hex,
      callsign: (a.flight ?? '').trim().toUpperCase(),
      lat: a.lat,
      lon: a.lon,
      altFt: alt,
      onGround,
      gsKt: typeof a.gs === 'number' ? a.gs : null,
      trackDeg: typeof a.track === 'number' ? a.track : null,
      type: a.t ?? '',
      reg: a.r ?? '',
      distNm: typeof a.dst === 'number' ? a.dst : haversineNm(HKIA.lat, HKIA.lon, a.lat, a.lon),
      seenAt: fetchedAt,
      posAt: fetchedAt - (typeof a.seen_pos === 'number' ? a.seen_pos * 1000 : 0),
    })
  }
  return out
}

export type FeedRoute = 'env' | 'direct' | 'proxy'

const ENV_URL = (import.meta.env.VITE_ADSB_URL as string | undefined) || ''
const ROUTES: { route: FeedRoute; url: string }[] = [
  ...(ENV_URL ? [{ route: 'env' as const, url: ENV_URL }] : []),
  { route: 'direct' as const, url: DIRECT_URL },
  { route: 'proxy' as const, url: PROXY_URL },
]
let sticky = 0

export interface FeedResult {
  aircraft: Aircraft[]
  route: FeedRoute
  fetchedAt: number
}

/** Try the routes in order starting from the last one that worked; throws if all fail. */
export async function fetchAircraft(fetcher: typeof fetch = fetch, timeoutMs = 7000): Promise<FeedResult> {
  let lastErr: unknown = null
  for (let k = 0; k < ROUTES.length; k++) {
    const i = (sticky + k) % ROUTES.length
    const { route, url } = ROUTES[i]
    const ctl = new AbortController()
    const timer = setTimeout(() => ctl.abort(), timeoutMs)
    try {
      const r = await fetcher(url, { signal: ctl.signal, headers: { Accept: 'application/json' } })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const js = (await r.json()) as { ac?: RawAc[] }
      if (!Array.isArray(js.ac)) throw new Error('unexpected payload')
      sticky = i
      const fetchedAt = Date.now()
      return { aircraft: normalise(js, fetchedAt), route, fetchedAt }
    } catch (e) {
      lastErr = e
    } finally {
      clearTimeout(timer)
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error('feed unavailable')
}
