import { describe, expect, it, vi, afterEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import Typhoon from './Typhoon'
import { clearJsonCache } from '@/lib/data'
import { signalRuns, hourLabel } from '@/charts/CaseCharts'
import type { CaseHour, CaseStudy } from '@/lib/types'

const hour = (t: string, signal: number, over: Partial<CaseHour> = {}): CaseHour => ({
  t,
  signal,
  n_sched: 20,
  n_departed: 18,
  n_cancelled: 2,
  n_labelled: 18,
  mean_delay: 12,
  p90_delay: 30,
  max_delay: 60,
  wspd_kt: 10,
  wgst_kt: 0,
  visib_sm: 6.21,
  flt_cat: 'VFR',
  wx: null,
  ...over,
})

const HOURS: CaseHour[] = [
  hour('2026-07-25T21:00:00+08:00', 3),
  hour('2026-07-25T22:00:00+08:00', 8, { mean_delay: 34 }),
  hour('2026-07-25T23:00:00+08:00', 8, { mean_delay: 28 }),
  hour('2026-07-26T01:00:00+08:00', 9, { mean_delay: 8, n_cancelled: 8, n_departed: 2 }),
  hour('2026-07-26T08:00:00+08:00', 8, { mean_delay: 267, n_cancelled: 28, n_departed: 11, wgst_kt: 45 }),
  hour('2026-07-26T20:00:00+08:00', 0, { mean_delay: 56 }),
]

const totals = (signal: number, n: number, cancelled: number, mean: number) => ({
  signal,
  n,
  n_cancelled: cancelled,
  cancel_rate: cancelled / n,
  n_labelled: n - cancelled,
  n_over_clip: 1,
  mean_delay: mean,
  median_delay: mean - 5,
  p90_delay: mean * 2,
  pct15: 0.6,
})

const CASE: CaseStudy = {
  generated_at: '2026-08-20T16:33:07+08:00',
  regenerate: 'python -m hkia.case_study',
  static: true,
  note: 'One-off artefact.',
  episode: {
    tc_id: '202602',
    name: 'NOUL',
    peak_signal: 9,
    first_signal: '2026-07-24T20:40:00+08:00',
    all_clear: '2026-07-26T19:10:00+08:00',
    sequence: 'T1→T3→T8→T9→T8→T3→T1',
    signals: [
      { signal: 1, direction: null, start: '2026-07-24T20:40:00+08:00', end: '2026-07-25T13:20:00+08:00', hours: 16.7 },
      { signal: 9, direction: null, start: '2026-07-26T01:10:00+08:00', end: '2026-07-26T07:10:00+08:00', hours: 6 },
    ],
  },
  window: {
    start: '2026-07-23T00:00:00+08:00',
    end: '2026-07-28T00:00:00+08:00',
    tz: 'Asia/Hong_Kong',
    days: ['2026-07-23', '2026-07-24', '2026-07-25', '2026-07-26', '2026-07-27'],
  },
  other_episodes: [
    {
      tc_id: '202601',
      name: 'MAYSAK',
      peak_signal: 1,
      start: '2026-07-02T07:40:00+08:00',
      end: '2026-07-04T03:20:00+08:00',
      kind: 'tc',
    },
  ],
  other_monsoon: { n: 4, date_min: '2026-05-16', date_max: '2026-07-14' },
  headline: {
    peak_signal: 9,
    n_flights_window: 2274,
    n_flights_episode: 1366,
    n_cancelled_episode: 216,
    cancel_rate_episode: 0.1581,
    peak_hour: '2026-07-26T08:00:00+08:00',
    peak_hour_mean_delay: 267.2,
    peak_hour_n: 11,
    peak_gust_kt: 45,
    min_visib_sm: 1.93,
    hours_to_recover: 6.8,
    n_hours_no_departures: 14,
  },
  hourly: HOURS,
  by_signal: [totals(0, 1401, 27, 20.8), totals(3, 285, 61, 50), totals(8, 201, 111, 123.1), totals(9, 21, 13, 255.8)],
  baseline: {
    label: 'no TC signal in force',
    date_min: '2026-05-16',
    date_max: '2026-08-21',
    n_days: 96,
    ...totals(0, 40511, 300, 15.93),
  },
  worst_flights: [
    {
      flight_no: 'VJ 985',
      airline: 'VJC',
      airline_name: 'VietJet',
      dest: 'PQC',
      dest_city: 'Phu Quoc',
      sched_ts: '2026-07-25T16:40:00+08:00',
      actual_ts: '2026-07-26T20:56:00+08:00',
      delay_min: 1696,
      signal: 3,
      over_clip: true,
    },
  ],
  cancellations: {
    total: 226,
    by_airline: [{ airline: 'CPA', name: 'Cathay Pacific', n_cancelled: 134, n_sched: 896, rate: 0.15 }],
    by_dest: [{ dest: 'TPE', city: 'Taipei Taoyuan', n_cancelled: 12 }],
    by_day: [{ date: '2026-07-26', n_sched: 451, n_cancelled: 178, rate: 0.395 }],
  },
  recovery: {
    all_clear_ts: '2026-07-26T19:10:00+08:00',
    recovered_at: '2026-07-27T02:00:00+08:00',
    hours_to_recover: 6.8,
    baseline_mean_delay: 15.9,
    min_n: 5,
    rule: 'first clock hour after the all-clear with >= 5 departed flights at or below the baseline',
  },
  retrospective: {
    in_sample: true,
    split_containing_episode: 'val',
    val_dates: ['2026-07-20', '2026-08-02'],
    model_version: '2e00760@2026-08-16T16:13:29+00:00',
    live_scoring_began: '2026-08-17',
    flag_threshold: 0.5,
    note: 'In-sample. Live scoring began 2026-08-17.',
    overall: {
      n: 2030,
      obs_rate: 0.417,
      mean_p: 0.365,
      pct_flagged: 0.268,
      auc: 0.7726,
      brier: 0.1938,
      mae: 26.8,
      mean_pred_delay: 14.3,
      mean_obs_delay: 32.1,
    },
    by_signal: [
      {
        signal: 8,
        n: 84,
        obs_rate: 0.714,
        mean_p: 0.594,
        pct_flagged: 0.714,
        auc: 0.624,
        brier: 0.213,
        mae: 96,
        mean_pred_delay: 28.4,
        mean_obs_delay: 123.1,
      },
      {
        signal: 9,
        n: 5,
        obs_rate: 0.6,
        mean_p: 0.319,
        pct_flagged: 0,
        auc: 0.5,
        brier: 0.32,
        mae: 245,
        mean_pred_delay: 10.8,
        mean_obs_delay: 255.8,
      },
    ],
    hourly: [],
  },
  clip: { min: -60, max: 600, note: 'delays outside [-60, 600] min are excluded from every average' },
  sources: { flights: 'data.gov.hk', weather: 'IEM ASOS archive', signals: 'HKO warning database' },
}

function stubFetch(body: unknown, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  clearJsonCache() // the loader memoises per file name; each case stubs its own response for case_noul.json
})

