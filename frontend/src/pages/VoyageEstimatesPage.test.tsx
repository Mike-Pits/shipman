import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VoyageEstimatesPage from './VoyageEstimatesPage'

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

const SAMPLE_ESTIMATE = {
  id: 1,
  vessel_id: null,
  load_port: 'Ust-Luga',
  discharge_port: 'Rotterdam',
  laycan_start: '2026-06-01',
  laycan_end: '2026-06-05',
  cargo_grade: 'gasoil',
  estimated_cargo_quantity_mt: 5000,
  estimated_rate: 30,
  estimated_rate_basis: 'per_tonne',
  currency: 'USD',
  estimated_bunker_consumption_mt: 200,
  estimated_bunker_cost: 110000,
  estimated_port_costs: 20000,
  estimated_duration_days: 10,
  status: 'draft',
  fixture_id: null,
  warnings: [],
  estimated_revenue: 150000,
  estimated_costs: 130000,
  estimated_net_result: 20000,
  estimated_tce_per_day: 2000,
}

describe('VoyageEstimatesPage', () => {
  it('renders the list with computed TCE shown', async () => {
    mockFetchByUrl({
      '/voyage-estimates': [{ status: 200, body: [SAMPLE_ESTIMATE] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<VoyageEstimatesPage />)

    expect(await screen.findByText('Ust-Luga')).toBeInTheDocument()
    expect(screen.getByText('2000')).toBeInTheDocument()
  })

  it('lets the operator create a voyage estimate', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/voyage-estimates': [
        { status: 200, body: [] },
        { status: 201, body: SAMPLE_ESTIMATE },
        { status: 200, body: [SAMPLE_ESTIMATE] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<VoyageEstimatesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.type(screen.getByLabelText(/load port/i), 'Ust-Luga')
    await user.type(screen.getByLabelText(/discharge port/i), 'Rotterdam')
    await user.type(screen.getByLabelText(/laycan start/i), '2026-06-01')
    await user.type(screen.getByLabelText(/laycan end/i), '2026-06-05')
    await user.type(screen.getByLabelText(/cargo grade/i), 'gasoil')
    await user.type(screen.getByLabelText(/cargo quantity/i), '5000')
    await user.type(screen.getByLabelText(/^rate$/i), '30')
    await userEvent.selectOptions(screen.getByLabelText(/rate basis/i), 'per_tonne')
    await user.type(screen.getByLabelText(/^currency/i), 'USD')
    await user.type(screen.getByLabelText(/bunker consumption/i), '200')
    await user.type(screen.getByLabelText(/bunker cost/i), '110000')
    await user.type(screen.getByLabelText(/port costs/i), '20000')
    await user.type(screen.getByLabelText(/duration/i), '10')
    await user.click(screen.getByRole('button', { name: /create estimate/i }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
      if (!call) throw new Error('no POST call yet')
      return call
    })
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({
      load_port: 'Ust-Luga',
      discharge_port: 'Rotterdam',
      estimated_rate: 30,
      estimated_rate_basis: 'per_tonne',
    })
  })

  it('lets the operator move an estimate into negotiation', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/voyage-estimates/1/status': [
        { status: 200, body: { ...SAMPLE_ESTIMATE, status: 'under_negotiation' } },
      ],
      '/voyage-estimates': [
        { status: 200, body: [SAMPLE_ESTIMATE] },
        { status: 200, body: [{ ...SAMPLE_ESTIMATE, status: 'under_negotiation' }] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<VoyageEstimatesPage />)
    await screen.findByText('Ust-Luga')

    await user.click(screen.getByRole('button', { name: /negotiate/i }))

    expect(await screen.findByText(/under negotiation/i)).toBeInTheDocument()
  })

  it('lets the operator decline an estimate', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/voyage-estimates/1/status': [{ status: 200, body: { ...SAMPLE_ESTIMATE, status: 'declined' } }],
      '/voyage-estimates': [
        { status: 200, body: [SAMPLE_ESTIMATE] },
        { status: 200, body: [{ ...SAMPLE_ESTIMATE, status: 'declined' }] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<VoyageEstimatesPage />)
    await screen.findByText('Ust-Luga')

    await user.click(screen.getByRole('button', { name: /^decline$/i }))

    expect(await screen.findByText(/^declined$/i)).toBeInTheDocument()
  })

  it('lets the operator promote an estimate to a fixture', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/voyage-estimates/1/promote': [{ status: 201, body: { id: 9, fixture_type: 'voyage_charter', brokers: [] } }],
      '/voyage-estimates': [
        { status: 200, body: [SAMPLE_ESTIMATE] },
        { status: 200, body: [{ ...SAMPLE_ESTIMATE, status: 'fixed', fixture_id: 9 }] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<VoyageEstimatesPage />)
    await screen.findByText('Ust-Luga')

    await user.click(screen.getByRole('button', { name: /^promote$/i }))
    await user.type(screen.getByLabelText(/charterer/i), 'Test Charterer')
    await user.click(screen.getByRole('button', { name: /confirm promotion/i }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url.includes('/promote'))
      if (!call) throw new Error('no promote call yet')
      return call
    })
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({
      fixture_type: 'voyage_charter',
      charterer: 'Test Charterer',
      load_port: 'Ust-Luga',
      discharge_port: 'Rotterdam',
      freight_rate: 30,
      freight_rate_basis: 'per_tonne',
    })
    expect(await screen.findByText(/^fixed$/i)).toBeInTheDocument()
  })

  it('shows a vetting warning when the assigned vessel is commercially unfixable', async () => {
    mockFetchByUrl({
      '/voyage-estimates': [
        {
          status: 200,
          body: [
            {
              ...SAMPLE_ESTIMATE,
              vessel_id: 1,
              warnings: ["This vessel's vetting status is expired or failed — it may be commercially unfixable"],
            },
          ],
        },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<VoyageEstimatesPage />)

    expect(await screen.findByText(/vetting status is expired or failed/i)).toBeInTheDocument()
  })
})
