import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DashboardPage from './DashboardPage'

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

const VESSEL = { id: 1, name: 'MV Arctic', imo_number: '9123456', ice_class: 'Arc4' }

const ACTIVE_VOYAGE = {
  id: 1,
  fixture_id: 1,
  vessel_id: 1,
  voyage_number: 'V-001',
  load_port: 'Ust-Luga',
  discharge_port: 'Rotterdam',
  start_date: '2026-06-01',
  end_date: null,
  cargo_grade: 'gasoil',
  cargo_quantity_mt: 5000,
  laden: true,
  warnings: [],
}

const COMPLETED_VOYAGE = { ...ACTIVE_VOYAGE, id: 2, voyage_number: 'V-002', end_date: '2026-06-11' }

describe('DashboardPage', () => {
  it('renders fleet size and active voyage count', async () => {
    mockFetchByUrl({
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/voyages': [{ status: 200, body: [ACTIVE_VOYAGE, COMPLETED_VOYAGE] }],
      '/reports/fleet-pnl': [
        { status: 200, body: { start_date: '2026-06-01', end_date: '2026-06-30', revenue: 0, costs: 0, net_result: 0, voyage_count: 0, currency: 'RUB' } },
      ],
      '/reports/da-reconciliation': [{ status: 200, body: [] }],
      '/reports/vetting-status': [{ status: 200, body: [] }],
      '/reports/claims-status': [{ status: 200, body: [] }],
      '/reports/current-vessel-status': [{ status: 200, body: [] }],
    })

    render(<DashboardPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    expect(screen.getByText('Fleet Size').closest('.stat-card')).toHaveTextContent('1')
    expect(screen.getByText('Active Voyages').closest('.stat-card')).toHaveTextContent('1')
  })

  it("renders this month's fleet P&L", async () => {
    mockFetchByUrl({
      '/vessels': [{ status: 200, body: [] }],
      '/voyages': [{ status: 200, body: [] }],
      '/reports/fleet-pnl': [
        {
          status: 200,
          body: { start_date: '2026-06-01', end_date: '2026-06-30', revenue: 800000, costs: 200000, net_result: 600000, voyage_count: 2, currency: 'RUB' },
        },
      ],
      '/reports/da-reconciliation': [{ status: 200, body: [] }],
      '/reports/vetting-status': [{ status: 200, body: [] }],
      '/reports/claims-status': [{ status: 200, body: [] }],
      '/reports/current-vessel-status': [{ status: 200, body: [] }],
    })

    render(<DashboardPage />)

    expect(await screen.findByText(/600000/)).toBeInTheDocument()
  })

  it('renders counts of unreconciled DAs, vetting issues, and open claims', async () => {
    mockFetchByUrl({
      '/vessels': [{ status: 200, body: [] }],
      '/voyages': [{ status: 200, body: [] }],
      '/reports/fleet-pnl': [
        { status: 200, body: { start_date: '2026-06-01', end_date: '2026-06-30', revenue: 0, costs: 0, net_result: 0, voyage_count: 0, currency: 'RUB' } },
      ],
      '/reports/da-reconciliation': [{ status: 200, body: [{ id: 1 }, { id: 2 }] }],
      '/reports/vetting-status': [
        { status: 200, body: [{ vessel_id: 1, vessel_name: 'MV Arctic', status: 'expired', expiry_date: '2025-01-01' }] },
      ],
      '/reports/claims-status': [{ status: 200, body: [{ id: 1 }, { id: 2 }, { id: 3 }] }],
      '/reports/current-vessel-status': [{ status: 200, body: [] }],
    })

    render(<DashboardPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('shows which vessels are not employed today', async () => {
    mockFetchByUrl({
      '/vessels': [{ status: 200, body: [] }],
      '/voyages': [{ status: 200, body: [] }],
      '/reports/fleet-pnl': [
        { status: 200, body: { start_date: '2026-06-01', end_date: '2026-06-30', revenue: 0, costs: 0, net_result: 0, voyage_count: 0, currency: 'RUB' } },
      ],
      '/reports/da-reconciliation': [{ status: 200, body: [] }],
      '/reports/vetting-status': [{ status: 200, body: [] }],
      '/reports/claims-status': [{ status: 200, body: [] }],
      '/reports/current-vessel-status': [
        {
          status: 200,
          body: [
            { vessel_id: 1, vessel_name: 'MV Arctic', status: 'employment', voyage_id: 1 },
            { vessel_id: 2, vessel_name: 'SP Baltic', status: 'ballast_passage', voyage_id: 2 },
            { vessel_id: 3, vessel_name: 'SP Dudinka', status: 'unaccounted', voyage_id: null },
          ],
        },
      ],
    })

    render(<DashboardPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    expect(screen.getByText('Vessels Not Employed Today').closest('.stat-card')).toHaveTextContent('2')
    expect(screen.getByText(/SP Baltic: Ballast Passage/)).toBeInTheDocument()
    expect(screen.getByText(/SP Dudinka: No Record/)).toBeInTheDocument()
  })
})
