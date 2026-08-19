import { lazy, Suspense } from 'react'
import { HashRouter, Route, Routes } from 'react-router-dom'
import { Header } from './components/Header'
import { MetaProvider } from './lib/meta-context'

const Live = lazy(() => import('./pages/Live'))
const Today = lazy(() => import('./pages/Today'))
const Patterns = lazy(() => import('./pages/Patterns'))
const Model = lazy(() => import('./pages/Model'))
const About = lazy(() => import('./pages/About'))

function Fallback() {
  return (
    <div className="p-6 text-sm text-muted" role="status">
      Loading…
    </div>
  )
}

export default function App() {
  return (
    <HashRouter>
      <MetaProvider>
        <div className="min-h-full flex flex-col">
          <Header />
          <main className="flex-1 mx-auto w-full max-w-[1600px] px-3 sm:px-4 py-3">
            <Suspense fallback={<Fallback />}>
              <Routes>
                <Route path="/" element={<Live />} />
                <Route path="/today" element={<Today />} />
                <Route path="/patterns" element={<Patterns />} />
                <Route path="/model" element={<Model />} />
                <Route path="/about" element={<About />} />
                <Route path="*" element={<Live />} />
              </Routes>
            </Suspense>
          </main>
          <footer className="mx-auto w-full max-w-[1600px] px-4 py-3 text-[0.7rem] text-muted border-t border-border">
            Data: Airport Authority HK flight info (data.gov.hk), Hong Kong Observatory, aviationweather.gov METAR · live aircraft:{' '}
            <a href="https://adsb.lol">adsb.lol</a> community ADS-B (display only, not a model input) · basemap ©{' '}
            <a href="https://carto.com/attributions">CARTO</a> © OpenStreetMap contributors · predictions are probabilities, not promises.
          </footer>
        </div>
      </MetaProvider>
    </HashRouter>
  )
}
