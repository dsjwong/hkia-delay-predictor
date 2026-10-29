import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { CancellationBody } from './CancellationPanel'
import type { Cancellations } from '@/lib/types'

const cell = (n: number, k: number) => ({ n, n_cancelled: k, rate: k / n, ci: [Math.max(0, k / n - 0.01), k / n + 0.01] as [number, number] })

const DATA: Cancellations = {
  summary: {
    date_min: '2026-05-16',
    date_max: '2026-10-28',
    n_days: 166,
    n_flights: 71547,
    n_cancelled: 659,
    rate: 0.0092,
    n_days_with_cancellations: 117,
    top3_days_share: 0.443,
    disruption_days: ['2026-07-11', '2026-07-26'],
    disruption_rate: 0.05,
    share_on_disruption_or_signal3: 0.545,
    ordinary: cell(69281, 300),
  },
  by_signal: [
    { signal: 0, label: 'none', n_days: 155, ...cell(68470, 446) },
    { signal: 1, label: 'No. 1', n_days: 9, ...cell(2570, 28) },
    { signal: 8, label: 'No. 8', n_days: 1, ...cell(201, 111) },
  ],
  by_hour: Array.from({ length: 24 }, (_, hour) => ({ hour, ...cell(3000, 12) })),
  by_airline: [{ code: 'CPA', name: 'Cathay Pacific', ...cell(27840, 88) }],
  days: [
    { date: '2026-07-26', n: 451, n_cancelled: 178, rate: 0.3947, signal: 9, top_airline: 'Cathay Pacific', top_airline_share: 0.652 },
    { date: '2026-07-11', n: 450, n_cancelled: 71, rate: 0.1578, signal: 0, top_airline: 'Cathay Pacific', top_airline_share: 0.423 },
  ],
  min_cell_airline: 500,
}

describe('CancellationBody', () => {
  it('shows n and the cancelled count in every signal row, and the headline tiles', () => {
    render(<CancellationBody c={DATA} />)
    expect(screen.getByRole('heading', { name: /cancellations across the whole window/i })).toBeTruthy()
    const row = screen.getAllByRole('row').find((r) => within(r).queryByText('201'))
    expect(row).toBeTruthy()
    expect(within(row as HTMLElement).getByText('111')).toBeTruthy()
    expect(screen.getByText('659')).toBeTruthy()
    expect(screen.getByText(/why there is no cancellation model/i)).toBeTruthy()
  })

  it('names the day with no signal as unattributed, not as a typhoon', () => {
    render(<CancellationBody c={DATA} />)
    const row = screen.getAllByRole('row').find((r) => within(r).queryByText('2026-07-11'))
    expect(within(row as HTMLElement).getByText('none')).toBeTruthy()
  })

  it('renders nothing for an empty snapshot', () => {
    const { container } = render(<CancellationBody c={{ summary: null }} />)
    expect(container.firstChild).toBeNull()
  })
})
