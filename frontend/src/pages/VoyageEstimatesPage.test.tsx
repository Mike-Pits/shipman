import { render, screen, waitFor, within } from '@testing-library/react'
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
  window.scrollTo = vi.fn()
})

const VESSEL = {
  id: 1,
  name: 'MV Arctic',
  imo_number: '9123456',
  ice_class: 'Arc4',
  fuel_consumption_profiles: [
    { id: 1, mode: 'laden', ifo_mt_per_day: 20, mgo_mt_per_day: 2, speed_kt: 12 },
    { id: 2, mode: 'ballast', ifo_mt_per_day: 18, mgo_mt_per_day: 2, speed_kt: 13 },
  ],
}

const RESULTS = {
  total_distance_nm: 1728,
  sea_days: 6,
  sea_laden_days: 6,
  sea_ballast_days: 0,
  port_days: 4,
  load_days: 2,
  discharge_days: 2,
  total_voyage_days: 10,
  fuel: { IFO: { quantity_mt: 130, cost: 65000 }, MGO: { quantity_mt: 22, cost: 19800 } },
  total_fuel_cost: 84800,
  freight_revenue: 150000,
  other_costs: 20000,
  extra_items_total: 0,
  allowed_laytime_days: 4,
  excess_days: 0,
  demurrage: 0,
  total_costs: 104800,
  net_result: 45200,
  tce_per_day: 4520,
  warnings: [],
}

const SAMPLE_ESTIMATE = {
  id: 1,
  name: 'UL-RTM June',
  vessel_id: null,
  currency: 'USD',
  laycan_start: '2026-06-01',
  laycan_end: '2026-06-05',
  freight_mode: 'per_mt',
  lumpsum_freight: 0,
  extra_sea_days: 0,
  extra_costs: 0,
  canal_fees: 0,
  port_charges: 20000,
  agent_fees: 0,
  bunker_surcharge: 0,
  demurrage_rate: 0,
  status: 'draft',
  fixture_id: null,
  baseline_net_result: null,
  baseline_tce_per_day: null,
  port_stops: [
    { port_name: 'Ust-Luga', stop_type: 'load', distance_nm: 0, condition: 'ballast', cargo_quantity_mt: 5000, laytime_value: 2, laytime_unit: 'days', laytime_basis: 'SHINC', rate_mt_per_day: 0 },
    { port_name: 'Rotterdam', stop_type: 'discharge', distance_nm: 1728, condition: 'laden', cargo_quantity_mt: 5000, laytime_value: 48, laytime_unit: 'hours', laytime_basis: 'SHINC', rate_mt_per_day: 0 },
  ],
  cargo_lots: [{ grade: 'gasoil', quantity_mt: 5000, freight_rate: 30 }],
  fuel_prices: [{ grade: 'IFO', price_per_mt: 500 }, { grade: 'MGO', price_per_mt: 900 }],
  cost_items: [],
  results: RESULTS,
  warnings: [],
}

const baseHandlers = (estimates: unknown[]) => ({
  '/voyage-estimates/calculate': [{ status: 200, body: RESULTS }],
  '/voyage-estimates': [{ status: 200, body: estimates }],
  '/vessels': [{ status: 200, body: [VESSEL] }],
  '/ports': [{ status: 200, body: [{ id: 1, name: 'Ust-Luga' }] }],
})

