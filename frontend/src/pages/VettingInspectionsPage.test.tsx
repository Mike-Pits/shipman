import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VettingInspectionsPage from './VettingInspectionsPage'

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

const SAMPLE_INSPECTION = {
  id: 1,
  vessel_id: 1,
  inspection_date: '2026-01-15',
  inspecting_body: 'Shell SIRE',
  inspection_type: 'SIRE',
  expiry_date: '2026-12-31',
  status: 'approved',
  observations: 'No major findings',
}

describe('VettingInspectionsPage', () => {
  it('shows the current vetting status and inspection history once a vessel is selected', async () => {
    mockFetchByUrl({
      '/vessels/1/vetting-status': [
        { status: 200, body: { status: 'approved', inspecting_body: 'Shell SIRE', expiry_date: '2026-12-31' } },
      ],
      '/vessels/1/vetting-inspections': [{ status: 200, body: [SAMPLE_INSPECTION] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<VettingInspectionsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/vessel/i), '1')

    await waitFor(() => expect(screen.getAllByText('Shell SIRE').length).toBeGreaterThan(0))
    expect(screen.getAllByText(/approved/i).length).toBeGreaterThan(0)
    expect(screen.getByText('No major findings')).toBeInTheDocument()
  })

  it('shows no-status messaging when the vessel has no inspections', async () => {
    mockFetchByUrl({
      '/vessels/1/vetting-status': [{ status: 200, body: { status: null } }],
      '/vessels/1/vetting-inspections': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<VettingInspectionsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/vessel/i), '1')

    expect(await screen.findByText(/no vetting inspections/i)).toBeInTheDocument()
  })

  it('lets the operator record a new vetting inspection', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/vessels/1/vetting-status': [{ status: 200, body: { status: null } }],
      '/vessels/1/vetting-inspections': [
        { status: 200, body: [] },
        { status: 201, body: SAMPLE_INSPECTION },
        { status: 200, body: [SAMPLE_INSPECTION] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<VettingInspectionsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/vessel/i), '1')
    await screen.findByText(/no vetting inspections/i)

    await user.type(screen.getByLabelText(/inspection date/i), '2026-01-15')
    await user.type(screen.getByLabelText(/inspecting body/i), 'Shell SIRE')
    await user.type(screen.getByLabelText(/inspection type/i), 'SIRE')
    await user.type(screen.getByLabelText(/expiry date/i), '2026-12-31')
    await userEvent.selectOptions(screen.getByLabelText(/^status/i), 'approved')
    await user.type(screen.getByLabelText(/observations/i), 'No major findings')
    await user.click(screen.getByRole('button', { name: /record inspection/i }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
      if (!call) throw new Error('no POST call yet')
      return call
    })
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({
      inspection_date: '2026-01-15',
      inspecting_body: 'Shell SIRE',
      inspection_type: 'SIRE',
      expiry_date: '2026-12-31',
      status: 'approved',
    })
    await waitFor(() => expect(screen.getAllByText('Shell SIRE').length).toBeGreaterThan(0))
  })

  it('shows an expired status for an approved inspection past its expiry date', async () => {
    mockFetchByUrl({
      '/vessels/1/vetting-status': [
        { status: 200, body: { status: 'expired', inspecting_body: 'Shell SIRE', expiry_date: '2025-01-01' } },
      ],
      '/vessels/1/vetting-inspections': [
        { status: 200, body: [{ ...SAMPLE_INSPECTION, expiry_date: '2025-01-01' }] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<VettingInspectionsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/vessel/i), '1')

    await waitFor(() => expect(screen.getAllByText(/^expired$/i).length).toBeGreaterThan(0))
  })
})
