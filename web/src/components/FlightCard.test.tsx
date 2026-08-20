import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { FlightCard } from './FlightCard'
import type { Flight } from '@/lib/types'

const FLIGHT: Flight = {
  flight_no: 'CX 261',
  airline: 'CPA',
  dest: 'CDG',
  sched_ts: '2026-08-20T16:05:00Z',
  est_ts: null,
  actual_ts: null,
  status: 'scheduled',
  terminal: 'T1',
  gate: '60',
  codeshares: null,
  delay_min: null,
  p: 0.42,
  pred_min: 18.4,
  scored_at: '2026-08-20T07:14:44Z',
  why: [
    [1, 'rain reported at the field', 6.2],
    [1, 'HKIA is running 19 min late today so far', 4.31],
    [-1, 'operated by Cathay Pacific (CPA)', -3.12],
  ],
}

const block = () => screen.getByRole('region', { name: /why this prediction/i })

describe('FlightCard — why this prediction', () => {
  it('renders one row per attribution with its one-liner and probability points', () => {
    render(<FlightCard flight={FLIGHT} meta={null} />)
    const items = within(block()).getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(items[0]).toHaveTextContent('rain reported at the field')
    expect(items[0]).toHaveTextContent('+6.2 pp')
    expect(items[2]).toHaveTextContent('operated by Cathay Pacific (CPA)')
    expect(items[2]).toHaveTextContent('-3.1 pp')
  })

  it('states the direction in words and in the sign, not by colour alone', () => {
    render(<FlightCard flight={FLIGHT} meta={null} />)
    const items = within(block()).getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('raises the probability')
    expect(items[2]).toHaveTextContent('lowers the probability')
    // every row also carries an arrow glyph (aria-hidden svg) next to the text
    expect(items[0].querySelector('svg')).not.toBeNull()
  })

  it('carries the "explains the model, not the world" caveat', () => {
    render(<FlightCard flight={FLIGHT} meta={null} />)
    expect(within(block()).getByText(/local SHAP values for this single prediction/i)).toBeInTheDocument()
    expect(within(block()).getByText(/explain the model,\s*not the world/i)).toBeInTheDocument()
  })

  it('shows an empty state when the snapshot has no attributions (older JSON)', () => {
    const { why: _why, ...rest } = FLIGHT
    render(<FlightCard flight={rest as Flight} meta={null} />)
    expect(within(block()).getByText(/No attribution in this snapshot/i)).toBeInTheDocument()
    expect(within(block()).queryAllByRole('listitem')).toHaveLength(0)
  })

  it('hides the block entirely for a flight that was never scored', () => {
    render(<FlightCard flight={{ ...FLIGHT, p: null, why: undefined }} meta={null} />)
    expect(screen.queryByRole('region', { name: /why this prediction/i })).toBeNull()
    expect(screen.getByText(/Not scored yet/i)).toBeInTheDocument()
  })
})
