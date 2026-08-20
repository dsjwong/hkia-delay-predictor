import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ReportCard, beatsBaselineText } from './ReportCard'
import type { LiveEval } from '@/lib/types'

const slice = (auc: number | null, brier = 0.17, mae = 14.5) => ({ auc, brier, mae })

const EV: LiveEval = {
  window_days: 7,
  n_matured: 1402,
  min_n: 100,
  min_slice_n: 20,
  status: 'ok',
  computed_at: '2026-08-20T06:32:39+00:00',
  date_min: '2026-08-17',
  date_max: '2026-08-20',
  delayed15_rate: 0.2375,
  median_lead_min: 25.6,
  model: { auc: 0.6635, brier: 0.1681, logloss: 0.5148, mae: 14.571 },
  baseline_airline_hour: { auc: 0.6466, brier: 0.1734, logloss: 0.5271, mae: 17.4 },
  naive_rate: { auc: 0.5, brier: 0.1811, logloss: 0.5482, mae: 15.003 },
  median_horizon_min: 18,
  coverage: { n_departed: 1562, n_scored: 1402, pct: 0.8976 },
  deltas: { auc: 0.0169, brier: -0.0053, logloss: -0.0123, mae: -2.829 },
  bootstrap: {
    n_boot: 2000,
    // the real numbers: only MAE clears zero, the AUC margin does not
    ci: { auc: [-0.0127, 0.0487], brier: [-0.0107, 0.0002], logloss: [-0.0262, 0.0023], mae: [-3.2792, -2.3981] },
    beats_baseline: { auc: false, brier: false, logloss: false, mae: true },
  },
  cal_min_n: 30,
  daily: [
    {
      date: '2026-08-17',
      n: 293,
      delayed15_rate: 0.2287,
      thin: false,
      partial: true,
      model: slice(0.5923),
      baseline: slice(0.5372),
    },
    { date: '2026-08-18', n: 440, delayed15_rate: 0.2386, thin: false, model: slice(0.7012), baseline: slice(0.6549) },
  ],
  lead_buckets: [
    {
      label: '< 30 min',
      lo_min: 0,
      hi_min: 30,
      n: 705,
      thin: false,
      delayed15_rate: 0.156,
      median_horizon_min: 12,
      median_lead_min: 18,
      model: slice(0.6974),
      baseline: slice(0.6718),
    },
    {
      label: '> 12 h',
      lo_min: 720,
      hi_min: null,
      n: 0,
      thin: true,
      delayed15_rate: null,
      median_horizon_min: null,
      median_lead_min: null,
      model: slice(null),
    },
  ],
  calibration: [
    { bin: '0.0-0.1', n: 204, thin: false, pred_mean: 0.071, obs_rate: 0.098 },
    { bin: '0.8-0.9', n: 6, thin: true, pred_mean: 0.843, obs_rate: 1.0 },
  ],
  notable: {
    confident_correct: [
      {
        flight_no: 'RA 410',
        date: '2026-08-18',
        airline: 'RNA',
        dest: 'KTM',
        p: 0.88,
        pred_min: 59.3,
        delay_min: 235,
        delayed15: 1,
        lead_min: 20,
      },
    ],
    worst_misses: [
      {
        flight_no: 'UO 616',
        date: '2026-08-18',
        airline: 'HKE',
        dest: 'ICN',
        p: 0.03,
        pred_min: -4.1,
        delay_min: 147,
        delayed15: 1,
        lead_min: 25,
      },
      {
        flight_no: 'OD 606',
        date: '2026-08-18',
        airline: 'MXD',
        dest: 'KUL',
        p: 0.79,
        pred_min: 65.1,
        delay_min: 0,
        delayed15: 0,
        lead_min: 12,
      },
    ],
    high_confidence: { threshold: 0.7, n: 14, n_late: 9, rate: 0.643 },
  },
}

