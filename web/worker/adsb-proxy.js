// Cloudflare Worker relay for the live map: adds CORS and falls back across free ADS-B feeds, always returning the
// readsb-style {ac: [...]} shape the web app expects. Deploy: `cd web/worker && npx wrangler login && npx wrangler deploy`
// (free plan: 100k req/day). Then set repo variable ADSB_PROXY_URL=https://hkia-adsb-proxy.<you>.workers.dev/ and
// re-run pages.yml. Responses are cached at the edge for 8 s so many viewers share one upstream call.
const HKIA = { lat: 22.308, lon: 113.918 }
const READSB = [
  'https://api.adsb.lol/v2/lat/22.308/lon/113.918/dist/100',
  'https://opendata.adsb.fi/api/v2/lat/22.308/lon/113.918/dist/100',
  'https://api.airplanes.live/v2/point/22.308/113.918/100',
]
const OPENSKY = 'https://opensky-network.org/api/states/all?lamin=20.6&lomin=112.1&lamax=24.0&lomax=115.7'
const ALLOW_ORIGIN = '*'
const UA = 'hkia-delay-predictor (github.com/dsjwong/hkia-delay-predictor)'

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') return new Response(null, { headers: cors() })
    const cache = caches.default
    const key = new Request('https://hkia-adsb-proxy.cache/feed', request)
    const hit = await cache.match(key)
    if (hit) return hit

    let payload = null
    for (const url of READSB) {
      try {
        const r = await fetch(url, { headers: { 'User-Agent': UA }, signal: AbortSignal.timeout(6000) })
        if (!r.ok) continue
        const js = await r.json()
        if (Array.isArray(js.ac) && js.ac.length > 0) { payload = { ac: js.ac, provider: new URL(url).host, now: Date.now() }; break }
      } catch { /* try next */ }
    }
    if (!payload) {
      try {
        const r = await fetch(OPENSKY, { headers: { 'User-Agent': UA }, signal: AbortSignal.timeout(8000) })
        if (r.ok) {
          const js = await r.json()
          const ac = (js.states || []).filter(s => s[5] != null && s[6] != null).map(s => ({
            hex: s[0], flight: (s[1] || '').trim(), lat: s[6], lon: s[5],
            alt_baro: s[8] ? 'ground' : Math.round((s[7] ?? s[13] ?? 0) * 3.28084),
            gs: s[9] != null ? +(s[9] * 1.94384).toFixed(1) : null, track: s[10], r: null, t: null,
            dst: +distNm(s[6], s[5]).toFixed(1),
          })).filter(a => a.dst <= 100)
          payload = { ac, provider: 'opensky-network.org', now: Date.now() }
        }
      } catch { /* fall through */ }
    }
    if (!payload) payload = { ac: [], provider: 'none', now: Date.now(), degraded: true }

    const res = new Response(JSON.stringify(payload), {
      status: 200,
      headers: { ...cors(), 'content-type': 'application/json', 'cache-control': 'public, max-age=8' },
    })
    ctx.waitUntil(cache.put(key, res.clone()))
    return res
  },
}

function distNm(lat, lon) {
  const R = 3440.065, toR = Math.PI / 180
  const dLat = (lat - HKIA.lat) * toR, dLon = (lon - HKIA.lon) * toR
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(HKIA.lat * toR) * Math.cos(lat * toR) * Math.sin(dLon / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(a))
}

function cors() {
  return { 'access-control-allow-origin': ALLOW_ORIGIN, 'access-control-allow-methods': 'GET, OPTIONS', 'access-control-max-age': '86400' }
}
