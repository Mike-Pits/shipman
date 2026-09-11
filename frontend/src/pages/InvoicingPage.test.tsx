import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InvoicingPage from './InvoicingPage'

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

const TC_OUT_FIXTURE = {
  id: 1,
  fixture_type: 'time_charter_out',
  charterer: 'Northern Charterers',
  contract_currency: 'RUB',
  hire_rate: 9000,
  brokers: [],
}

const SAMPLE_INVOICE = {
  id: 1,
  invoice_number: 'INV-2026-0001',
  invoice_type: 'hire',
  status: 'draft',
  date_of_issue: '2026-07-01',
  due_date: '2026-07-05',
  currency: 'RUB',
  vat_applicable: false,
  vat_amount: 0,
  counterparty: 'Northern Charterers',
  subject: null,
  fixture_id: 1,
  voyage_id: null,
  vessel_id: 1,
  claim_id: null,
  payment_id: null,
  hire_period_start: '2026-06-01',
  hire_period_end: '2026-06-11',
  total_amount_due: 90000,
  total_amount_due_rub: null,
  lines: [{ id: 1, description: 'Hire', quantity: 10, unit: 'day', unit_price: 9000, amount: 90000 }],
}

describe('InvoicingPage', () => {
  it('renders the list of invoices', async () => {
    mockFetchByUrl({
      '/invoices': [{ status: 200, body: [SAMPLE_INVOICE] }],
      '/fixtures': [{ status: 200, body: [TC_OUT_FIXTURE] }],
      '/voyages': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/claims': [{ status: 200, body: [] }],
    })

    render(<InvoicingPage />)

    expect(await screen.findByText('INV-2026-0001')).toBeInTheDocument()
    expect(screen.getByText('Northern Charterers')).toBeInTheDocument()
  })

  it('lets the operator create a hire invoice', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/invoices': [
        { status: 200, body: [] },
        { status: 201, body: SAMPLE_INVOICE },
        { status: 200, body: [SAMPLE_INVOICE] },
      ],
      '/fixtures': [{ status: 200, body: [TC_OUT_FIXTURE] }],
      '/voyages': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/claims': [{ status: 200, body: [] }],
    })

    render(<InvoicingPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.type(screen.getByLabelText(/date of issue/i), '2026-07-01')
    await user.selectOptions(screen.getByLabelText(/fixture/i), '1')
    await user.selectOptions(screen.getByLabelText(/vessel/i), '1')
    await user.type(screen.getByLabelText(/hire period start/i), '2026-06-01')
    await user.type(screen.getByLabelText(/hire period end/i), '2026-06-11')
    await user.click(screen.getByRole('button', { name: /create draft/i }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
      if (!call) throw new Error('no POST call yet')
      return call
    })
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({
      invoice_type: 'hire',
      date_of_issue: '2026-07-01',
      fixture_id: 1,
      vessel_id: 1,
      hire_period_start: '2026-06-01',
      hire_period_end: '2026-06-11',
    })
  })

  it('lets the operator create a free-form invoice with a manually entered line', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/invoices': [
        { status: 200, body: [] },
        { status: 201, body: { ...SAMPLE_INVOICE, id: 9, invoice_type: 'free_form' } },
        { status: 200, body: [] },
      ],
      '/fixtures': [{ status: 200, body: [TC_OUT_FIXTURE] }],
      '/voyages': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/claims': [{ status: 200, body: [] }],
    })

    render(<InvoicingPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.selectOptions(screen.getByLabelText(/invoice type/i), 'free_form')
    await user.type(screen.getByLabelText(/date of issue/i), '2026-06-01')
    await user.selectOptions(screen.getByLabelText(/^vessel$/i), '1')
    await user.type(screen.getByLabelText(/subject/i), 'Agency reimbursement')
    await user.type(screen.getByLabelText(/counterparty/i), 'Baltic Agency LLC')
    await user.selectOptions(screen.getByLabelText(/^currency$/i), 'RUB')
    await user.click(screen.getByRole('button', { name: /add line/i }))
    await user.type(screen.getByLabelText(/description/i), 'Port dues reimbursement')
    await user.type(screen.getByLabelText(/quantity/i), '1')
    await user.type(screen.getByLabelText(/^unit$/i), 'lump sum')
    await user.type(screen.getByLabelText(/unit price/i), '50000')
    await user.click(screen.getByRole('button', { name: /create draft/i }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
      if (!call) throw new Error('no POST call yet')
      return call
    })
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({
      invoice_type: 'free_form',
      subject: 'Agency reimbursement',
      counterparty: 'Baltic Agency LLC',
      currency: 'RUB',
      lines: [{ description: 'Port dues reimbursement', quantity: 1, unit: 'lump sum', unit_price: 50000 }],
    })
  })

  it('lets the operator issue a draft invoice', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/invoices/1/issue': [{ status: 200, body: { ...SAMPLE_INVOICE, status: 'issued', payment_id: 5 } }],
      '/invoices': [
        { status: 200, body: [SAMPLE_INVOICE] },
        { status: 200, body: [{ ...SAMPLE_INVOICE, status: 'issued', payment_id: 5 }] },
      ],
      '/fixtures': [{ status: 200, body: [TC_OUT_FIXTURE] }],
      '/voyages': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/claims': [{ status: 200, body: [] }],
    })

    render(<InvoicingPage />)
    expect(await screen.findByText('INV-2026-0001')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^issue$/i }))

    await waitFor(() => expect(screen.getByText(/issued/i)).toBeInTheDocument())
    const issueCall = fetchMock.mock.calls.find(([url]) => (url as string).includes('/issue'))
    expect(issueCall).toBeTruthy()
  })

  it('lets the operator void an issued invoice after confirming', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const issuedInvoice = { ...SAMPLE_INVOICE, status: 'issued', payment_id: 5 }
    const fetchMock = mockFetchByUrl({
      '/invoices/1/void': [{ status: 200, body: { ...issuedInvoice, status: 'void', payment_id: null } }],
      '/invoices': [
        { status: 200, body: [issuedInvoice] },
        { status: 200, body: [{ ...issuedInvoice, status: 'void', payment_id: null }] },
      ],
      '/fixtures': [{ status: 200, body: [TC_OUT_FIXTURE] }],
      '/voyages': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/claims': [{ status: 200, body: [] }],
    })

    render(<InvoicingPage />)
    expect(await screen.findByText('INV-2026-0001')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /void/i }))

    expect(window.confirm).toHaveBeenCalled()
    await waitFor(() => expect(screen.getByText(/^void$/i)).toBeInTheDocument())
    const voidCall = fetchMock.mock.calls.find(([url]) => (url as string).includes('/void'))
    expect(voidCall).toBeTruthy()
  })

  it('lets the operator delete a draft invoice after confirming', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = mockFetchByUrl({
      '/invoices': [
        { status: 200, body: [SAMPLE_INVOICE] },
        { status: 204, body: undefined },
        { status: 200, body: [] },
      ],
      '/fixtures': [{ status: 200, body: [TC_OUT_FIXTURE] }],
      '/voyages': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/claims': [{ status: 200, body: [] }],
    })

    render(<InvoicingPage />)
    expect(await screen.findByText('INV-2026-0001')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^delete$/i }))

    await waitFor(() => expect(screen.queryByText('INV-2026-0001')).not.toBeInTheDocument())
    const deleteCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'DELETE')
    expect(deleteCall?.[0]).toContain('/invoices/1')
  })
})
