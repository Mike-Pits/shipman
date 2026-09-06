import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ClaimsPage from './ClaimsPage'

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
  cargo_grade: 'gasoil',
  cargo_quantity_mt: 5000,
  laden: true,
  warnings: [],
}

const SAMPLE_CLAIM = {
  id: 1,
  voyage_id: 1,
  fixture_id: 1,
  disbursement_account_id: null,
  claim_type: 'cargo_quantity',
  counterparty: 'Rotterdam Terminal Ltd',
  amount_claimed: 15000,
  amount_settled: null,
  currency: 'USD',
  status: 'open',
  date_raised: '2026-06-15',
  date_resolved: null,
  settled_payment_id: null,
  notes: 'Shortlanded 50 MT per draft survey',
}

describe('ClaimsPage', () => {
  it('renders the list of claims', async () => {
    mockFetchByUrl({
      '/claims': [{ status: 200, body: [SAMPLE_CLAIM] }],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<ClaimsPage />)

    expect(await screen.findByText('Rotterdam Terminal Ltd')).toBeInTheDocument()
    expect(screen.getByText(/15000/)).toBeInTheDocument()
  })

  it('lets the operator record a claim linked to a voyage', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/claims': [
        { status: 200, body: [] },
        { status: 201, body: SAMPLE_CLAIM },
        { status: 200, body: [SAMPLE_CLAIM] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<ClaimsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/voyage/i), '1')
    await userEvent.selectOptions(screen.getByLabelText(/claim type/i), 'cargo_quantity')
    await user.type(screen.getByLabelText(/counterparty/i), 'Rotterdam Terminal Ltd')
    await user.type(screen.getByLabelText(/amount claimed/i), '15000')
    await user.type(screen.getByLabelText(/^currency/i), 'USD')
    await user.type(screen.getByLabelText(/date raised/i), '2026-06-15')
    await user.click(screen.getByRole('button', { name: /record claim/i }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
      if (!call) throw new Error('no POST call yet')
      return call
    })
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({
      voyage_id: 1,
      claim_type: 'cargo_quantity',
      counterparty: 'Rotterdam Terminal Ltd',
      amount_claimed: 15000,
      currency: 'USD',
      date_raised: '2026-06-15',
    })
  })

  it('lets the operator move a claim into negotiation', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/claims/1/status': [{ status: 200, body: { ...SAMPLE_CLAIM, status: 'negotiating' } }],
      '/claims': [
        { status: 200, body: [SAMPLE_CLAIM] },
        { status: 200, body: [{ ...SAMPLE_CLAIM, status: 'negotiating' }] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<ClaimsPage />)
    await screen.findByText('Rotterdam Terminal Ltd')

    await user.click(screen.getByRole('button', { name: /negotiate/i }))

    expect(await screen.findByText(/^negotiating$/i)).toBeInTheDocument()
  })

  it('lets the operator reject a claim', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/claims/1/status': [{ status: 200, body: { ...SAMPLE_CLAIM, status: 'rejected' } }],
      '/claims': [
        { status: 200, body: [SAMPLE_CLAIM] },
        { status: 200, body: [{ ...SAMPLE_CLAIM, status: 'rejected' }] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<ClaimsPage />)
    await screen.findByText('Rotterdam Terminal Ltd')

    await user.click(screen.getByRole('button', { name: /^reject$/i }))

    expect(await screen.findByText(/^rejected$/i)).toBeInTheDocument()
  })

  it('lets the operator settle a claim with a settled amount', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/claims/1/settle': [
        { status: 200, body: { ...SAMPLE_CLAIM, status: 'settled', amount_settled: 12000, date_resolved: '2026-07-01' } },
      ],
      '/claims': [
        { status: 200, body: [SAMPLE_CLAIM] },
        {
          status: 200,
          body: [{ ...SAMPLE_CLAIM, status: 'settled', amount_settled: 12000, date_resolved: '2026-07-01' }],
        },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<ClaimsPage />)
    await screen.findByText('Rotterdam Terminal Ltd')

    await user.type(screen.getByLabelText(/settlement amount/i), '12000')
    await user.click(screen.getByRole('button', { name: /settle/i }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url.includes('/settle'))
      if (!call) throw new Error('no settle call yet')
      return call
    })
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({ amount_settled: 12000 })
    expect(await screen.findByText(/^settled$/i)).toBeInTheDocument()
  })
})
