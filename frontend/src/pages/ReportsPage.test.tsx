import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReportsPage from './ReportsPage'

function mockFetchByUrl(handlers: Record<string, Array<{ status: number; body: unknown }>>) {
  const counters: Record<string, number> = {}
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    const key = Object.keys(handlers).find((k) => url.includes(k))!
    const i = counters[key] ?? 0
    const responses = handlers[key]
    const { status, body } = responses[Math.min(i, responses.length - 1)]
    counters[key] = i + 1
    void options
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    } as Response
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

const DA_ROW = {
  id: 1,
  voyage_id: 1,
  port: 'Rotterdam',
  status: 'pda_only',
  pda_amount: 15000,
  fda_total: 0,
  variance: -15000,
}

const VETTING_ROW = {
  vessel_id: 1,
  vessel_name: 'MV Arctic',
  status: 'expired',
  expiry_date: '2025-01-01',
}

const CLAIM_ROW = {
  id: 1,
  voyage_id: 1,
  claim_type: 'cargo_quantity',
  counterparty: 'Rotterdam Terminal Ltd',
  amount_claimed: 15000,
  currency: 'USD',
  status: 'open',
  age_days: 10,
}

describe('ReportsPage', () => {
  it('runs a fleet P&L report for a date range', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/reports/fleet-pnl': [
        {
          status: 200,
          body: { start_date: '2026-06-01', end_date: '2026-06-30', revenue: 800000, costs: 200000, net_result: 600000, voyage_count: 2, currency: 'RUB' },
        },
      ],
      '/reports/da-reconciliation': [{ status: 200, body: [] }],
      '/reports/vetting-status': [{ status: 200, body: [] }],
      '/reports/claims-status': [{ status: 200, body: [] }],
    })

    render(<ReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.type(screen.getByLabelText(/start date/i), '2026-06-01')
    await user.type(screen.getByLabelText(/end date/i), '2026-06-30')
    await user.click(screen.getByRole('button', { name: /run fleet p&l/i }))

    expect(await screen.findByText('800000')).toBeInTheDocument()
    expect(screen.getByText('600000')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('shows the DA reconciliation report on load', async () => {
    mockFetchByUrl({
      '/reports/da-reconciliation': [{ status: 200, body: [DA_ROW] }],
      '/reports/vetting-status': [{ status: 200, body: [] }],
      '/reports/claims-status': [{ status: 200, body: [] }],
    })

    render(<ReportsPage />)

    expect(await screen.findByText('Rotterdam')).toBeInTheDocument()
    expect(screen.getByText('-15000')).toBeInTheDocument()
  })

  it('shows the fleet vetting status report on load', async () => {
    mockFetchByUrl({
      '/reports/da-reconciliation': [{ status: 200, body: [] }],
      '/reports/vetting-status': [{ status: 200, body: [VETTING_ROW] }],
      '/reports/claims-status': [{ status: 200, body: [] }],
    })

    render(<ReportsPage />)

    expect(await screen.findByText('MV Arctic')).toBeInTheDocument()
    expect(screen.getByText(/^expired$/i)).toBeInTheDocument()
  })

  it('shows the claims status report on load', async () => {
    mockFetchByUrl({
      '/reports/da-reconciliation': [{ status: 200, body: [] }],
      '/reports/vetting-status': [{ status: 200, body: [] }],
      '/reports/claims-status': [{ status: 200, body: [CLAIM_ROW] }],
    })

    render(<ReportsPage />)

    expect(await screen.findByText('Rotterdam Terminal Ltd')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
  })

  it('provides Excel export links for each report', async () => {
    mockFetchByUrl({
      '/reports/da-reconciliation': [{ status: 200, body: [] }],
      '/reports/vetting-status': [{ status: 200, body: [] }],
      '/reports/claims-status': [{ status: 200, body: [] }],
    })

    render(<ReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    const fleetLink = screen.getByRole('link', { name: /export fleet p&l/i }) as HTMLAnchorElement
    const daLink = screen.getByRole('link', { name: /export da reconciliation/i }) as HTMLAnchorElement
    const vettingLink = screen.getByRole('link', { name: /export vetting status/i }) as HTMLAnchorElement
    const claimsLink = screen.getByRole('link', { name: /export claims status/i }) as HTMLAnchorElement

    expect(fleetLink.href).toContain('/api/reports/fleet-pnl')
    expect(daLink.href).toContain('/api/reports/da-reconciliation?format=xlsx')
    expect(vettingLink.href).toContain('/api/reports/vetting-status?format=xlsx')
    expect(claimsLink.href).toContain('/api/reports/claims-status?format=xlsx')
  })
})
