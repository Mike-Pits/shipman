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
})
