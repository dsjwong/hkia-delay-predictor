import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { FlightCard } from './FlightCard'
import type { Flight, Inbound } from '@/lib/types'

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

  it('hides the block for a departed flight — the exporter only writes attributions for pending ones', () => {
    render(<FlightCard flight={{ ...FLIGHT, status: 'departed', actual_ts: '2026-08-20T16:31:00Z', why: undefined }} meta={null} />)
    expect(screen.queryByRole('region', { name: /why this prediction/i })).toBeNull()
  })

  it('hides the block entirely for a flight that was never scored', () => {
    render(<FlightCard flight={{ ...FLIGHT, p: null, why: undefined }} meta={null} />)
    expect(screen.queryByRole('region', { name: /why this prediction/i })).toBeNull()
    expect(screen.getByText(/Not scored yet/i)).toBeInTheDocument()
  })
})

const LANDED_INBOUND: Inbound = {
  flight_no: 'UO 755',
  origin: 'CNX',
  sched_ts: '2026-08-20T02:30:00Z',
  actual_ts: '2026-08-20T03:00:00Z',
  est_ts: null,
  status: 'landed',
  slack_min: 128,
  sched_slack_min: 150,
  confidence: 1.0,
  method: 'stand_gate',
  used_by_model: true,
}

const inboundBlock = () => screen.getByRole('region', { name: /inbound aircraft/i })

describe('FlightCard — inbound aircraft', () => {
  it('renders the section for a landed inbound, with an on-stand badge and no "not in the score" caveat', () => {
    render(<FlightCard flight={{ ...FLIGHT, inbound: LANDED_INBOUND }} meta={null} />)
    const block = inboundBlock()
    expect(within(block).getByText(/UO 755 from CNX/i)).toBeInTheDocument()
    expect(within(block).getByText(/on stand/i)).toBeInTheDocument()
    expect(within(block).getByText(/2 h 08 min/)).toBeInTheDocument()
    expect(within(block).queryByText(/wasn.t available in time/i)).toBeNull()
  })

  it('shows the ETA and the "not in the score" clause for an in-flight inbound not used by the model', () => {
    const inbound: Inbound = {
      ...LANDED_INBOUND,
      actual_ts: null,
      est_ts: '2026-08-20T03:10:00Z',
      status: 'in_flight',
      used_by_model: false,
    }
    render(<FlightCard flight={{ ...FLIGHT, inbound }} meta={null} />)
    const block = inboundBlock()
    expect(within(block).getByText(/in flight/i)).toBeInTheDocument()
    expect(within(block).getByText(/est/i)).toBeInTheDocument()
    expect(within(block).getByText(/wasn.t available in time for the score above/i)).toBeInTheDocument()
  })

  it('is not rendered when the flight carries no inbound object', () => {
    render(<FlightCard flight={{ ...FLIGHT, inbound: undefined }} meta={null} />)
    expect(screen.queryByRole('region', { name: /inbound aircraft/i })).toBeNull()
  })
})
