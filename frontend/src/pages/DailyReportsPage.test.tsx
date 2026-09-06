import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DailyReportsPage from './DailyReportsPage'

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

const VESSEL = { id: 1, name: 'SP Baltic Trader', imo_number: '9123456', ice_class: 'Arc4' }
const VESSEL_B = { id: 2, name: 'SP Northern Star', imo_number: '9234567', ice_class: 'Arc4' }

const SAMPLE_REPORT = {
  id: 1,
  vessel_id: 1,
  voyage_id: null,
  report_datetime: '2026-05-27 08:00:00',
  raw_text: '1 2705/0800\n2 6457N/04000E\n43 Архангельск\nNNNN',
  fields: { '1': '2705/0800', '2': '6457N/04000E', '43': 'Архангельск' },
  approved: false,
  warnings: [],
  source_message_id: null,
}

describe('DailyReportsPage', () => {
  it('renders the list of daily reports fetched from the API', async () => {
    mockFetchByUrl({
      '/daily-reports/imap-settings': [{ status: 200, body: { folder: 'INBOX' } }],
      '/daily-reports': [{ status: 200, body: [SAMPLE_REPORT] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<DailyReportsPage />)

    expect(await screen.findByText('2026-05-27 08:00:00')).toBeInTheDocument()
    expect(screen.getByText('6457N/04000E')).toBeInTheDocument()
  })

  it('shows a reminder about the explicit date format for historical entries', async () => {
    mockFetchByUrl({
      '/daily-reports/imap-settings': [{ status: 200, body: { folder: 'INBOX' } }],
      '/daily-reports': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<DailyReportsPage />)

    expect(await screen.findByText(/yyyy-mm-dd\/hhmm/i)).toBeInTheDocument()
  })

  it('lets the operator submit a raw DISP-01 message and see the parsed fields', async () => {
    const user = userEvent.setup()
    mockFetchByUrl({
      '/daily-reports/imap-settings': [{ status: 200, body: { folder: 'INBOX' } }],
      '/daily-reports/poll-imap': [],
      '/daily-reports': [
        { status: 200, body: [] },
        { status: 201, body: SAMPLE_REPORT },
        { status: 200, body: [SAMPLE_REPORT] },
      ],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<DailyReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/^vessel/i), '1')
    await user.type(screen.getByLabelText(/paste disp-01/i), '1 2705/0800\n2 6457N/04000E\n43 Архангельск\nNNNN')
    await user.click(screen.getByRole('button', { name: /submit report/i }))

    expect(await screen.findByText('6457N/04000E')).toBeInTheDocument()
  })

  it('lets the operator approve a pending report', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/daily-reports/imap-settings': [{ status: 200, body: { folder: 'INBOX' } }],
      '/daily-reports/1/approve': [{ status: 200, body: { ...SAMPLE_REPORT, approved: true } }],
      '/daily-reports': [{ status: 200, body: [SAMPLE_REPORT] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<DailyReportsPage />)
    expect(await screen.findByText('2026-05-27 08:00:00')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /approve/i }))

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([url]) => (url as string).includes('/1/approve'))).toBe(true),
    )
  })

  it('lets the operator edit an unapproved report and resubmit the corrected text', async () => {
    const user = userEvent.setup()
    const correctedReport = { ...SAMPLE_REPORT, fields: { ...SAMPLE_REPORT.fields, '43': 'Мурманск' } }
    const fetchMock = mockFetchByUrl({
      '/daily-reports/imap-settings': [{ status: 200, body: { folder: 'INBOX' } }],
      '/daily-reports/1': [{ status: 200, body: correctedReport }],
      '/daily-reports': [{ status: 200, body: [SAMPLE_REPORT] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<DailyReportsPage />)
    expect(await screen.findByText('2026-05-27 08:00:00')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^edit/i }))
    const textarea = screen.getByDisplayValue(/Архангельск/)
    await user.clear(textarea)
    await user.type(textarea, '1 2705/0800\n43 Мурманск\nNNNN')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'PUT')).toBe(true),
    )
  })

  it('surfaces a fuel-consumption warning returned by the API', async () => {
    const reportWithWarning = { ...SAMPLE_REPORT, warnings: ['IFO consumption of 30.00 MT exceeds the normal laden rate'] }
    mockFetchByUrl({
      '/daily-reports/imap-settings': [{ status: 200, body: { folder: 'INBOX' } }],
      '/daily-reports': [{ status: 200, body: [reportWithWarning] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<DailyReportsPage />)

    expect(await screen.findByText(/exceeds the normal laden rate/i)).toBeInTheDocument()
  })

  it('lets the operator update the IMAP folder and trigger a poll', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchByUrl({
      '/daily-reports/imap-settings': [
        { status: 200, body: { folder: 'INBOX' } },
        { status: 200, body: { folder: 'DISP01' } },
      ],
      '/daily-reports/poll-imap': [
        { status: 200, body: { ingested: [SAMPLE_REPORT], skipped_duplicates: [], errors: [] } },
      ],
      '/daily-reports': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL] }],
    })

    render(<DailyReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    const folderInput = screen.getByLabelText(/mailbox folder/i)
    await user.clear(folderInput)
    await user.type(folderInput, 'DISP01')
    await user.click(screen.getByRole('button', { name: /save folder/i }))

    await userEvent.selectOptions(screen.getByLabelText(/^vessel/i), '1')
    await user.click(screen.getByRole('button', { name: /poll imap now/i }))

    expect(await screen.findByText(/ingested: 1/i)).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => (url as string).includes('/poll-imap'))).toBe(true)
  })

  it('shows a progress indicator while an IMAP poll is in flight, and clears it when done', async () => {
    const user = userEvent.setup()
    let resolvePoll!: (value: Response) => void
    const pollPromise = new Promise<Response>((resolve) => {
      resolvePoll = resolve
    })
    const fetchMock = vi.fn(async (url: string) => {
      if (url.includes('/poll-imap')) return pollPromise
      if (url.includes('/imap-folder-mapping')) return { ok: false, status: 404, json: async () => ({}) } as Response
      if (url.includes('/imap-settings')) return { ok: true, status: 200, json: async () => ({ folder: 'INBOX' }) } as Response
      if (url.includes('/daily-reports')) return { ok: true, status: 200, json: async () => [] } as Response
      if (url.includes('/vessels')) return { ok: true, status: 200, json: async () => [VESSEL] } as Response
      throw new Error(`unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<DailyReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())
    await userEvent.selectOptions(screen.getByLabelText(/^vessel/i), '1')

    const pollButton = screen.getByRole('button', { name: /poll imap now/i })
    await user.click(pollButton)

    expect(await screen.findByText(/polling/i)).toBeInTheDocument()
    expect(pollButton).toBeDisabled()

    resolvePoll({
      ok: true,
      status: 200,
      json: async () => ({ ingested: [], skipped_duplicates: [], errors: [] }),
    } as Response)

    await waitFor(() => expect(screen.queryByText(/polling/i)).not.toBeInTheDocument())
    expect(pollButton).not.toBeDisabled()
  })

  it('warns when the configured folder is already registered to a different vessel', async () => {
    mockFetchByUrl({
      '/daily-reports/imap-folder-mapping': [{ status: 200, body: { folder: 'INBOX', vessel_id: 2 } }],
      '/daily-reports/imap-settings': [{ status: 200, body: { folder: 'INBOX' } }],
      '/daily-reports': [{ status: 200, body: [] }],
      '/vessels': [{ status: 200, body: [VESSEL, VESSEL_B] }],
    })

    render(<DailyReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await userEvent.selectOptions(screen.getByLabelText(/^vessel/i), '1')

    expect(await screen.findByText(/already registered/i)).toBeInTheDocument()
  })

  it('offers to confirm and retry when polling hits a vessel-mismatch conflict', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
      if (url.includes('/poll-imap')) {
        const body = options?.body ? JSON.parse(options.body as string) : {}
        if (!body.confirm_vessel_change) {
          return {
            ok: false,
            status: 409,
            json: async () => ({ detail: "Folder 'INBOX' was last polled for vessel_id=2, not vessel_id=1." }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ ingested: [], skipped_duplicates: [], errors: [] }),
        } as Response
      }
      if (url.includes('/imap-folder-mapping')) return { ok: false, status: 404, json: async () => ({}) } as Response
      if (url.includes('/imap-settings')) return { ok: true, status: 200, json: async () => ({ folder: 'INBOX' }) } as Response
      if (url.includes('/daily-reports')) return { ok: true, status: 200, json: async () => [] } as Response
      if (url.includes('/vessels')) return { ok: true, status: 200, json: async () => [VESSEL] } as Response
      throw new Error(`unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<DailyReportsPage />)
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())
    await userEvent.selectOptions(screen.getByLabelText(/^vessel/i), '1')
    await user.click(screen.getByRole('button', { name: /poll imap now/i }))

    await waitFor(() => expect(window.confirm).toHaveBeenCalled())
    const pollCalls = fetchMock.mock.calls.filter(([url]) => (url as string).includes('/poll-imap'))
    await waitFor(() => expect(pollCalls.length).toBe(2))
    const secondCallBody = JSON.parse(pollCalls[1][1]!.body as string)
    expect(secondCallBody.confirm_vessel_change).toBe(true)
  })
})
