import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VoyageReportsPage from './VoyageReportsPage'

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

const VOYAGE = {
  id: 1,
  fixture_id: 1,
  vessel_id: 1,
  voyage_number: 'V-001',
  load_port: 'Ust-Luga',
  discharge_port: 'Rotterdam',
  start_date: '2026-06-01',
  end_date: '2026-06-11',
  cargo_grade: 'gasoil',
  cargo_quantity_mt: 5000,
  laden: true,
  warnings: [],
}

describe('VoyageReportsPage', () => {
  it("lets the operator select a voyage and see its P&L", async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/voyages': [{ status: 200, body: [VOYAGE] }],
      '/reports/voyage-pnl/1': [
        { status: 200, body: { voyage_id: 1, revenue: 500000, costs: 120000, net_result: 380000, currency: 'RUB' } },
      ],
      '/reports/tce/1': [
        {
          status: 200,
          body: {
            voyage_id: 1,
            revenue: 500000,
            costs: 120000,
            net_result: 380000,
            currency: 'RUB',
            duration_days: 10,
            off_hire_days: 0,
            earning_days: 10,
            tce_per_day: 38000,
          },
        },
      ],
    })

    render(<VoyageReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/voyage/i), '1')

    expect(await screen.findByText('500000')).toBeInTheDocument()
    expect(screen.getByText('120000')).toBeInTheDocument()
    expect(screen.getByText('380000')).toBeInTheDocument()
    void user
  })

  it('shows the estimate variance when the voyage originated from a promoted estimate', async () => {
    mockFetchByUrl({
      '/voyages': [{ status: 200, body: [VOYAGE] }],
      '/reports/voyage-pnl/1': [
        {
          status: 200,
          body: {
            voyage_id: 1,
            revenue: 150000,
            costs: 110000,
            net_result: 40000,
            currency: 'RUB',
            estimated_net_result: 50000,
            variance_vs_estimate: -10000,
          },
        },
      ],
      '/reports/tce/1': [
        {
          status: 200,
          body: {
            voyage_id: 1,
            revenue: 150000,
            costs: 110000,
            net_result: 40000,
            currency: 'RUB',
            duration_days: 10,
            off_hire_days: 0,
            earning_days: 10,
            tce_per_day: 4000,
          },
        },
      ],
    })

    render(<VoyageReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/voyage/i), '1')

    expect(await screen.findByText('50000')).toBeInTheDocument()
    expect(screen.getByText('-10000')).toBeInTheDocument()
  })

  it('shows the TCE breakdown for a completed voyage', async () => {
    mockFetchByUrl({
      '/voyages': [{ status: 200, body: [VOYAGE] }],
      '/reports/voyage-pnl/1': [
        { status: 200, body: { voyage_id: 1, revenue: 500000, costs: 120000, net_result: 380000, currency: 'RUB' } },
      ],
      '/reports/tce/1': [
        {
          status: 200,
          body: {
            voyage_id: 1,
            revenue: 500000,
            costs: 120000,
            net_result: 380000,
            currency: 'RUB',
            duration_days: 10,
            off_hire_days: 2,
            earning_days: 8,
            tce_per_day: 47500,
          },
        },
      ],
    })

    render(<VoyageReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/voyage/i), '1')

    expect(await screen.findByText('47500')).toBeInTheDocument()
    expect(screen.getByText('8')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('shows a friendly message when TCE cannot be calculated yet', async () => {
    mockFetchByUrl({
      '/voyages': [{ status: 200, body: [VOYAGE] }],
      '/reports/voyage-pnl/1': [
        { status: 200, body: { voyage_id: 1, revenue: 500000, costs: 120000, net_result: 380000, currency: 'RUB' } },
      ],
      '/reports/tce/1': [
        {
          status: 422,
          body: { detail: 'Voyage has no end date yet — TCE cannot be calculated until the voyage is complete' },
        },
      ],
    })

    render(<VoyageReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/voyage/i), '1')

    expect(await screen.findByText(/tce cannot be calculated/i)).toBeInTheDocument()
  })

  it('provides Excel export links for both reports', async () => {
    mockFetchByUrl({
      '/voyages': [{ status: 200, body: [VOYAGE] }],
      '/reports/voyage-pnl/1': [
        { status: 200, body: { voyage_id: 1, revenue: 500000, costs: 120000, net_result: 380000, currency: 'RUB' } },
      ],
      '/reports/tce/1': [
        {
          status: 200,
          body: {
            voyage_id: 1,
            revenue: 500000,
            costs: 120000,
            net_result: 380000,
            currency: 'RUB',
            duration_days: 10,
            off_hire_days: 0,
            earning_days: 10,
            tce_per_day: 38000,
          },
        },
      ],
    })

    render(<VoyageReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/voyage/i), '1')
    await screen.findByText('380000')

    const pnlLink = screen.getByRole('link', { name: /export p&l/i }) as HTMLAnchorElement
    const tceLink = screen.getByRole('link', { name: /export tce/i }) as HTMLAnchorElement
    expect(pnlLink.href).toContain('/api/reports/voyage-pnl/1?format=xlsx')
    expect(tceLink.href).toContain('/api/reports/tce/1?format=xlsx')
  })
})
