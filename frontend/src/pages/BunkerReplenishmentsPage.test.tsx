import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import BunkerReplenishmentsPage from './BunkerReplenishmentsPage'

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

const VESSEL = { id: 1, name: 'SP Baltic Trader', imo_number: '9123456', ice_class: 'Arc4' }

const SAMPLE_REPLENISHMENT = {
  id: 1,
  vessel_id: 1,
  replenishment_datetime: '2026-06-01 10:00:00',
  port: 'Ust-Luga',
  supplier: 'Baltic Bunker Co',
  invoice_number: 'INV-001',
  currency: 'USD',
  lines: [
    { id: 1, fuel_grade: 'IFO', quantity_mt: 200, price_per_mt: 550, total_cost: 110000 },
    { id: 2, fuel_grade: 'MGO', quantity_mt: 30, price_per_mt: 800, total_cost: 24000 },
  ],
  total_cost: 134000,
}

describe('BunkerReplenishmentsPage', () => {
  it('renders the list with total cost per replenishment', async () => {
    mockFetchByUrl({
      '/bunker-replenishments': [{ status: 200, body: [SAMPLE_REPLENISHMENT] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<BunkerReplenishmentsPage />)

    expect(await screen.findByText('Ust-Luga')).toBeInTheDocument()
    expect(screen.getByText('134000')).toBeInTheDocument()
  })

  it('lets the operator record a replenishment with IFO and MGO lines', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/bunker-replenishments': [
        { status: 200, body: [] },
        { status: 201, body: SAMPLE_REPLENISHMENT },
        { status: 200, body: [SAMPLE_REPLENISHMENT] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<BunkerReplenishmentsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/^vessel/i), '1')
    await user.type(screen.getByLabelText(/date\/time/i), '2026-06-01 10:00:00')
    await user.type(screen.getByLabelText(/^port/i), 'Ust-Luga')
    await user.type(screen.getByLabelText(/supplier/i), 'Baltic Bunker Co')
    await user.type(screen.getByLabelText(/^currency/i), 'USD')
    await user.type(screen.getByLabelText(/ifo.*quantity/i), '200')
    await user.type(screen.getByLabelText(/ifo.*price/i), '550')
    await user.type(screen.getByLabelText(/mgo.*quantity/i), '30')
    await user.type(screen.getByLabelText(/mgo.*price/i), '800')
    await user.click(screen.getByRole('button', { name: /record replenishment/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4))
    const postCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
    const body = JSON.parse(postCall![1].body as string)
    expect(body.lines).toEqual([
      { fuel_grade: 'IFO', quantity_mt: 200, price_per_mt: 550 },
      { fuel_grade: 'MGO', quantity_mt: 30, price_per_mt: 800 },
    ])
  })

  it('omits an empty fuel grade line from the submitted payload', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/bunker-replenishments': [
        { status: 200, body: [] },
        { status: 201, body: SAMPLE_REPLENISHMENT },
        { status: 200, body: [SAMPLE_REPLENISHMENT] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<BunkerReplenishmentsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/^vessel/i), '1')
    await user.type(screen.getByLabelText(/date\/time/i), '2026-06-01 10:00:00')
    await user.type(screen.getByLabelText(/^port/i), 'Ust-Luga')
    await user.type(screen.getByLabelText(/supplier/i), 'Baltic Bunker Co')
    await user.type(screen.getByLabelText(/^currency/i), 'USD')
    await user.type(screen.getByLabelText(/ifo.*quantity/i), '200')
    await user.type(screen.getByLabelText(/ifo.*price/i), '550')
    await user.click(screen.getByRole('button', { name: /record replenishment/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4))
    const postCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
    const body = JSON.parse(postCall![1].body as string)
    expect(body.lines).toEqual([{ fuel_grade: 'IFO', quantity_mt: 200, price_per_mt: 550 }])
  })

  it('lets the operator view the itemized lines for a replenishment', async () => {
    mockFetchByUrl({
      '/bunker-replenishments': [{ status: 200, body: [SAMPLE_REPLENISHMENT] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<BunkerReplenishmentsPage />)
    await screen.findByText('Ust-Luga')

    await userEvent.click(screen.getByRole('button', { name: /view lines/i }))

    expect(screen.getByText('110000')).toBeInTheDocument()
    expect(screen.getByText('24000')).toBeInTheDocument()
  })

  it('lets the operator edit a replenishment and submits a PUT', async () => {
    const user = userEvent.setup()
    const correctedReplenishment = {
      ...SAMPLE_REPLENISHMENT,
      supplier: 'Corrected Supplier Ltd',
      lines: [{ id: 1, fuel_grade: 'IFO', quantity_mt: 180, price_per_mt: 540, total_cost: 97200 }],
      total_cost: 97200,
    }
    const fetchMock = mockFetchByUrl({
      '/bunker-replenishments': [
        { status: 200, body: [SAMPLE_REPLENISHMENT] },
        { status: 200, body: correctedReplenishment },
        { status: 200, body: [correctedReplenishment] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<BunkerReplenishmentsPage />)
    await screen.findByText('Ust-Luga')

    await user.click(screen.getByRole('button', { name: /edit/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(/editing.*existing/i)
    const supplierInput = screen.getByLabelText(/supplier/i)
    await user.clear(supplierInput)
    await user.type(supplierInput, 'Corrected Supplier Ltd')
    await user.click(screen.getByRole('button', { name: /update replenishment/i }))

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'PUT')).toBe(true),
    )
    const putCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'PUT')
    expect(putCall?.[0]).toContain('/bunker-replenishments/1')
    const body = JSON.parse(putCall![1].body as string)
    expect(body.supplier).toBe('Corrected Supplier Ltd')

    expect(await screen.findByText('Corrected Supplier Ltd')).toBeInTheDocument()
  })
})
