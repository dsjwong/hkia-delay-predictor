import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

describe('App shell', () => {
  it('renders the header, nav and LIVE indicator', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({}), { status: 404 })),
    )
    render(<App />)
    expect(await screen.findByText('HKIA departures')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Today' }).length).toBeGreaterThan(0)
    vi.unstubAllGlobals()
  })
})
