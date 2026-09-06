import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FixturesPage from './FixturesPage'

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

describe('FixturesPage', () => {
  it('renders the list of fixtures fetched from the API', async () => {
    mockFetchSequence([
      {
        status: 200,
        body: [
          { id: 1, fixture_type: 'voyage_charter', charterer: 'Test Charterer', contract_currency: 'USD', brokers: [] },
        ],
      },
    ])

    render(<FixturesPage />)

    expect(await screen.findByText('Test Charterer')).toBeInTheDocument()
  })

  it('lets the operator create a Voyage Charter fixture', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchSequence([
      { status: 200, body: [] },
      {
        status: 201,
        body: { id: 2, fixture_type: 'voyage_charter', charterer: 'Baltic Traders', contract_currency: 'USD', brokers: [] },
      },
      { status: 200, body: [] },
    ])

    render(<FixturesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.selectOptions(screen.getByLabelText(/fixture type/i), 'voyage_charter')
    await user.type(screen.getByLabelText(/charterer/i), 'Baltic Traders')
    await user.type(screen.getByLabelText(/contract currency/i), 'USD')
    await user.type(screen.getByLabelText(/freight rate$/i), '25')
    await user.selectOptions(screen.getByLabelText(/freight rate basis/i), 'per_tonne')
    await user.type(screen.getByLabelText(/load port/i), 'Ust-Luga')
    await user.type(screen.getByLabelText(/discharge port/i), 'Rotterdam')
    await user.type(screen.getByLabelText(/cargo grade/i), 'gasoil')
    await user.click(screen.getByRole('button', { name: /create fixture/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    const postCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
    const body = JSON.parse(postCall![1].body as string)
    expect(body).toMatchObject({
      fixture_type: 'voyage_charter',
      charterer: 'Baltic Traders',
      contract_currency: 'USD',
      freight_rate: 25,
      freight_rate_basis: 'per_tonne',
      load_port: 'Ust-Luga',
      discharge_port: 'Rotterdam',
      cargo_grade: 'gasoil',
    })
  })

  it('lets the operator create a Time Charter Out fixture with configured hire payment terms', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchSequence([
      { status: 200, body: [] },
      {
        status: 201,
        body: { id: 3, fixture_type: 'time_charter_out', charterer: 'Northern Charterers', contract_currency: 'USD', brokers: [] },
      },
      { status: 200, body: [] },
    ])

    render(<FixturesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.selectOptions(screen.getByLabelText(/fixture type/i), 'time_charter_out')
    await user.type(screen.getByLabelText(/charterer/i), 'Northern Charterers')
    await user.type(screen.getByLabelText(/contract currency/i), 'RUB')
    await user.type(screen.getByLabelText(/hire rate$/i), '9000')
    await user.selectOptions(screen.getByLabelText(/hire rate basis/i), 'daily')
    await user.type(screen.getByLabelText(/charter period from/i), '2026-06-01')
    await user.type(screen.getByLabelText(/charter period to/i), '2026-08-30')
    await user.selectOptions(screen.getByLabelText(/hire payment basis/i), 'advance')
    await user.type(screen.getByLabelText(/hire payment frequency/i), '30')
    await user.click(screen.getByRole('button', { name: /create fixture/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    const postCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
    const body = JSON.parse(postCall![1].body as string)
    expect(body).toMatchObject({
      fixture_type: 'time_charter_out',
      hire_rate: 9000,
      hire_rate_basis: 'daily',
      charter_period_from: '2026-06-01',
      charter_period_to: '2026-08-30',
      hire_payment_basis: 'advance',
      hire_payment_frequency_days: 30,
    })
  })

  it('lets the operator create a COA fixture', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchSequence([
      { status: 200, body: [] },
      {
        status: 201,
        body: { id: 4, fixture_type: 'coa', charterer: 'Term Charterer', contract_currency: 'USD', brokers: [] },
      },
      { status: 200, body: [] },
    ])

    render(<FixturesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.selectOptions(screen.getByLabelText(/fixture type/i), 'coa')
    await user.type(screen.getByLabelText(/charterer/i), 'Term Charterer')
    await user.type(screen.getByLabelText(/contract currency/i), 'USD')
    await user.type(screen.getByLabelText(/contract period from/i), '2026-01-01')
    await user.type(screen.getByLabelText(/contract period to/i), '2026-12-31')
    await user.type(screen.getByLabelText(/total contracted quantity/i), '60000')
    await user.type(screen.getByLabelText(/rate per tonne/i), '28')
    await user.click(screen.getByRole('button', { name: /create fixture/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    const postCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
    const body = JSON.parse(postCall![1].body as string)
    expect(body).toMatchObject({
      fixture_type: 'coa',
      contract_period_from: '2026-01-01',
      contract_period_to: '2026-12-31',
      total_contracted_quantity: 60000,
      rate_per_tonne: 28,
    })
  })

  it('lets the operator add up to 3 brokers with commission percentages', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchSequence([
      { status: 200, body: [] },
      {
        status: 201,
        body: { id: 5, fixture_type: 'voyage_charter', charterer: 'Baltic Traders', contract_currency: 'USD', brokers: [] },
      },
      { status: 200, body: [] },
    ])

    render(<FixturesPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.selectOptions(screen.getByLabelText(/fixture type/i), 'voyage_charter')
    await user.type(screen.getByLabelText(/charterer/i), 'Baltic Traders')
    await user.type(screen.getByLabelText(/contract currency/i), 'USD')
    await user.type(screen.getByLabelText(/broker 1 name/i), 'Acme Brokers')
    await user.type(screen.getByLabelText(/broker 1 commission/i), '1.25')
    await user.click(screen.getByRole('button', { name: /create fixture/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    const postCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
    const body = JSON.parse(postCall![1].body as string)
    expect(body.brokers).toEqual([{ broker_name: 'Acme Brokers', commission_percentage: 1.25 }])
  })

  it('lets the operator edit a fixture, shows a warning while editing, and submits a PUT', async () => {
    const user = userEvent.setup()
    const existingFixture = {
      id: 6,
      fixture_type: 'voyage_charter',
      charterer: 'Baltic Traders',
      contract_currency: 'USD',
      freight_rate: 25,
      freight_rate_basis: 'per_tonne',
      load_port: 'Ust-Luga',
      discharge_port: 'Rotterdam',
      cargo_grade: 'gasoil',
      brokers: [],
    }
    const fetchMock = mockFetchSequence([
      { status: 200, body: [existingFixture] },
      { status: 200, body: { ...existingFixture, charterer: 'Updated Charterer' } },
      { status: 200, body: [{ ...existingFixture, charterer: 'Updated Charterer' }] },
    ])

    render(<FixturesPage />)
    expect(await screen.findByText('Baltic Traders')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /edit/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(/editing.*existing fixture/i)
    expect(screen.getByLabelText(/charterer/i)).toHaveValue('Baltic Traders')

    const chartererInput = screen.getByLabelText(/charterer/i)
    await user.clear(chartererInput)
    await user.type(chartererInput, 'Updated Charterer')
    await user.click(screen.getByRole('button', { name: /update fixture/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    const putCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'PUT')
    expect(putCall?.[0]).toContain('/fixtures/6')
    expect(JSON.parse(putCall![1].body as string).charterer).toBe('Updated Charterer')
  })
})
