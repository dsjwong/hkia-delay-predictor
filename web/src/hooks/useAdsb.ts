import { useEffect, useRef, useState } from 'react'
import { fetchAircraft, POLL_MS, type Aircraft, type FeedRoute } from '@/lib/adsb'

export interface AdsbState {
  aircraft: Aircraft[]
  route: FeedRoute | null
  fetchedAt: number | null
  error: string | null
  /** consecutive failures */
  failures: number
}

/** Poll the feed every POLL_MS while the tab is visible; keep the last good frame on errors. */
export function useAdsb(enabled = true): AdsbState {
  const [st, setSt] = useState<AdsbState>({ aircraft: [], route: null, fetchedAt: null, error: null, failures: 0 })
  const busy = useRef(false)
  useEffect(() => {
    if (!enabled) return
    let alive = true
    const tick = async () => {
      if (busy.current || document.hidden) return
      busy.current = true
      try {
        const r = await fetchAircraft()
        if (alive) setSt({ aircraft: r.aircraft, route: r.route, fetchedAt: r.fetchedAt, error: null, failures: 0 })
      } catch (e) {
        if (alive) setSt((s) => ({ ...s, error: e instanceof Error ? e.message : String(e), failures: s.failures + 1 }))
      } finally {
        busy.current = false
      }
    }
    void tick()
    const id = window.setInterval(tick, POLL_MS)
    const onVis = () => !document.hidden && void tick()
    document.addEventListener('visibilitychange', onVis)
    return () => {
      alive = false
      window.clearInterval(id)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [enabled])
  return st
}
