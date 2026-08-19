// Optional: a 20-line Cloudflare Worker that adds CORS to the adsb.lol feed, so the web app does not depend on a public
// CORS proxy. Deploy with `npx wrangler deploy` (free plan: 100k requests/day is plenty for a few viewers polling every 8 s),
// then build the site with VITE_ADSB_URL=https://<your-worker>.workers.dev/ (or set it as a repository variable and pass it
// in pages.yml). Restrict ALLOW_ORIGIN to your Pages origin if you like.
const UPSTREAM = 'https://api.adsb.lol/v2/lat/22.308/lon/113.918/dist/100'
const ALLOW_ORIGIN = '*'

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: cors() })
    }
    const r = await fetch(UPSTREAM, {
      headers: { 'User-Agent': 'hkia-delay-predictor (github.com/dsjwong/hkia-delay-predictor)' },
      cf: { cacheTtl: 4, cacheEverything: true },
    })
    return new Response(r.body, { status: r.status, headers: { ...cors(), 'content-type': 'application/json', 'cache-control': 'no-store' } })
  },
}

function cors() {
  return { 'access-control-allow-origin': ALLOW_ORIGIN, 'access-control-allow-methods': 'GET, OPTIONS', 'access-control-max-age': '86400' }
}
