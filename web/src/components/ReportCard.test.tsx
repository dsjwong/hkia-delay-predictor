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
  deltas: { auc: 0.0169, brier: -0.0053, logloss: -0.0123, mae: -2.829 },
  daily: [
    { date: '2026-08-17', n: 293, delayed15_rate: 0.2287, thin: false, model: slice(0.5923), baseline: slice(0.5372) },
    { date: '2026-08-18', n: 440, delayed15_rate: 0.2386, thin: false, model: slice(0.7012), baseline: slice(0.6549) },
  ],
  lead_buckets: [
    {
      label: '< 30 min',
      lo_min: 0,
      hi_min: 30,
      n: 811,
      thin: false,
      delayed15_rate: 0.164,
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
      median_lead_min: null,
      model: slice(null),
    },
  ],
  calibration: [{ bin: '0.0-0.1', n: 204, pred_mean: 0.071, obs_rate: 0.098 }],
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
  },
}

describe('ReportCard', () => {
  it('leads with the live headline numbers and the baseline delta', () => {
    render(<ReportCard ev={EV} />)
    expect(screen.getByText('AUC (live)')).toBeInTheDocument()
    expect(screen.getByText('0.663')).toBeInTheDocument()
    expect(screen.getByText('+0.017')).toBeInTheDocument() // beats the airline x hour baseline
    expect(screen.getByText('-0.005')).toBeInTheDocument() // Brier, lower is better
    expect(screen.getByText('-2.8 min')).toBeInTheDocument()
    expect(screen.getAllByText('1,402').length).toBeGreaterThan(0)
    expect(screen.getByText(/7-day window · 08-17 → 08-20/)).toBeInTheDocument()
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
    expect(screen.getByText('no lead-time buckets in this snapshot')).toBeInTheDocument()
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
    expect(beatsBaselineText(EV)).toBe('beats baseline live: AUC +0.017')
    expect(beatsBaselineText({ ...EV, deltas: { ...EV.deltas!, auc: -0.004 } })).toBe(
      'trails baseline live: AUC -0.004',
    )
    expect(beatsBaselineText({ ...EV, status: 'not enough matured predictions yet' })).toBeNull()
    expect(beatsBaselineText({ ...EV, deltas: null })).toBeNull()
    expect(beatsBaselineText(null)).toBeNull()
  })
})
