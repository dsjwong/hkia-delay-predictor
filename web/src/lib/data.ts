/** JSON loaders. The snapshots are committed to web/public/data/ by the GitHub Actions cron every ~30 min.
 *  In production the app reads them from raw.githubusercontent.com/main (CORS *, max-age 300) so the Pages build never has
 *  to be redone for fresh data; the copy bundled under <base>/data/ is the fallback (and the source in dev). */
import { useEffect, useState } from 'react'
import type { Departures, Meta, ModelJson, Patterns, Weather } from './types'

const RAW_BASE = 'https://raw.githubusercontent.com/dsjwong/hkia-delay-predictor/main/web/public/data/'
const LOCAL_BASE = `${import.meta.env.BASE_URL}data/`
const OVERRIDE = import.meta.env.VITE_DATA_BASE as string | undefined

export function dataBases(): string[] {
  if (OVERRIDE) return [OVERRIDE.endsWith('/') ? OVERRIDE : OVERRIDE + '/', LOCAL_BASE]
  if (import.meta.env.DEV || import.meta.env.MODE === 'test') return [LOCAL_BASE]
  return [RAW_BASE, LOCAL_BASE]
}

/** 5-minute cache-bust bucket so the raw CDN (max-age 300) never serves a stale copy for longer than its own TTL. */
function bucket(now = Date.now()): string {
  return String(Math.floor(now / 300000))
}

export async function fetchJson<T>(name: string, fetcher: typeof fetch = fetch): Promise<{ data: T; source: string }> {
  let lastErr: unknown = null
  for (const base of dataBases()) {
    try {
      const r = await fetcher(`${base}${name}?v=${bucket()}`, { cache: 'no-cache' })
      if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`)
      return { data: (await r.json()) as T, source: base }
    } catch (e) {
      lastErr = e
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error(`failed to load ${name}`)
}

interface Entry<T> {
  at: number
  promise: Promise<T>
}
const cache = new Map<string, Entry<unknown>>()
const TTL_MS = 5 * 60 * 1000

export function loadJson<T>(name: string, force = false): Promise<T> {
  const hit = cache.get(name) as Entry<T> | undefined
  if (hit && !force && Date.now() - hit.at < TTL_MS) return hit.promise
  const promise = fetchJson<T>(name).then((x) => x.data)
  cache.set(name, { at: Date.now(), promise })
  promise.catch(() => cache.delete(name))
  return promise
}

export interface Loaded<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

/** Load one JSON file; re-fetches every `refreshMs` (default 5 min) while mounted. */
export function useJson<T>(name: string, refreshMs = TTL_MS): Loaded<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let alive = true
    setLoading(true)
    loadJson<T>(name, tick > 0)
      .then((d) => {
        if (!alive) return
        setData(d)
        setError(null)
      })
      .catch((e: unknown) => alive && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => alive && setLoading(false))
    const id = refreshMs > 0 ? window.setInterval(() => setTick((t) => t + 1), refreshMs) : 0
    return () => {
      alive = false
      if (id) window.clearInterval(id)
    }
  }, [name, tick, refreshMs])
  return { data, error, loading, reload: () => setTick((t) => t + 1) }
}

export const useMeta = () => useJson<Meta>('meta.json')
export const useWeather = () => useJson<Weather>('weather.json')
export const usePatterns = () => useJson<Patterns>('patterns.json', 0)
export const useModel = () => useJson<ModelJson>('model.json', 0)
export const useDepartures = (which: 'yesterday' | 'today' | 'tomorrow') =>
  useJson<Departures>(`departures_${which}.json`)

export function airlineName(meta: Meta | null, code: string | null | undefined): string {
  if (!code) return '?'
  return meta?.airlines[code] ?? code
}
export function destLabel(meta: Meta | null, code: string | null | undefined): string {
  if (!code) return '—'
  const a = meta?.airports[code]
  return a && a.city !== code ? `${a.city} (${code})` : code
}