describe('VoyageEstimatesPage', () => {
  it('renders the list with route, days and calculated TCE', async () => {
    mockFetchByUrl(baseHandlers([SAMPLE_ESTIMATE]))

    render(<VoyageEstimatesPage />)

    expect(await screen.findByText('UL-RTM June')).toBeInTheDocument()
    expect(screen.getByText('Ust-Luga → Rotterdam')).toBeInTheDocument()
    expect(screen.getByText(/4,?520 USD/)).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
  })

  it('lets the operator build a multi-port estimate and save it', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/voyage-estimates/calculate': [{ status: 200, body: RESULTS }],
      '/voyage-estimates': [
        { status: 200, body: [] },
        { status: 201, body: SAMPLE_ESTIMATE },
        { status: 200, body: [SAMPLE_ESTIMATE] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/ports': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.type(screen.getByLabelText('Estimate Name'), 'UL-RTM June')
    await user.selectOptions(screen.getByLabelText('Vessel'), '1')
    await user.type(screen.getByLabelText('Port 1'), 'Ust-Luga')
    await user.type(screen.getByLabelText('Cargo (MT) 1'), '5000')
    await user.click(screen.getByRole('button', { name: '+ Add Port' }))
    await user.type(screen.getByLabelText('Port 2'), 'Rotterdam')
    await user.selectOptions(screen.getByLabelText('Type 2'), 'discharge')
    await user.type(screen.getByLabelText('Dist. (NM) 2'), '1728')
    await user.type(screen.getByLabelText('Cargo Grade 1'), 'gasoil')
    await user.type(screen.getByLabelText('Qty (MT) 1'), '5000')
    await user.type(screen.getByLabelText('Freight Rate 1'), '30')
    await user.type(screen.getByLabelText('Price IFO'), '500')
    await user.type(screen.getByLabelText('Price MGO'), '900')
    await user.click(screen.getByRole('button', { name: 'Save Estimate' }))

    const postCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
      if (!call) throw new Error('no POST call yet')
      return call
    })
    expect(postCall[0]).toContain('/voyage-estimates')
    const body = JSON.parse(postCall[1]!.body as string)
    expect(body).toMatchObject({
      name: 'UL-RTM June',
      vessel_id: 1,
      currency: 'USD',
      freight_mode: 'per_mt',
      cargo_lots: [{ grade: 'gasoil', quantity_mt: 5000, freight_rate: 30 }],
      fuel_prices: [{ grade: 'IFO', price_per_mt: 500 }, { grade: 'MGO', price_per_mt: 900 }],
    })
    expect(body.port_stops.map((s: { port_name: string }) => s.port_name)).toEqual(['Ust-Luga', 'Rotterdam'])
    expect(body.port_stops[0]).toMatchObject({ stop_type: 'load', condition: 'ballast' })
    expect(body.port_stops[1]).toMatchObject({ stop_type: 'discharge', distance_nm: 1728, condition: 'laden' })
    expect(await screen.findByRole('region', { name: 'Voyage Results' })).toBeInTheDocument()
  })

  it('calculates without saving and shows the results panel', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/voyage-estimates/calculate': [{ status: 200, body: RESULTS }],
      '/voyage-estimates': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/ports': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.type(screen.getByLabelText('Port 1'), 'Ust-Luga')
    await user.click(screen.getByRole('button', { name: 'Calculate Voyage' }))

    const panel = await screen.findByRole('region', { name: 'Voyage Results' })
    expect(within(panel).getByText(/4,?520 USD/)).toBeInTheDocument()
    expect(within(panel).getByText('MGO')).toBeInTheDocument()
    expect(within(panel).getByText('IFO')).toBeInTheDocument()
    expect(within(panel).getByText('Fuel')).toBeInTheDocument()
    expect(within(panel).getByText('104,800 USD')).toBeInTheDocument()
    expect(within(panel).getByText('No demurrage — within laytime')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/voyage-estimates'))).toBe(true) // initial list only
    expect(fetchMock.mock.calls.filter(([, o]) => o?.method === 'POST')).toHaveLength(1)
  })

  it('hides the cargo lots in lumpsum mode and sends only the lumpsum freight', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/voyage-estimates/calculate': [{ status: 200, body: RESULTS }],
      '/voyage-estimates': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [] }],
      '/ports': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.click(screen.getByLabelText('Lumpsum'))
    expect(screen.queryByLabelText('Qty (MT) 1')).not.toBeInTheDocument()
    await user.type(screen.getByLabelText(/Lumpsum Freight/), '200000')
    await user.type(screen.getByLabelText('Port 1'), 'Ust-Luga')
    await user.click(screen.getByRole('button', { name: 'Calculate Voyage' }))

    const call = await waitFor(() => {
      const c = fetchMock.mock.calls.find(([, o]) => o?.method === 'POST')
      if (!c) throw new Error('no POST yet')
      return c
    })
    expect(JSON.parse(call[1]!.body as string)).toMatchObject({ freight_mode: 'lumpsum', lumpsum_freight: 200000, cargo_lots: [] })
  })

  it('recalculates automatically as the itinerary is typed, without pressing Calculate', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl(baseHandlers([]))

    render(<VoyageEstimatesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())
    expect(screen.queryByRole('region', { name: 'Voyage Results' })).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('Port 1'), 'Ust-Luga')

    expect(await screen.findByRole('region', { name: 'Voyage Results' })).toBeInTheDocument()
    const calls = fetchMock.mock.calls.filter(([url]) => url.includes('/calculate'))
    expect(calls.length).toBeGreaterThan(0)
    expect(JSON.parse(calls[calls.length - 1][1]!.body as string).port_stops[0].port_name).toBe('Ust-Luga')
  })

  it('gives each leg a condition that defaults from its type and can be overridden', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl(baseHandlers([]))

    render(<VoyageEstimatesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())
    await user.type(screen.getByLabelText('Port 1'), 'Ust-Luga')
    await user.click(screen.getByRole('button', { name: '+ Add Port' }))
    await user.type(screen.getByLabelText('Port 2'), 'Rotterdam')

    expect(screen.getByLabelText('Condition 1')).toBeDisabled() // nothing is sailed to the first port
    expect(screen.getByLabelText('Condition 2')).toHaveValue('laden') // a new port is a discharge port
    await user.selectOptions(screen.getByLabelText('Type 2'), 'load')
    expect(screen.getByLabelText('Condition 2')).toHaveValue('ballast')
    await user.selectOptions(screen.getByLabelText('Condition 2'), 'laden')

    await waitFor(() => {
      const calls = fetchMock.mock.calls.filter(([url]) => url.includes('/calculate'))
      const last = JSON.parse(calls[calls.length - 1][1]!.body as string)
      expect(last.port_stops[1]).toMatchObject({ stop_type: 'load', condition: 'laden' })
    })
  })

  it('always offers IFO and MGO price fields', async () => {
    mockFetchByUrl(baseHandlers([]))

    render(<VoyageEstimatesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    expect(screen.getByLabelText('Price IFO')).toBeInTheDocument()
    expect(screen.getByLabelText('Price MGO')).toBeInTheDocument()
  })

  it('explains in the results when the vessel has no speed for a leg condition', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/voyage-estimates/calculate': [{ status: 200, body: { ...RESULTS, warnings: ['missing_speed:ballast'] } }],
      '/voyage-estimates': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/ports': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())
    await user.type(screen.getByLabelText('Port 1'), 'Ust-Luga')

    expect(await screen.findByText(/no ballast speed on the Vessels page/i)).toBeInTheDocument()
  })

  it('lets the operator move an estimate into negotiation', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/voyage-estimates/1/status': [{ status: 200, body: { ...SAMPLE_ESTIMATE, status: 'under_negotiation' } }],
      '/voyage-estimates/calculate': [{ status: 200, body: RESULTS }],
      '/voyage-estimates': [
        { status: 200, body: [SAMPLE_ESTIMATE] },
        { status: 200, body: [{ ...SAMPLE_ESTIMATE, status: 'under_negotiation' }] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/ports': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await screen.findByText('UL-RTM June')

    await user.click(screen.getByRole('button', { name: /negotiate/i }))

    expect(await screen.findByText(/under negotiation/i)).toBeInTheDocument()
  })

  it('lets the operator decline an estimate', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/voyage-estimates/1/status': [{ status: 200, body: { ...SAMPLE_ESTIMATE, status: 'declined' } }],
      '/voyage-estimates/calculate': [{ status: 200, body: RESULTS }],
      '/voyage-estimates': [
        { status: 200, body: [SAMPLE_ESTIMATE] },
        { status: 200, body: [{ ...SAMPLE_ESTIMATE, status: 'declined' }] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/ports': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await screen.findByText('UL-RTM June')

    await user.click(screen.getByRole('button', { name: /^decline$/i }))

    expect(await screen.findByText(/^declined$/i)).toBeInTheDocument()
  })

  it('lets the operator promote an estimate to a fixture', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/voyage-estimates/1/promote': [{ status: 201, body: { id: 9, fixture_type: 'voyage_charter', brokers: [] } }],
      '/voyage-estimates/calculate': [{ status: 200, body: RESULTS }],
      '/voyage-estimates': [
        { status: 200, body: [SAMPLE_ESTIMATE] },
        { status: 200, body: [{ ...SAMPLE_ESTIMATE, status: 'fixed', fixture_id: 9 }] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/ports': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await screen.findByText('UL-RTM June')

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
      cargo_grade: 'gasoil',
      freight_rate: 30,
      freight_rate_basis: 'per_tonne',
    })
    expect(await screen.findByText(/^fixed$/i)).toBeInTheDocument()
  })

  it('shows a vetting warning when the assigned vessel is commercially unfixable', async () => {
    mockFetchByUrl(
      baseHandlers([
        {
          ...SAMPLE_ESTIMATE,
          vessel_id: 1,
          warnings: ["This vessel's vetting status is expired or failed — it may be commercially unfixable"],
        },
      ]),
    )

    render(<VoyageEstimatesPage />)

    expect(await screen.findByText(/vetting status is expired or failed/i)).toBeInTheDocument()
  })

  it('lets the operator correct an estimate and submits a PUT', async () => {
    const user = userEvent.setup()
    const corrected = {
      ...SAMPLE_ESTIMATE,
      cargo_lots: [{ grade: 'gasoil', quantity_mt: 5000, freight_rate: 35 }],
      results: { ...RESULTS, freight_revenue: 175000, net_result: 70200, tce_per_day: 7020 },
    }
    const fetchMock = mockFetchByUrl({
      '/voyage-estimates/calculate': [{ status: 200, body: RESULTS }],
      '/voyage-estimates': [
        { status: 200, body: [SAMPLE_ESTIMATE] },
        { status: 200, body: corrected },
        { status: 200, body: [corrected] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/ports': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await screen.findByText('UL-RTM June')

    await user.click(screen.getByRole('button', { name: /^edit$/i }))

    const rate = screen.getByLabelText('Freight Rate 1')
    await user.clear(rate)
    await user.type(rate, '35')
    await user.click(screen.getByRole('button', { name: 'Update Estimate' }))

    const putCall = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === 'PUT')
      if (!call) throw new Error('no PUT call yet')
      return call
    })
    expect(putCall[0]).toContain('/voyage-estimates/1')
    expect(JSON.parse(putCall[1]!.body as string).cargo_lots[0].freight_rate).toBe(35)
    expect(await screen.findAllByText(/7,?020 USD/)).toHaveLength(2) // list row + results panel
  })

  it('duplicates an estimate under a "(copy)" name', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/voyage-estimates/calculate': [{ status: 200, body: RESULTS }],
      '/voyage-estimates': [
        { status: 200, body: [SAMPLE_ESTIMATE] },
        { status: 201, body: { ...SAMPLE_ESTIMATE, id: 2, name: 'UL-RTM June (copy)' } },
        { status: 200, body: [SAMPLE_ESTIMATE] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/ports': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await screen.findByText('UL-RTM June')
    await user.click(screen.getByRole('button', { name: 'Duplicate' }))

    const call = await waitFor(() => {
      const c = fetchMock.mock.calls.find(([, o]) => o?.method === 'POST')
      if (!c) throw new Error('no POST yet')
      return c
    })
    const body = JSON.parse(call[1]!.body as string)
    expect(body.name).toBe('UL-RTM June (copy)')
    expect(body.port_stops).toHaveLength(2)
  })

  it('deletes an unfixed estimate after confirmation, but offers no delete for a fixed one', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fixed = { ...SAMPLE_ESTIMATE, id: 2, name: 'Fixed one', status: 'fixed', fixture_id: 5 }
    const fetchMock = mockFetchByUrl({
      '/voyage-estimates/calculate': [{ status: 200, body: RESULTS }],
      '/voyage-estimates': [
        { status: 200, body: [SAMPLE_ESTIMATE, fixed] },
        { status: 204, body: null },
        { status: 200, body: [fixed] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
      '/ports': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await screen.findByText('UL-RTM June')
    expect(screen.getAllByRole('button', { name: 'Delete' })).toHaveLength(1)

    await user.click(screen.getByRole('button', { name: 'Delete' }))

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([, o]) => o?.method === 'DELETE')).toBe(true),
    )
  })

  it('opens a fixed estimate read-only', async () => {
    const user = userEvent.setup()
    const fixed = { ...SAMPLE_ESTIMATE, status: 'fixed', fixture_id: 5 }
    mockFetchByUrl(baseHandlers([fixed]))

    render(<VoyageEstimatesPage />)
    await screen.findByText('UL-RTM June')
    await user.click(screen.getByRole('button', { name: 'View' }))

    expect(screen.getByText(/frozen baseline/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Update Estimate' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Estimate Name')).toBeDisabled()
  })

  it('adds a port to the suggestion list', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/ports': [
        { status: 200, body: [] },
        { status: 201, body: { id: 3, name: 'Dudinka' } },
        { status: 200, body: [{ id: 3, name: 'Dudinka' }] },
      ],
      '/voyage-estimates/calculate': [{ status: 200, body: RESULTS }],
      '/voyage-estimates': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())
    await user.type(screen.getByLabelText('New port'), 'Dudinka')
    await user.click(screen.getByRole('button', { name: 'Add Port' }))

    expect(await screen.findByText('Dudinka')).toBeInTheDocument()
    const post = fetchMock.mock.calls.find(([url, o]) => url.endsWith('/ports') && o?.method === 'POST')!
    expect(JSON.parse(post[1]!.body as string)).toEqual({ name: 'Dudinka' })
  })

  it('shows a readable error when the server rejects the estimate', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/voyage-estimates/calculate': [
        { status: 422, body: { detail: [{ loc: ['body', 'port_stops'], msg: 'Field required', type: 'missing' }] } },
      ],
      '/voyage-estimates': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [] }],
      '/ports': [{ status: 200, body: [] }],
    })

    render(<VoyageEstimatesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Calculate Voyage' }))

    expect(await screen.findByText(/port_stops: Field required/)).toBeInTheDocument()
  })
})