describe('ReportCard', () => {
  it('leads with the live headline numbers and the baseline delta', () => {
    render(<ReportCard ev={EV} />)
    expect(screen.getByText('AUC (live)')).toBeInTheDocument()
    expect(screen.getByText('0.663')).toBeInTheDocument()
    expect(screen.getByText('+0.017')).toBeInTheDocument()
    expect(screen.getByText('-0.005')).toBeInTheDocument() // Brier, lower is better
    expect(screen.getByText('-2.8 min')).toBeInTheDocument()
    expect(screen.getAllByText('1,402').length).toBeGreaterThan(0)
    expect(screen.getByText(/90 % of the 1,562 departures/)).toBeInTheDocument()
  })

  it('does not claim a win the confidence interval does not support', () => {
    render(<ReportCard ev={EV} />)
    // the AUC margin straddles zero: interval shown, "within noise" said, and no green pill
    const pill = (t: string) => screen.getByText(t).closest('span[class*="rounded-full"]')!
    expect(pill('+0.017').className).not.toMatch(/text-good/)
    expect(screen.getAllByText(/95 % CI/).length).toBe(3) // one per delta tile
    expect(screen.getAllByText(/within noise/).length).toBe(2) // AUC and Brier; MAE is the one real win
    expect(pill('-2.8 min').className).toMatch(/text-good/) // MAE clears zero, so it may be green
    expect(screen.getByText(/separably better on MAE/)).toBeInTheDocument()
  })

  it('states the coverage of the window rather than implying every departure was scored', () => {
    render(<ReportCard ev={EV} />)
    expect(screen.getAllByText(/1,402/).length).toBeGreaterThan(0)
    expect(screen.getByText(/departures on those dates were scored in time/)).toBeInTheDocument()
    expect(screen.getByText(/not a random sample/)).toBeInTheDocument()
  })

  it('explains that the horizon is measured against the timetable, not the actual departure', () => {
    render(<ReportCard ev={EV} />)
    expect(screen.getByText('AUC by forecast horizon')).toBeInTheDocument()
    expect(screen.getByText(/is a function of the delay itself/)).toBeInTheDocument()
  })

  it('shows the unflattering counterpart to the hand-picked winners', () => {
    render(<ReportCard ev={EV} />)
    expect(screen.getByText(/all 14 calls published at P ≥ 70 %/i)).toBeInTheDocument()
    expect(screen.getByText(/picked/i)).toHaveTextContent(/can only contain wins/i)
    expect(screen.getAllByText(/were more than 15 minutes late/).length).toBeGreaterThan(0)
  })

  it('shows the notable flights with an outcome that is never colour alone', () => {
    render(<ReportCard ev={EV} />)
    expect(screen.getByText('RA 410')).toBeInTheDocument()
    expect(screen.getByText('235 min late')).toBeInTheDocument()
    const misses = screen.getByRole('table', { name: /largest gap/i })
    expect(within(misses).getByText('UO 616')).toBeInTheDocument()
    expect(within(misses).getByText('on time')).toBeInTheDocument() // high P, left on time
    expect(within(misses).getByText('147 min late')).toBeInTheDocument() // low P, very late
  })

  it('explains the method in plain English', () => {
    render(<ReportCard ev={EV} />)
    expect(screen.getByText('How this is computed')).toBeInTheDocument()
    expect(screen.getByText(/last score written before the actual departure time/)).toBeInTheDocument()
    expect(screen.getByText(/airline × hour lookup table/)).toBeInTheDocument()
  })

  it('falls back to empty states when an older snapshot has no report-card keys', () => {
    const old: LiveEval = {
      ...EV,
      daily: undefined,
      lead_buckets: undefined,
      calibration: undefined,
      notable: undefined,
    }
    render(<ReportCard ev={old} />)
    expect(screen.getByText('0.663')).toBeInTheDocument() // headline tiles still work
    expect(screen.getByText('no daily series in this snapshot')).toBeInTheDocument()
    expect(screen.getByText('no horizon buckets in this snapshot')).toBeInTheDocument()
    expect(screen.getByText('no live calibration in this snapshot')).toBeInTheDocument()
    expect(screen.getAllByText('no flights in this slice yet')).toHaveLength(2)
  })

  it('says it is still collecting before MIN_N matured predictions', () => {
    render(
      <ReportCard ev={{ window_days: 7, n_matured: 12, min_n: 100, status: 'not enough matured predictions yet' }} />,
    )
    expect(screen.getByText(/Collecting/)).toBeInTheDocument()
    expect(screen.queryByText('AUC (live)')).not.toBeInTheDocument()
  })
})

describe('beatsBaselineText', () => {
  it('renders the Live-map chip only when there is a real live delta', () => {
    // AUC margin inside the noise -> the chip must not say "beats"
    expect(beatsBaselineText(EV)).toBe('live: MAE -2.8 min vs baseline')
    const solid = { ...EV, bootstrap: { ...EV.bootstrap!, beats_baseline: { auc: true, mae: true } } }
    expect(beatsBaselineText(solid)).toBe('beats baseline live: AUC +0.017')
    const nothing = { ...EV, bootstrap: { ...EV.bootstrap!, beats_baseline: { auc: false, mae: false } } }
    expect(beatsBaselineText(nothing)).toBe('live report card: AUC 0.663')
    expect(beatsBaselineText({ ...EV, status: 'not enough matured predictions yet' })).toBeNull()
    // no baseline at all -> the chip still links to the card, it just stops making a comparison
    expect(beatsBaselineText({ ...EV, deltas: null, bootstrap: null })).toBe('live report card: AUC 0.663')
    expect(beatsBaselineText({ ...EV, model: {}, deltas: null, bootstrap: null })).toBeNull()
    expect(beatsBaselineText(null)).toBeNull()
  })
})

describe('ReportCard failure modes', () => {
  it('does not disguise a broken export as a young deployment', () => {
    render(
      <ReportCard ev={{ window_days: 7, n_matured: 0, min_n: 100, status: 'error: no such table: predictions' }} />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/could not be computed/i)
    expect(screen.queryByText(/Collecting/)).not.toBeInTheDocument()
    expect(screen.getByText(/no such table: predictions/)).toBeInTheDocument()
  })

  it('keeps a flight number appearing twice in a day as two rows', () => {
    const twice = {
      ...EV,
      notable: {
        ...EV.notable!,
        confident_correct: [
          { ...EV.notable!.confident_correct[0], sched_ts: '2026-08-18T02:00+00:00' },
          { ...EV.notable!.confident_correct[0], sched_ts: '2026-08-18T14:00+00:00', p: 0.8 },
        ],
      },
    }
    render(<ReportCard ev={twice} />)
    expect(screen.getAllByText('RA 410')).toHaveLength(2) // same flight_no + date, distinct keys
  })
})
