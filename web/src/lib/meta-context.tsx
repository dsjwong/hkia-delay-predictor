import { createContext, useContext, type ReactNode } from 'react'
import { useMeta, useWeather, type Loaded } from './data'
import type { Meta, Weather } from './types'

interface Ctx {
  meta: Loaded<Meta>
  weather: Loaded<Weather>
}
const C = createContext<Ctx | null>(null)

export function MetaProvider({ children }: { children: ReactNode }) {
  const meta = useMeta()
  const weather = useWeather()
  return <C.Provider value={{ meta, weather }}>{children}</C.Provider>
}

export function useMetaCtx(): Ctx {
  const v = useContext(C)
  if (!v) throw new Error('MetaProvider missing')
  return v
}
