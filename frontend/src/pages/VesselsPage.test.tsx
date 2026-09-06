import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VesselsPage from './VesselsPage'

function mockFetchSequence(responses: Array<{ status: number; body: unknown }>) {
  let call = 0
  const fetchMock = vi.fn(async () => {
    const { status, body } = responses[Math.min(call, responses.length - 1)]
    call += 1
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

describe('VesselsPage', () => {
  it('renders the list of vessels fetched from the API', async () => {
    mockFetchSequence([
      {
        status: 200,
        body: [
          { id: 1, name: 'SP Baltic Trader', imo_number: '9123456', ice_class: 'Arc4' },
          { id: 2, name: 'SP Northern Star', imo_number: '9234567', ice_class: 'Arc4' },
        ],
      },
    ])

    render(<VesselsPage />)

    expect(await screen.findByText('SP Baltic Trader')).toBeInTheDocument()
    expect(screen.getByText('SP Northern Star')).toBeInTheDocument()
  })

  it('lets the operator register a vessel and shows it in the list afterward', async () => {
    const user = userEvent.setup()
    mockFetchSequence([
      { status: 200, body: [] }, // initial list load
      {
        status: 201,
        body: { id: 3, name: 'SP New Vessel', imo_number: '9345678', ice_class: 'Arc7' },
      },
      {
        status: 200,
        body: [{ id: 3, name: 'SP New Vessel', imo_number: '9345678', ice_class: 'Arc7' }],
      }, // refetched list after creation
    ])

    render(<VesselsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.type(screen.getByLabelText(/name/i), 'SP New Vessel')
    await user.type(screen.getByLabelText(/imo number/i), '9345678')
    await user.type(screen.getByLabelText(/flag/i), 'Russia')
    await user.type(screen.getByLabelText(/year built/i), '2020')
    await user.type(screen.getByLabelText(/dwt/i), '8000')
    await user.type(screen.getByLabelText(/loa/i), '120')
    await user.type(screen.getByLabelText(/beam/i), '18')
    await user.type(screen.getByLabelText(/draft/i), '7')
    await user.type(screen.getByLabelText(/cargo tank capacity/i), '9000')
    await user.type(screen.getByLabelText(/ice class/i), 'Arc7')
    await user.type(screen.getByLabelText(/engine power/i), '4000')
    await user.click(screen.getByRole('button', { name: /register vessel/i }))

    expect(await screen.findByText('SP New Vessel')).toBeInTheDocument()
  })

  it('lets the operator enter fuel consumption rates per mode and sends them with the vessel', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchSequence([
      { status: 200, body: [] },
      { status: 201, body: { id: 4, name: 'SP Fuel Test', imo_number: '9456789', ice_class: 'Arc4' } },
      { status: 200, body: [] },
    ])

    render(<VesselsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.type(screen.getByLabelText(/name/i), 'SP Fuel Test')
    await user.type(screen.getByLabelText(/imo number/i), '9456789')
    await user.type(screen.getByLabelText(/flag/i), 'Russia')
    await user.type(screen.getByLabelText(/year built/i), '2020')
    await user.type(screen.getByLabelText(/dwt/i), '8000')
    await user.type(screen.getByLabelText(/loa/i), '120')
    await user.type(screen.getByLabelText(/beam/i), '18')
    await user.type(screen.getByLabelText(/draft/i), '7')
    await user.type(screen.getByLabelText(/cargo tank capacity/i), '9000')
    await user.type(screen.getByLabelText(/ice class/i), 'Arc4')
    await user.type(screen.getByLabelText(/engine power/i), '4000')

    await user.type(screen.getByLabelText(/laden ifo/i), '18.5')
    await user.type(screen.getByLabelText(/laden mgo/i), '0.5')
    await user.type(screen.getByLabelText(/ballast ifo/i), '16')
    await user.type(screen.getByLabelText(/ballast mgo/i), '0.5')
    await user.type(screen.getByLabelText(/idle.*anchor ifo/i), '2')
    await user.type(screen.getByLabelText(/idle.*anchor mgo/i), '0.2')
    await user.type(screen.getByLabelText(/discharging ifo/i), '3.5')
    await user.type(screen.getByLabelText(/discharging mgo/i), '1')

    await user.click(screen.getByRole('button', { name: /register vessel/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    const postCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
    const body = JSON.parse(postCall![1].body as string)
    expect(body.fuel_consumption_profiles).toEqual([
      { mode: 'laden', ifo_mt_per_day: 18.5, mgo_mt_per_day: 0.5 },
      { mode: 'ballast', ifo_mt_per_day: 16, mgo_mt_per_day: 0.5 },
      { mode: 'idle_anchor', ifo_mt_per_day: 2, mgo_mt_per_day: 0.2 },
      { mode: 'discharging', ifo_mt_per_day: 3.5, mgo_mt_per_day: 1 },
    ])
  })

  it('lets the operator delete a vessel after confirming, and removes it from the list', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = mockFetchSequence([
      {
        status: 200,
        body: [{ id: 1, name: 'SP Baltic Trader', imo_number: '9123456', ice_class: 'Arc4' }],
      },
      { status: 204, body: undefined },
      { status: 200, body: [] },
    ])

    render(<VesselsPage />)
    expect(await screen.findByText('SP Baltic Trader')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /delete/i }))

    expect(window.confirm).toHaveBeenCalled()
    await waitFor(() => expect(screen.queryByText('SP Baltic Trader')).not.toBeInTheDocument())
    const deleteCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'DELETE')
    expect(deleteCall?.[0]).toContain('/vessels/1')
  })

  it('does not delete the vessel when the operator cancels the confirmation', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const fetchMock = mockFetchSequence([
      {
        status: 200,
        body: [{ id: 1, name: 'SP Baltic Trader', imo_number: '9123456', ice_class: 'Arc4' }],
      },
    ])

    render(<VesselsPage />)
    expect(await screen.findByText('SP Baltic Trader')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /delete/i }))

    expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false)
    expect(screen.getByText('SP Baltic Trader')).toBeInTheDocument()
  })

  it('lets the operator edit a vessel: clicking Edit pre-fills the form and submits a PUT', async () => {
    const user = userEvent.setup()
    const existingVessel = {
      id: 5,
      name: 'SP Baltic Trader',
      imo_number: '9123456',
      flag: 'Russia',
      year_built: 2015,
      vessel_type: 'clean/product tanker',
      dwt: 8500,
      loa: 120.5,
      beam: 18.2,
      draft: 7.1,
      cargo_tank_capacity_cbm: 9800,
      ice_class: 'Arc4',
      engine_power_kw: 4500,
      fuel_consumption_profiles: [
        { id: 1, mode: 'laden', ifo_mt_per_day: 18.5, mgo_mt_per_day: 0.5 },
        { id: 2, mode: 'ballast', ifo_mt_per_day: 16, mgo_mt_per_day: 0.5 },
        { id: 3, mode: 'idle_anchor', ifo_mt_per_day: 2, mgo_mt_per_day: 0.2 },
        { id: 4, mode: 'discharging', ifo_mt_per_day: 3.5, mgo_mt_per_day: 1 },
      ],
    }
    const updatedVessel = { ...existingVessel, ice_class: 'Arc7' }
    const fetchMock = mockFetchSequence([
      { status: 200, body: [existingVessel] },
      { status: 200, body: updatedVessel },
      { status: 200, body: [updatedVessel] },
    ])

    render(<VesselsPage />)
    expect(await screen.findByText('SP Baltic Trader')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /edit/i }))

    expect(screen.getByLabelText(/^name/i)).toHaveValue('SP Baltic Trader')
    expect(screen.getByLabelText(/laden ifo/i)).toHaveValue(18.5)

    const iceClassInput = screen.getByLabelText(/ice class/i)
    await user.clear(iceClassInput)
    await user.type(iceClassInput, 'Arc7')
    await user.click(screen.getByRole('button', { name: /update vessel/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    const putCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'PUT')
    expect(putCall?.[0]).toContain('/vessels/5')
    const body = JSON.parse(putCall![1].body as string)
    expect(body.ice_class).toBe('Arc7')
    expect(body.name).toBe('SP Baltic Trader')
    expect(body.fuel_consumption_profiles).toEqual([
      { mode: 'laden', ifo_mt_per_day: 18.5, mgo_mt_per_day: 0.5 },
      { mode: 'ballast', ifo_mt_per_day: 16, mgo_mt_per_day: 0.5 },
      { mode: 'idle_anchor', ifo_mt_per_day: 2, mgo_mt_per_day: 0.2 },
      { mode: 'discharging', ifo_mt_per_day: 3.5, mgo_mt_per_day: 1 },
    ])
  })

  it('lets the operator save an edit even when the vessel has genuine zero-value numeric fields', async () => {
    // Regression test: value={form.field || ''} used to render a real 0 as an empty
    // string, which fails native `required` validation and silently blocks submission.
    const user = userEvent.setup()
    const zeroValueVessel = {
      id: 9,
      name: 'test_ship',
      imo_number: 'test_nr',
      flag: 'string',
      year_built: 0,
      vessel_type: 'string',
      dwt: 0,
      loa: 0,
      beam: 0,
      draft: 0,
      cargo_tank_capacity_cbm: 0,
      ice_class: 'string',
      engine_power_kw: 0,
      fuel_consumption_profiles: [],
    }
    const fetchMock = mockFetchSequence([
      { status: 200, body: [zeroValueVessel] },
      { status: 200, body: { ...zeroValueVessel, ice_class: 'Arc4' } },
      { status: 200, body: [{ ...zeroValueVessel, ice_class: 'Arc4' }] },
    ])

    render(<VesselsPage />)
    expect(await screen.findByText('test_ship')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /edit/i }))
    const iceClassInput = screen.getByLabelText(/ice class/i)
    await user.clear(iceClassInput)
    await user.type(iceClassInput, 'Arc4')
    await user.click(screen.getByRole('button', { name: /update vessel/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    const putCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'PUT')
    expect(putCall).toBeDefined()
    const body = JSON.parse(putCall![1].body as string)
    expect(body.dwt).toBe(0)
    expect(body.ice_class).toBe('Arc4')
  })
})
