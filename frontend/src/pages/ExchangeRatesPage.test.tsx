import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ExchangeRatesPage from './ExchangeRatesPage'

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

const TODAY = new Date().toISOString().slice(0, 10)

describe('ExchangeRatesPage', () => {
  it("renders today's rate when one is already stored", async () => {
    mockFetchByUrl({
      [`/exchange-rates/${TODAY}`]: [
        { status: 200, body: { id: 1, rate_date: TODAY, usd_rub_rate: 91.5, manual_override: false, stale: false } },
      ],
    })

    render(<ExchangeRatesPage />)

    expect(await screen.findByText(/91\.5/)).toBeInTheDocument()
  })

  it('shows a not-fetched message when no rate exists for today yet', async () => {
    mockFetchByUrl({
      [`/exchange-rates/${TODAY}`]: [{ status: 404, body: { detail: 'No rate stored for this date' } }],
    })

    render(<ExchangeRatesPage />)

    expect(await screen.findByText(/no rate fetched for today/i)).toBeInTheDocument()
  })

  it("lets the operator fetch today's rate", async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      [`/exchange-rates/${TODAY}`]: [{ status: 404, body: {} }],
      '/exchange-rates/fetch': [
        { status: 200, body: { id: 2, rate_date: TODAY, usd_rub_rate: 92.1, manual_override: false, stale: false } },
      ],
    })

    render(<ExchangeRatesPage />)
    await waitFor(() => expect(screen.getByRole('button', { name: /fetch today/i })).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /fetch today/i }))

    expect(await screen.findByText(/92\.1/)).toBeInTheDocument()
  })

  it('shows a stale warning when the fetch falls back to the last known rate', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      [`/exchange-rates/${TODAY}`]: [{ status: 404, body: {} }],
      '/exchange-rates/fetch': [
        { status: 200, body: { id: 3, rate_date: '2026-08-01', usd_rub_rate: 90.0, manual_override: false, stale: true } },
      ],
    })

    render(<ExchangeRatesPage />)
    await user.click(await screen.findByRole('button', { name: /fetch today/i }))

    expect(await screen.findByText(/rate fetch failed/i)).toBeInTheDocument()
  })

  it('lets the operator look up a rate for a specific date', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      [`/exchange-rates/${TODAY}`]: [{ status: 404, body: {} }],
      '/exchange-rates/2026-06-01': [
        { status: 200, body: { id: 4, rate_date: '2026-06-01', usd_rub_rate: 80.0, manual_override: false, stale: false } },
      ],
    })

    render(<ExchangeRatesPage />)
    await user.type(screen.getByLabelText(/^date/i), '2026-06-01')
    await user.click(screen.getByRole('button', { name: /look up/i }))

    expect(await screen.findByLabelText(/rate \(usd\/rub\)/i)).toHaveValue(80)
  })

  it('tells the operator when no rate is stored for the looked-up date', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      [`/exchange-rates/${TODAY}`]: [{ status: 404, body: {} }],
      '/exchange-rates/2026-06-02': [{ status: 404, body: {} }],
    })

    render(<ExchangeRatesPage />)
    await user.type(screen.getByLabelText(/^date/i), '2026-06-02')
    await user.click(screen.getByRole('button', { name: /look up/i }))

    expect(await screen.findByText(/no rate stored for this date/i)).toBeInTheDocument()
  })

  it('lets the operator set/override a rate for a date', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      [`/exchange-rates/${TODAY}`]: [{ status: 404, body: {} }],
      '/exchange-rates/2026-06-03': [
        { status: 404, body: {} },
        { status: 200, body: { id: 5, rate_date: '2026-06-03', usd_rub_rate: 85.0, manual_override: true, stale: false } },
      ],
    })

    render(<ExchangeRatesPage />)
    await user.type(screen.getByLabelText(/^date/i), '2026-06-03')
    await user.click(screen.getByRole('button', { name: /look up/i }))
    await screen.findByText(/no rate stored for this date/i)

    await user.type(screen.getByLabelText(/rate \(usd\/rub\)/i), '85')
    await user.click(screen.getByRole('button', { name: /save rate/i }))

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'PUT')).toBe(true),
    )
    expect(await screen.findByText(/manually overridden/i)).toBeInTheDocument()
  })
})
