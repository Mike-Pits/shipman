import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VoyagesPage from './VoyagesPage'

function mockFetchByUrl(handlers: Record<string, Array<{ status: number; body: unknown }>>) {
  const calls: Array<[string, RequestInit | undefined]> = []
  const counters: Record<string, number> = {}
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    calls.push([url, options])
    const key = Object.keys(handlers).find((k) => url.includes(k))!
    const i = counters[key] ?? 0
    const responses = handlers[key]
    const { status, body } = responses[Math.min(i, responses.length - 1)]
    counters[key] = i + 1
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    } as Response
  })
  vi.stubGlobal('fetch', fetchMock)
  return { fetchMock, calls }
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

const VESSEL = { id: 1, name: 'SP Baltic Trader', imo_number: '9123456', ice_class: 'Arc4' }
const FIXTURE = { id: 1, fixture_type: 'voyage_charter', charterer: 'Test Charterer', contract_currency: 'USD', brokers: [] }

describe('VoyagesPage', () => {
  it('renders the list of voyages fetched from the API', async () => {
    mockFetchByUrl({
      '/voyages': [{ status: 200, body: [{ id: 1, fixture_id: 1, vessel_id: 1, voyage_number: 'V-001', load_port: 'Ust-Luga', discharge_port: 'Rotterdam', start_date: '2026-06-01', cargo_grade: 'gasoil', cargo_quantity_mt: 5000, laden: true, warnings: [] }] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/fixtures': [{ status: 200, body: [FIXTURE] }],
    })

    render(<VoyagesPage />)

    expect(await screen.findByText('V-001')).toBeInTheDocument()
    expect(screen.getAllByText('SP Baltic Trader').length).toBeGreaterThan(0)
  })

  it('lets the operator create a voyage linked to a fixture and vessel', async () => {
    const user = userEvent.setup()
    const { fetchMock } = mockFetchByUrl({
      '/voyages': [
        { status: 200, body: [] },
        { status: 201, body: { id: 2, fixture_id: 1, vessel_id: 1, voyage_number: 'V-002', load_port: 'Ust-Luga', discharge_port: 'Rotterdam', start_date: '2026-06-01', cargo_grade: 'gasoil', cargo_quantity_mt: 5000, laden: true, warnings: [] } },
        { status: 200, body: [] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/fixtures': [{ status: 200, body: [FIXTURE] }],
    })

    render(<VoyagesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.selectOptions(screen.getByLabelText(/fixture/i), '1')
    await user.selectOptions(screen.getByLabelText(/vessel/i), '1')
    await user.type(screen.getByLabelText(/voyage number/i), 'V-002')
    await user.type(screen.getByLabelText(/load port/i), 'Ust-Luga')
    await user.type(screen.getByLabelText(/discharge port/i), 'Rotterdam')
    await user.type(screen.getByLabelText(/start date/i), '2026-06-01')
    await user.type(screen.getByLabelText(/cargo grade/i), 'gasoil')
    await user.type(screen.getByLabelText(/cargo quantity/i), '5000')
    await user.click(screen.getByLabelText(/laden/i))
    await user.click(screen.getByRole('button', { name: /create voyage/i }))

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(true),
    )
    const postCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
    const body = JSON.parse(postCall![1].body as string)
    expect(body).toMatchObject({
      fixture_id: 1,
      vessel_id: 1,
      voyage_number: 'V-002',
      load_port: 'Ust-Luga',
      discharge_port: 'Rotterdam',
      start_date: '2026-06-01',
      cargo_grade: 'gasoil',
      cargo_quantity_mt: 5000,
      laden: true,
    })
    expect(body.end_date).toBeNull()
  })

  it('surfaces a vetting warning returned by the API for a voyage', async () => {
    mockFetchByUrl({
      '/voyages': [{ status: 200, body: [{ id: 3, fixture_id: 1, vessel_id: 1, voyage_number: 'V-003', load_port: 'Ust-Luga', discharge_port: 'Rotterdam', start_date: '2026-06-01', cargo_grade: 'gasoil', cargo_quantity_mt: 5000, laden: true, warnings: ["This vessel's vetting status is expired or failed — it may be commercially unfixable"] }] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/fixtures': [{ status: 200, body: [FIXTURE] }],
    })

    render(<VoyagesPage />)

    expect(await screen.findByText(/vetting status is expired or failed/i)).toBeInTheDocument()
  })

  it('lets the operator edit a voyage, shows a warning while editing, and submits a PUT', async () => {
    const user = userEvent.setup()
    const existingVoyage = {
      id: 7,
      fixture_id: 1,
      vessel_id: 1,
      voyage_number: 'V-007',
      load_port: 'Ust-Luga',
      discharge_port: 'Rotterdam',
      start_date: '2026-06-01',
      cargo_grade: 'gasoil',
      cargo_quantity_mt: 5000,
      laden: true,
      warnings: [],
    }
    const { fetchMock } = mockFetchByUrl({
      '/voyages': [
        { status: 200, body: [existingVoyage] },
        { status: 200, body: { ...existingVoyage, cargo_quantity_mt: 6000 } },
        { status: 200, body: [{ ...existingVoyage, cargo_quantity_mt: 6000 }] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/fixtures': [{ status: 200, body: [FIXTURE] }],
    })

    render(<VoyagesPage />)
    expect(await screen.findByText('V-007')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /edit/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(/editing.*existing voyage/i)
    const qtyInput = screen.getByLabelText(/cargo quantity/i)
    expect(qtyInput).toHaveValue(5000)
    await user.clear(qtyInput)
    await user.type(qtyInput, '6000')
    await user.click(screen.getByRole('button', { name: /update voyage/i }))

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'PUT')).toBe(true),
    )
    const putCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'PUT')
    expect(putCall?.[0]).toContain('/voyages/7')
    expect(JSON.parse(putCall![1].body as string).cargo_quantity_mt).toBe(6000)
  })
})
