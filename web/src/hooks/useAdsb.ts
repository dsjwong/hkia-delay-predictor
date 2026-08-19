import { useEffect, useRef, useState } from 'react'
import { fetchAircraft, pollInterval, type Aircraft, type FeedRoute } from '@/lib/adsb'

export interface AdsbState {
  aircraft: Aircraft[]
  route: FeedRoute | null
  fetchedAt: number | null
  error: string | null
  /** consecutive failures */
  failures: number
}

/** Poll the feed while the tab is visible (interval depends on the route that works: 8 s direct/relay, 60 s public proxy,
 *  exponential backoff up to 2 min on repeated failures); keep the last good frame on errors. */
export function useAdsb(enabled = true): AdsbState {
  const [st, setSt] = useState<AdsbState>({ aircraft: [], route: null, fetchedAt: null, error: null, failures: 0 })
  const busy = useRef(false)
  const timer = useRef(0)
  useEffect(() => {
    if (!enabled) return
    let alive = true
    let route: FeedRoute | null = null
    let failures = 0
    const schedule = (ms: number) => {
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => void tick(), ms)
    }
    const tick = async () => {
      if (!alive) return
      if (busy.current || document.hidden) return schedule(2000)
      busy.current = true
      try {
        const r = await fetchAircraft()
        route = r.route
        failures = 0
        if (alive) setSt({ aircraft: r.aircraft, route: r.route, fetchedAt: r.fetchedAt, error: null, failures: 0 })
      } catch (e) {
        failures += 1
        if (alive) setSt((s) => ({ ...s, error: e instanceof Error ? e.message : String(e), failures: s.failures + 1 }))
      } finally {
        busy.current = false
      }
      const base = pollInterval(route)
      schedule(failures ? Math.min(base * 2 ** Math.min(failures, 4), 120000) : base)
    }
    void tick()
    const onVis = () => !document.hidden && schedule(0)
    document.addEventListener('visibilitychange', onVis)
    return () => {
      alive = false
      window.clearTimeout(timer.current)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [enabled])
  return st
}