describe('signalRuns', () => {
  it('collapses contiguous hours into one band per level and drops the no-signal runs', () => {
    const runs = signalRuns(HOURS)
    expect(runs.map((r) => r.signal)).toEqual([3, 8, 9, 8])
    expect(runs[1]).toMatchObject({
      signal: 8,
      from: '2026-07-25T22:00:00+08:00',
      to: '2026-07-25T23:00:00+08:00',
      n: 2,
    })
    expect(runs.every((r) => r.signal > 0)).toBe(true)
  })

  it('labels an hour as day + HH:MM in HKT without a timezone round-trip', () => {
    expect(hourLabel('2026-07-26T08:00:00+08:00')).toBe('26 08:00')
  })
})

describe('Typhoon case study page', () => {
  it('renders the headline tiles and the story numbers', async () => {
    stubFetch(CASE)
    render(<Typhoon />)
    expect(await screen.findByText(/Case study — Typhoon Noul/)).toBeInTheDocument()
    const tile = (label: string) => screen.getByText(label).closest('.hk-card') as HTMLElement
    expect(within(tile('Peak signal')).getByText('No. 9')).toBeInTheDocument()
    expect(within(tile('Departures cancelled')).getByText('216')).toBeInTheDocument()
    expect(within(tile('Departures cancelled')).getByText(/15.8 % of 1,366/)).toBeInTheDocument()
    expect(within(tile('Peak hourly mean delay')).getByText('267 min')).toBeInTheDocument()
    expect(within(tile('Hours to recover')).getByText('7 h')).toBeInTheDocument()
    // the worst-flights table shows the uncapped delay
    expect(screen.getByText('VJ 985')).toBeInTheDocument()
    expect(screen.getByText('1,696')).toBeInTheDocument()
    // the other in-window episodes are named rather than implied away
    expect(screen.getByText(/Typhoon MAYSAK/)).toBeInTheDocument()
    expect(screen.getByText(/4 strong-monsoon episodes/)).toBeInTheDocument()
  })

  it('carries the in-sample flag in the UI, not only in the prose', async () => {
    stubFetch(CASE)
    render(<Typhoon />)
    expect(await screen.findByRole('note')).toHaveTextContent(/No prediction was published for these flights/)
    expect(screen.getByRole('note')).toHaveTextContent(/validation split/)
    expect(screen.getByText('in-sample — illustration only')).toBeInTheDocument()
    // and the retrospective table pairs predicted with observed so the under-call is visible
    const retro = screen.getByText('in-sample — illustration only').closest('.hk-card') as HTMLElement
    expect(within(retro).getByText('28')).toBeInTheDocument()
    expect(within(retro).getByText('123')).toBeInTheDocument()
    // a 5-flight slice is labelled thin instead of showing an AUC
    expect(within(retro).getByText('thin, n=5')).toBeInTheDocument()
  })

  it('shows an error state when the static artefact is missing', async () => {
    stubFetch({}, 404)
    render(<Typhoon />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/Could not load case_noul.json/)
    expect(screen.getByRole('alert')).toHaveTextContent(/hkia.case_study/)
  })

  it('renders a skeleton before the fetch resolves', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise(() => {})),
    )
    render(<Typhoon />)
    expect(screen.getAllByRole('status').length).toBeGreaterThan(0)
  })
})
