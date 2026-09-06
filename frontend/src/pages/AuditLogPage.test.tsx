import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AuditLogPage from './AuditLogPage'

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

const ENTRY_1 = {
  id: 1,
  table_name: 'vessels',
  record_id: 1,
  action: 'insert',
  old_values: null,
  new_values: '{"id": 1, "name": "MV Arctic"}',
  user: 'operator',
  timestamp: '2026-06-01T10:00:00+00:00',
}

const ENTRY_2 = {
  id: 2,
  table_name: 'payments',
  record_id: 5,
  action: 'update',
  old_values: '{"status": "draft"}',
  new_values: '{"status": "paid"}',
  user: 'operator',
  timestamp: '2026-06-02T11:00:00+00:00',
}

describe('AuditLogPage', () => {
  it('renders the audit log entries', async () => {
    mockFetchByUrl({
      '/audit-log': [{ status: 200, body: [ENTRY_1, ENTRY_2] }],
    })

    render(<AuditLogPage />)

    const table = await screen.findByRole('table')
    expect(within(table).getByText('vessels')).toBeInTheDocument()
    expect(within(table).getByText('payments')).toBeInTheDocument()
    expect(within(table).getByText('insert')).toBeInTheDocument()
    expect(within(table).getByText('update')).toBeInTheDocument()
  })

  it('lets the operator filter the audit log by table', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/audit-log': [{ status: 200, body: [ENTRY_1, ENTRY_2] }],
    })

    render(<AuditLogPage />)
    const table = await screen.findByRole('table')
    within(table).getByText('vessels')

    await userEvent.selectOptions(screen.getByLabelText(/table/i), 'payments')

    expect(within(table).queryByText('vessels')).not.toBeInTheDocument()
    expect(within(table).getByText('payments')).toBeInTheDocument()
    void user
  })

  it('lets the operator view the old/new values of an entry', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/audit-log': [{ status: 200, body: [ENTRY_2] }],
    })

    render(<AuditLogPage />)
    await screen.findByRole('table')

    await user.click(screen.getByRole('button', { name: /view changes/i }))

    expect(await screen.findByText(/"status": "draft"/)).toBeInTheDocument()
    expect(screen.getByText(/"status": "paid"/)).toBeInTheDocument()
  })
})
