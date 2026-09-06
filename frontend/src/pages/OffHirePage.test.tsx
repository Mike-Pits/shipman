import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import OffHirePage from './OffHirePage'

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
  voyage_number: 'TC-001',
  load_port: 'Ust-Luga',
  discharge_port: 'Ust-Luga',
  start_date: '2026-06-01',
  end_date: '2026-08-30',
  cargo_grade: 'n/a',
  cargo_quantity_mt: 0,
  laden: false,
  warnings: [],
}

const SAMPLE_PERIOD = {
  id: 1,
  voyage_id: 1,
  start_datetime: '2026-06-05 00:00:00',
  end_datetime: '2026-06-07 00:00:00',
  reason: 'Main engine breakdown',
  calculated_deduction: 18000,
  override_deduction: null,
  duration_days: 2,
  effective_deduction: 18000,
}

describe('OffHirePage', () => {
  it('shows the off-hire periods for a selected voyage', async () => {
    mockFetchByUrl({
      '/voyages/1/off-hire-periods': [{ status: 200, body: [SAMPLE_PERIOD] }],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<OffHirePage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/voyage/i), '1')

    expect(await screen.findByText('Main engine breakdown')).toBeInTheDocument()
    expect(screen.getAllByText('18000').length).toBeGreaterThan(0)
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('lets the operator record an off-hire period with an automatically calculated deduction', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/voyages/1/off-hire-periods': [
        { status: 200, body: [] },
        { status: 201, body: SAMPLE_PERIOD },
        { status: 200, body: [SAMPLE_PERIOD] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<OffHirePage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/voyage/i), '1')
    await user.type(screen.getByLabelText(/start/i), '2026-06-05 00:00:00')
    await user.type(screen.getByLabelText(/^end/i), '2026-06-07 00:00:00')
    await user.type(screen.getByLabelText(/reason/i), 'Main engine breakdown')
    await user.click(screen.getByRole('button', { name: /record off-hire/i }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
      if (!call) throw new Error('no POST call yet')
      return call
    })
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({
      start_datetime: '2026-06-05 00:00:00',
      end_datetime: '2026-06-07 00:00:00',
      reason: 'Main engine breakdown',
    })
    expect(await screen.findByText('Main engine breakdown')).toBeInTheDocument()
  })

  it('lets the operator override the calculated deduction', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/voyages/1/off-hire-periods': [
        { status: 200, body: [] },
        { status: 201, body: { ...SAMPLE_PERIOD, override_deduction: 15000, effective_deduction: 15000 } },
        { status: 200, body: [{ ...SAMPLE_PERIOD, override_deduction: 15000, effective_deduction: 15000 }] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<OffHirePage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/voyage/i), '1')
    await user.type(screen.getByLabelText(/start/i), '2026-06-05 00:00:00')
    await user.type(screen.getByLabelText(/^end/i), '2026-06-07 00:00:00')
    await user.type(screen.getByLabelText(/reason/i), 'Partial off-hire clause applies')
    await user.type(screen.getByLabelText(/override/i), '15000')
    await user.click(screen.getByRole('button', { name: /record off-hire/i }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
      if (!call) throw new Error('no POST call yet')
      return call
    })
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({ override_deduction: 15000 })
    await waitFor(() => expect(screen.getAllByText('15000').length).toBeGreaterThan(0))
  })

  it('surfaces the backend error when off-hire is attempted on a non time-charter-out voyage', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/voyages/1/off-hire-periods': [
        { status: 200, body: [] },
        { status: 422, body: { detail: 'Off-hire periods can only be recorded for a Time Charter Out voyage' } },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<OffHirePage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/voyage/i), '1')
    await user.type(screen.getByLabelText(/start/i), '2026-06-05 00:00:00')
    await user.type(screen.getByLabelText(/^end/i), '2026-06-07 00:00:00')
    await user.type(screen.getByLabelText(/reason/i), 'n/a')
    await user.click(screen.getByRole('button', { name: /record off-hire/i }))

    expect(await screen.findByText(/time charter out voyage/i)).toBeInTheDocument()
  })

  it('lets the operator correct an off-hire period and submits a PUT', async () => {
    const user = userEvent.setup()
    const correctedPeriod = {
      ...SAMPLE_PERIOD,
      end_datetime: '2026-06-08 00:00:00',
      reason: 'Main engine breakdown (extended)',
      duration_days: 3,
      calculated_deduction: 27000,
      effective_deduction: 27000,
    }
    const fetchMock = mockFetchByUrl({
      '/voyages/1/off-hire-periods/1': [{ status: 200, body: correctedPeriod }],
      '/voyages/1/off-hire-periods': [
        { status: 200, body: [SAMPLE_PERIOD] },
        { status: 200, body: [correctedPeriod] },
      ],
      '/voyages': [{ status: 200, body: [VOYAGE] }],
    })

    render(<OffHirePage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/voyage/i), '1')
    await screen.findByText('Main engine breakdown')

    await user.click(screen.getByRole('button', { name: /^edit$/i }))

    const endInput = screen.getByLabelText(/^end/i)
    await user.clear(endInput)
    await user.type(endInput, '2026-06-08 00:00:00')
    const reasonInput = screen.getByLabelText(/reason/i)
    await user.clear(reasonInput)
    await user.type(reasonInput, 'Main engine breakdown (extended)')
    await user.click(screen.getByRole('button', { name: /update off-hire/i }))

    const putCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'PUT')
      if (!call) throw new Error('no PUT call yet')
      return call
    })
    expect(putCall[0]).toContain('/voyages/1/off-hire-periods/1')
    const body = JSON.parse(putCall[1]!.body as string)
    expect(body).toMatchObject({ end_datetime: '2026-06-08 00:00:00', reason: 'Main engine breakdown (extended)' })

    await waitFor(() => expect(screen.getAllByText('27000').length).toBeGreaterThan(0))
  })
})
