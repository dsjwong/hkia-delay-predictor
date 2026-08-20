import { lazy, Suspense } from 'react'
import { HashRouter, Route, Routes, useLocation } from 'react-router-dom'
import { BottomTabs, Header } from './components/Header'
import { ErrorBoundary } from './components/ErrorBoundary'
import { MetaProvider } from './lib/meta-context'
import { Skeleton } from './components/ui/skeleton'
import { cn } from './lib/utils'

const Live = lazy(() => import('./pages/Live'))
const Today = lazy(() => import('./pages/Today'))
const Patterns = lazy(() => import('./pages/Patterns'))
const Model = lazy(() => import('./pages/Model'))
const Typhoon = lazy(() => import('./pages/Typhoon'))
const About = lazy(() => import('./pages/About'))

function Fallback() {
  return (
    <div className="p-4 space-y-3" role="status" aria-label="loading page">
      <Skeleton className="h-6 w-56" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
      <Skeleton className="h-64" />
    </div>
  )
}

function Shell() {
  const { pathname } = useLocation()
  const isMap = pathname === '/' || !['/today', '/patterns', '/model', '/typhoon', '/about'].includes(pathname)
  return (
    <div className="min-h-full flex flex-col">
      <Header />
      <main
        className={cn('flex-1 w-full pb-14 md:pb-0', isMap ? 'relative' : 'mx-auto max-w-[1400px] px-4 sm:px-6 py-5')}
      >
        <ErrorBoundary>
          <Suspense fallback={<Fallback />}>
            <Routes>
              <Route path="/" element={<Live />} />
              <Route path="/today" element={<Today />} />
              <Route path="/patterns" element={<Patterns />} />
              <Route path="/model" element={<Model />} />
              <Route path="/typhoon" element={<Typhoon />} />
              <Route path="/about" element={<About />} />
              <Route path="*" element={<Live />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </main>
      {!isMap && (
        <footer className="mx-auto w-full max-w-[1400px] px-4 sm:px-6 py-4 text-[0.7rem] text-muted border-t border-border leading-relaxed">
          Data: Airport Authority HK flight info (data.gov.hk), Hong Kong Observatory, aviationweather.gov METAR · live
          aircraft: <a href="https://adsb.lol">adsb.lol</a> community ADS-B (display only, not a model input) · basemap
          © <a href="https://carto.com/attributions">CARTO</a> © OpenStreetMap contributors · predictions are
          probabilities, not promises.
        </footer>
      )}
      <BottomTabs />
    </div>
  )
}

export default function App() {
  return (
    <HashRouter>
      <MetaProvider>
        <Shell />
      </MetaProvider>
    </HashRouter>
  )
}
