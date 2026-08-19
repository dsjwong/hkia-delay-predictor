import { REPO } from '@/components/Header'

const STEPS = [
  'GitHub Actions cron (ingest.yml, every 30 min, $0) checks out this repo.',
  "hkia.ingest_flights pulls yesterday/today/tomorrow's departures from the Airport Authority flight-info API on data.gov.hk (scheduled vs actual = the label).",
  'hkia.ingest_weather pulls the latest VHHH METAR (aviationweather.gov) and HKO current readings + warnings (typhoon signals) into SQLite data/hkia.db.',
  'hkia.features builds the same 33 features for training and inference (calendar, airline/destination, congestion, as-of weather, point-in-time rolling delays).',
  'hkia.train (offline, occasionally) fits baselines + XGBoost on a date-ordered split → models/, reports/M2-results.md.',
  'hkia.predict (every cron run) scores every not-yet-departed flight for today + tomorrow → table predictions (history kept).',
  'hkia.export_json writes compact JSON snapshots (meta, departures, patterns, model, weather; ~600 KB) to web/public/data/.',
  'A daily job (backfill.yml) tops up METAR history (IEM) + typhoon-signal history and runs hkia.evaluate (last score before departure vs actual).',
  'The bot commits data/hkia.db + the JSON back to main — the repo is the data store.',
  'This page is a static React app on GitHub Pages: it reads the JSON straight from raw.githubusercontent.com/main (no backend, no rebuild for fresh data) and the live aircraft from adsb.lol in your browser. The Streamlit dashboard (hkia-delays.streamlit.app) reads the same db and stays up as a fallback.',
]

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-base font-semibold tracking-tight text-ink">{title}</h3>
      <div className="text-sm text-ink-2 leading-relaxed">{children}</div>
    </section>
  )
}

export default function About() {
  return (
    <div className="max-w-[820px] space-y-8">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">About</h2>
        <p className="mt-2 text-sm text-ink-2 leading-relaxed">
          <b className="text-ink">What</b> — for every HKIA passenger departure, the probability it leaves more than 15
          min late and the expected delay in minutes, from live schedule + weather data, with an honest evaluation page.
          Departures only (v1).
        </p>
      </div>

      <Section title="Architecture (10 lines)">
        <ol className="grid grid-cols-[2ch_1fr] gap-x-3 gap-y-2">
          {STEPS.map((s, i) => (
            <li key={i} className="contents">
              <span className="hk-num text-muted text-right" aria-hidden="true">
                {i + 1}
              </span>
              <span>{s}</span>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="Live map">
        <p>
          Every aircraft within 100 nm of VHHH from the free <a href="https://adsb.lol">adsb.lol</a> community ADS-B
          feed, polled from your browser every 8 s and dead-reckoned in between so the icons glide. Aircraft whose
          callsign matches a flight number in today's / yesterday's HKIA departure schedule (ICAO airline code + number,
          CPA261 ↔ CX 261) are highlighted on the amber ramp by their latest P(delay &gt; 15); click one (or a row in
          the side list) for the flight card. The API does not send CORS headers, so the page goes through a public CORS
          proxy (api.cors.lol) unless the site is built with its own proxy URL — see the README. ADS-B is display only,
          not a model input.
        </p>
      </Section>

      <Section title="Data sources">
        <ul className="list-disc pl-5 space-y-1.5">
          <li>
            <a href="https://data.gov.hk/en-data/dataset/aahk-team1-flight-info">
              HKIA flight information — data.gov.hk / Airport Authority
            </a>{' '}
            (real-time + ~91-day history)
          </li>
          <li>
            <a href="https://data.gov.hk/en-data/dataset/hk-hko-rss-current-weather-report">
              Hong Kong Observatory Open Data API
            </a>{' '}
            (current readings, warnings, TC signals) and the{' '}
            <a href="https://www.hko.gov.hk/en/wxinfo/climat/warndb/warndb1.shtml">HKO warning database</a>
          </li>
          <li>
            <a href="https://aviationweather.gov/data/api/">aviationweather.gov METAR</a> for VHHH; historical METAR
            from the <a href="https://mesonet.agron.iastate.edu/request/download.phtml">IEM ASOS archive</a>
          </li>
          <li>
            <a href="https://adsb.lol">adsb.lol</a> live ADS-B positions for the map (community feed, free, no key);
            basemap © <a href="https://carto.com/attributions">CARTO</a> © OpenStreetMap contributors
          </li>
        </ul>
      </Section>

      <Section title="Code">
        <p>
          <a href={REPO}>{REPO.replace('https://', '')}</a> · README has the run book,{' '}
          <code className="font-mono text-xs bg-elev px-1 rounded">reports/M2-results.md</code> the numbers,{' '}
          <code className="font-mono text-xs bg-elev px-1 rounded">docs/features.md</code> the feature dictionary,{' '}
          <code className="font-mono text-xs bg-elev px-1 rounded">web/</code> this app.
        </p>
      </Section>

      <Section title="Author">
        <p>
          Darren Wong, HKUST CS + AI. Built as a genuine-interest aviation + ML project and an ML-engineering showcase.
        </p>
      </Section>
    </div>
  )
}
