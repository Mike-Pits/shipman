import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DisbursementAccountsPage from './DisbursementAccountsPage'

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

const SAMPLE_DA = {
  id: 1,
  voyage_id: 1,
  port: 'Rotterdam',
  pda_amount: 15000,
  pda_currency: 'USD',
  pda_date: '2026-06-05',
  status: 'pda_only',
  lines: [],
  fda_total: 0,
  variance: -15000,
}

describe('DisbursementAccountsPage', () => {
  it('renders the list with PDA/FDA/variance shown', async () => {
    mockFetchByUrl({
      '/disbursement-accounts': [{ status: 200, body: [SAMPLE_DA] }],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<DisbursementAccountsPage />)

    await waitFor(() => expect(screen.getAllByText('V-001').length).toBeGreaterThan(0))
    expect(screen.getByText('Rotterdam')).toBeInTheDocument()
    expect(screen.getByText('-15000')).toBeInTheDocument()
  })

  it('lets the operator record a PDA for a voyage', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/disbursement-accounts': [
        { status: 200, body: [] },
        { status: 201, body: SAMPLE_DA },
        { status: 200, body: [SAMPLE_DA] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<DisbursementAccountsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/^voyage/i), '1')
    await user.type(screen.getByLabelText(/^port/i), 'Rotterdam')
    await user.type(screen.getByLabelText(/pda amount/i), '15000')
    await user.type(screen.getByLabelText(/pda currency/i), 'USD')
    await user.type(screen.getByLabelText(/pda date/i), '2026-06-05')
    await user.click(screen.getByRole('button', { name: /record pda/i }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
      if (!call) throw new Error('no POST call yet')
      return call
    })
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({ voyage_id: 1, port: 'Rotterdam', pda_amount: 15000 })
  })

  it('lets the operator add an FDA line, updating total and variance', async () => {
    const user = userEvent.setup()
    const updatedDa = {
      ...SAMPLE_DA,
      status: 'fda_pending',
      lines: [{ id: 1, line_type: 'pilotage', description: 'Inbound pilot', amount: 3000, currency: 'USD' }],
      fda_total: 3000,
      variance: -12000,
    }
    mockFetchByUrl({
      '/disbursement-accounts/1/fda-lines': [{ status: 200, body: updatedDa }],
      '/disbursement-accounts': [
        { status: 200, body: [SAMPLE_DA] },
        { status: 200, body: [updatedDa] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<DisbursementAccountsPage />)
    await waitFor(() => expect(screen.getAllByText('V-001').length).toBeGreaterThan(0))

    await user.type(screen.getByLabelText(/description/i), 'Inbound pilot')
    await user.type(screen.getByLabelText(/^amount/i), '3000')
    await user.type(screen.getByLabelText(/^currency/i), 'USD')
    await user.click(screen.getByRole('button', { name: /add line/i }))

    expect(await screen.findByText('-12000')).toBeInTheDocument()
    expect(screen.getByText('3000')).toBeInTheDocument()
  })

  it('lets the operator reconcile a DA', async () => {
    const user = userEvent.setup()
    const daWithLines = {
      ...SAMPLE_DA,
      status: 'fda_pending',
      lines: [{ id: 1, line_type: 'pilotage', description: 'Inbound pilot', amount: 3000, currency: 'USD' }],
      fda_total: 3000,
      variance: -12000,
    }
    mockFetchByUrl({
      '/disbursement-accounts/1/reconcile': [{ status: 200, body: { ...daWithLines, status: 'reconciled' } }],
      '/disbursement-accounts': [
        { status: 200, body: [daWithLines] },
        { status: 200, body: [{ ...daWithLines, status: 'reconciled' }] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<DisbursementAccountsPage />)
    await waitFor(() => expect(screen.getAllByText('V-001').length).toBeGreaterThan(0))

    await user.click(screen.getByRole('button', { name: /reconcile/i }))

    expect(await screen.findByText(/reconciled/i)).toBeInTheDocument()
  })

  it('lets the operator mark a DA as disputed', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/disbursement-accounts/1/dispute': [{ status: 200, body: { ...SAMPLE_DA, status: 'disputed' } }],
      '/disbursement-accounts': [
        { status: 200, body: [SAMPLE_DA] },
        { status: 200, body: [{ ...SAMPLE_DA, status: 'disputed' }] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<DisbursementAccountsPage />)
    await waitFor(() => expect(screen.getAllByText('V-001').length).toBeGreaterThan(0))

    await user.click(screen.getByRole('button', { name: /mark disputed/i }))

    expect(await screen.findByText(/disputed/i)).toBeInTheDocument()
  })

  it('lets the operator correct the PDA header fields and submits a PUT', async () => {
    const user = userEvent.setup()
    const correctedDa = { ...SAMPLE_DA, port: 'Rotterdam Port', pda_amount: 16000, variance: -16000 }
    const fetchMock = mockFetchByUrl({
      '/disbursement-accounts': [
        { status: 200, body: [SAMPLE_DA] },
        { status: 200, body: correctedDa },
        { status: 200, body: [correctedDa] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<DisbursementAccountsPage />)
    await waitFor(() => expect(screen.getAllByText('V-001').length).toBeGreaterThan(0))

    await user.click(screen.getByRole('button', { name: /^edit$/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(/editing.*existing/i)
    const portInput = screen.getByLabelText(/^port/i)
    await user.clear(portInput)
    await user.type(portInput, 'Rotterdam Port')
    await user.click(screen.getByRole('button', { name: /update pda/i }))

    const putCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'PUT')
      if (!call) throw new Error('no PUT call yet')
      return call
    })
    expect(putCall[0]).toContain('/disbursement-accounts/1')
    const body = JSON.parse(putCall[1]!.body as string)
    expect(body.port).toBe('Rotterdam Port')

    expect(await screen.findByText('Rotterdam Port')).toBeInTheDocument()
  })

  it('lets the operator correct an existing FDA line and submits a PUT', async () => {
    const user = userEvent.setup()
    const daWithLine = {
      ...SAMPLE_DA,
      status: 'fda_pending',
      lines: [{ id: 1, line_type: 'pilotage', description: 'Inbound pilot', amount: 3000, currency: 'USD' }],
      fda_total: 3000,
      variance: -12000,
    }
    const correctedDa = {
      ...daWithLine,
      lines: [{ id: 1, line_type: 'pilotage', description: 'Inbound pilot (corrected)', amount: 3200, currency: 'USD' }],
      fda_total: 3200,
      variance: -11800,
    }
    const fetchMock = mockFetchByUrl({
      '/disbursement-accounts/1/fda-lines/1': [{ status: 200, body: correctedDa }],
      '/disbursement-accounts': [
        { status: 200, body: [daWithLine] },
        { status: 200, body: [correctedDa] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<DisbursementAccountsPage />)
    await waitFor(() => expect(screen.getAllByText('V-001').length).toBeGreaterThan(0))

    await user.click(screen.getByRole('button', { name: /view lines/i }))
    await user.click(screen.getByRole('button', { name: /^edit line$/i }))

    const saveButton = screen.getByRole('button', { name: /save line/i })
    const editForm = within(saveButton.closest('form')!)
    const descriptionInput = editForm.getByLabelText(/description/i)
    await user.clear(descriptionInput)
    await user.type(descriptionInput, 'Inbound pilot (corrected)')
    const amountInput = editForm.getByLabelText(/^amount/i)
    await user.clear(amountInput)
    await user.type(amountInput, '3200')
    await user.click(saveButton)

    const putCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url.includes('/fda-lines/1'))
      if (!call) throw new Error('no PUT call yet')
      return call
    })
    const body = JSON.parse(putCall[1]!.body as string)
    expect(body).toMatchObject({ description: 'Inbound pilot (corrected)', amount: 3200 })

    expect(await screen.findByText('-11800')).toBeInTheDocument()
  })
})
