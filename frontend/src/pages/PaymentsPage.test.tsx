import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PaymentsPage from './PaymentsPage'

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

const SAMPLE_PAYMENT = {
  id: 1,
  vessel_id: 1,
  voyage_id: null,
  fixture_id: null,
  disbursement_account_id: null,
  vendor_name: 'Port Authority',
  cost_category: 'expense',
  cost_type_name: 'Port Charges',
  original_currency: 'RUB',
  original_amount: 800000,
  rub_equivalent: 800000,
  exchange_rate_used: null,
  exchange_rate_date: null,
  invoice_date: '2026-06-01',
  due_date: null,
  payment_date: null,
  status: 'draft',
  document_number: null,
  notes: null,
}

describe('PaymentsPage', () => {
  it('renders the list with RUB equivalent shown', async () => {
    mockFetchByUrl({
      '/payments': [{ status: 200, body: [SAMPLE_PAYMENT] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/voyages': [{ status: 200, body: [] }],
    })

    render(<PaymentsPage />)

    await waitFor(() => expect(screen.getAllByText('MV Arctic').length).toBeGreaterThan(0))
    expect(screen.getByText('Port Charges')).toBeInTheDocument()
    expect(screen.getByText('800000')).toBeInTheDocument()
  })

  it('lets the operator record a RUB payment needing no conversion', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/payments': [
        { status: 200, body: [] },
        { status: 201, body: SAMPLE_PAYMENT },
        { status: 200, body: [SAMPLE_PAYMENT] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/voyages': [{ status: 200, body: [] }],
    })

    render(<PaymentsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/^vessel/i), '1')
    await userEvent.selectOptions(screen.getByLabelText(/cost category/i), 'expense')
    await user.type(screen.getByLabelText(/cost type/i), 'Port Charges')
    await userEvent.selectOptions(screen.getByLabelText(/original currency/i), 'RUB')
    await user.type(screen.getByLabelText(/original amount/i), '800000')
    await user.type(screen.getByLabelText(/invoice date/i), '2026-06-01')
    await user.click(screen.getByRole('button', { name: /record payment/i }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
      if (!call) throw new Error('no POST call yet')
      return call
    })
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({
      vessel_id: 1,
      cost_category: 'expense',
      cost_type_name: 'Port Charges',
      original_currency: 'RUB',
      original_amount: 800000,
    })
  })

  it('surfaces the error when a USD payment has no stored exchange rate for its date', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/payments': [
        { status: 200, body: [] },
        { status: 422, body: { detail: 'No exchange rate stored for this date' } },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/voyages': [{ status: 200, body: [] }],
    })

    render(<PaymentsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/^vessel/i), '1')
    await userEvent.selectOptions(screen.getByLabelText(/cost category/i), 'income')
    await user.type(screen.getByLabelText(/cost type/i), 'Freight')
    await userEvent.selectOptions(screen.getByLabelText(/original currency/i), 'USD')
    await user.type(screen.getByLabelText(/original amount/i), '12500')
    await user.type(screen.getByLabelText(/invoice date/i), '2026-07-15')
    await user.click(screen.getByRole('button', { name: /record payment/i }))

    expect(await screen.findByText(/no exchange rate stored/i)).toBeInTheDocument()
  })

  it('lets the operator progress a payment through its status workflow', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/payments/1/status': [{ status: 200, body: { ...SAMPLE_PAYMENT, status: 'paid' } }],
      '/payments': [
        { status: 200, body: [SAMPLE_PAYMENT] },
        { status: 200, body: [{ ...SAMPLE_PAYMENT, status: 'paid' }] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/voyages': [{ status: 200, body: [] }],
    })

    render(<PaymentsPage />)
    await waitFor(() => expect(screen.getAllByText('MV Arctic').length).toBeGreaterThan(0))

    const select = screen.getByLabelText(/status for port charges/i) as HTMLSelectElement
    await userEvent.selectOptions(select, 'paid')

    await waitFor(() => expect(select.value).toBe('paid'))
  })

  it('lets the operator view a payment converted to a different display currency', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/payments/1?display_currency=USD': [
        { status: 200, body: { ...SAMPLE_PAYMENT, display_currency: 'USD', display_amount: 10000 } },
      ],
      '/payments': [{ status: 200, body: [SAMPLE_PAYMENT] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/voyages': [{ status: 200, body: [] }],
    })

    render(<PaymentsPage />)
    await waitFor(() => expect(screen.getAllByText('MV Arctic').length).toBeGreaterThan(0))

    await user.click(screen.getByRole('button', { name: /show in usd/i }))

    expect(await screen.findByText(/10000 USD/)).toBeInTheDocument()
  })

  it('lets the operator correct a payment and submits a PUT preserving its status', async () => {
    const user = userEvent.setup()
    const correctedPayment = { ...SAMPLE_PAYMENT, cost_type_name: 'Port Charges (corrected)', original_amount: 850000, rub_equivalent: 850000 }
    const fetchMock = mockFetchByUrl({
      '/payments': [
        { status: 200, body: [SAMPLE_PAYMENT] },
        { status: 200, body: correctedPayment },
        { status: 200, body: [correctedPayment] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/voyages': [{ status: 200, body: [] }],
    })

    render(<PaymentsPage />)
    await waitFor(() => expect(screen.getAllByText('MV Arctic').length).toBeGreaterThan(0))

    await user.click(screen.getByRole('button', { name: /^edit$/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(/editing.*existing/i)
    const amountInput = screen.getByLabelText(/original amount/i)
    await user.clear(amountInput)
    await user.type(amountInput, '850000')
    await user.click(screen.getByRole('button', { name: /update payment/i }))

    const putCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'PUT')
      if (!call) throw new Error('no PUT call yet')
      return call
    })
    expect(putCall[0]).toContain('/payments/1')
    const body = JSON.parse(putCall[1]!.body as string)
    expect(body).toMatchObject({ original_amount: 850000, status: 'draft' })

    expect(await screen.findByText('Port Charges (corrected)')).toBeInTheDocument()
  })

  it('lets the operator delete a payment after confirming, and removes it from the list', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = mockFetchByUrl({
      '/payments': [
        { status: 200, body: [SAMPLE_PAYMENT] },
        { status: 204, body: undefined },
        { status: 200, body: [] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/voyages': [{ status: 200, body: [] }],
    })

    render(<PaymentsPage />)
    await waitFor(() => expect(screen.getAllByText('MV Arctic').length).toBeGreaterThan(0))

    await user.click(screen.getByRole('button', { name: /delete/i }))

    expect(window.confirm).toHaveBeenCalled()
    await waitFor(() => expect(screen.queryByText('Port Charges')).not.toBeInTheDocument())
    const deleteCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'DELETE')
    expect(deleteCall?.[0]).toContain('/payments/1')
  })

  it('does not delete the payment when the operator cancels the confirmation', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const fetchMock = mockFetchByUrl({
      '/payments': [{ status: 200, body: [SAMPLE_PAYMENT] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/voyages': [{ status: 200, body: [] }],
    })

    render(<PaymentsPage />)
    await waitFor(() => expect(screen.getAllByText('MV Arctic').length).toBeGreaterThan(0))

    await user.click(screen.getByRole('button', { name: /delete/i }))

    expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false)
    expect(screen.getByText('Port Charges')).toBeInTheDocument()
  })
})
