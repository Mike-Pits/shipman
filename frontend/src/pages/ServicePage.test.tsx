import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ServicePage from './ServicePage'

type Reply = { status: number; body: unknown }

// Keys are "METHOD /path-substring"; the first matching key wins, so list specific ones first.
function mockFetch(handlers: Record<string, Reply[]>) {
  const counters: Record<string, number> = {}
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    const method = options?.method ?? 'GET'
    const key = Object.keys(handlers).find((k) => {
      const [m, ...rest] = k.split(' ')
      return m === method && url.includes(rest.join(' '))
    })
    if (!key) throw new Error(`unexpected request ${method} ${url}`)
    const i = counters[key] ?? 0
    counters[key] = i + 1
    const { status, body } = handlers[key][Math.min(i, handlers[key].length - 1)]
    return { ok: status < 400, status, json: async () => body } as Response
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

const BACKUP = {
  name: 'shipman-20261014-090000-auto.db',
  kind: 'auto',
  created_at: '2026-10-14T09:00:00',
  size_bytes: 1048576,
  sha256: 'a'.repeat(64),
  integrity_ok: true,
  fk_violations: [],
  row_counts: { vessels: 2 },
  restore_blockers: [],
}

const STATUS = {
  database_path: '/data/shipman.db',
  database_size_bytes: 2097152,
  backup_dir: '/data/backups',
  backup_dir_is_default: true,
  auto_backup_enabled: true,
  keep_daily: 14,
  keep_monthly: 12,
  backup_count: 1,
  last_backup: BACKUP,
  last_backup_age_hours: 3,
}

const base = (overrides: Record<string, Reply[]> = {}) => ({
  ...overrides,
  'GET /service/status': [{ status: 200, body: STATUS }],
  'GET /service/backups': [{ status: 200, body: [BACKUP] }],
})

describe('ServicePage', () => {
  it('shows the database, backup folder, last backup and the backups list', async () => {
    mockFetch(base())

    render(<ServicePage />)

    expect(await screen.findByText(/\/data\/shipman\.db/)).toBeInTheDocument()
    expect(screen.getByText('/data/backups')).toBeInTheDocument()
    expect(screen.getByText(/3 h ago/)).toBeInTheDocument()
    expect(screen.getByText('shipman-20261014-090000-auto.db')).toBeInTheDocument()
    expect(screen.getByText('Automatic')).toBeInTheDocument()
    expect(screen.getAllByText('Verified')).toHaveLength(2) // column header + badge
    expect(screen.queryByText('Backup overdue')).not.toBeInTheDocument()
  })

  it('flags an overdue backup when none exists or the last one is over 48 hours old', async () => {
    mockFetch({
      'GET /service/status': [{ status: 200, body: { ...STATUS, last_backup: null, last_backup_age_hours: null } }],
      'GET /service/backups': [{ status: 200, body: [] }],
    })

    render(<ServicePage />)

    expect(await screen.findByText('Backup overdue')).toBeInTheDocument()
    expect(screen.getByText('No backups yet.')).toBeInTheDocument()
  })

  it('makes a backup on request and reports it', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetch(
      base({ 'POST /service/backups': [{ status: 201, body: { ...BACKUP, kind: 'manual', name: 'shipman-x-manual.db' } }] }),
    )

    render(<ServicePage />)
    await user.click(await screen.findByRole('button', { name: 'Back up now' }))

    expect(await screen.findByText(/shipman-x-manual\.db created and verified/)).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([, o]) => o?.method === 'POST')).toBe(true)
  })

  it('only restores after the operator types RESTORE', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetch(
      base({
        'POST /restore': [{ status: 200, body: { restored: BACKUP.name, safety_backup: 'shipman-safe-pre-restore.db' } }],
      }),
    )

    render(<ServicePage />)
    await user.click(await screen.findByRole('button', { name: 'Restore' }))

    const confirm = screen.getByRole('button', { name: 'Restore this backup' })
    expect(confirm).toBeDisabled()
    await user.type(screen.getByLabelText(/Type RESTORE to confirm/), 'RESTORE')
    expect(confirm).toBeEnabled()
    await user.click(confirm)

    expect(await screen.findByText(/shipman-safe-pre-restore\.db/)).toBeInTheDocument()
    const call = fetchMock.mock.calls.find(([url]) => url.includes('/restore'))!
    expect(JSON.parse(call[1]!.body as string)).toEqual({ confirm: 'RESTORE' })
  })

  it('disables restore and explains why when the backup is from an older version', async () => {
    mockFetch({
      'GET /service/status': [{ status: 200, body: STATUS }],
      'GET /service/backups': [{ status: 200, body: [{ ...BACKUP, restore_blockers: ['vessels: flag'] }] }],
    })

    render(<ServicePage />)

    expect(await screen.findByText(/it lacks: vessels: flag/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restore' })).toBeDisabled()
  })

  it('deletes a backup after confirmation', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = mockFetch(base({ 'DELETE /service/backups': [{ status: 204, body: null }] }))

    render(<ServicePage />)
    await user.click(await screen.findByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(fetchMock.mock.calls.some(([, o]) => o?.method === 'DELETE')).toBe(true))
  })

  it('imports a backup file by uploading its raw bytes', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetch(
      base({ 'POST /service/backups/import': [{ status: 201, body: { ...BACKUP, kind: 'imported', name: 'shipman-imp.db' } }] }),
    )

    render(<ServicePage />)
    await screen.findByRole('button', { name: 'Back up now' })
    const file = new File(['SQLite format 3\0'], 'laptop.db')
    await user.upload(screen.getByLabelText('Import backup file…', { selector: 'input' }), file)

    expect(await screen.findByText(/Imported shipman-imp\.db/)).toBeInTheDocument()
    const call = fetchMock.mock.calls.find(([url]) => url.includes('/import'))!
    expect(call[1]!.body).toBe(file)
  })

  it('compacts the database and reports the sizes', async () => {
    const user = userEvent.setup()
    mockFetch(
      base({ 'POST /service/compact': [{ status: 200, body: { size_before: 2097152, size_after: 1048576, safety_backup: 's.db' } }] }),
    )

    render(<ServicePage />)
    await user.click(await screen.findByRole('button', { name: 'Compact database' }))

    expect(await screen.findByText(/2\.0 MB → 1\.0 MB/)).toBeInTheDocument()
  })

  it('runs a health check and names orphaned records', async () => {
    const user = userEvent.setup()
    mockFetch(
      base({
        'GET /service/health': [
          {
            status: 200,
            body: {
              integrity_ok: true,
              integrity_problems: [],
              fk_violations: [{ table: 'invoice_lines', parent: 'invoices', rows: 3 }],
              row_counts: { vessels: 2 },
              size_bytes: 2097152,
              reclaimable_bytes: 4096,
              journal_mode: 'delete',
              sqlite_version: '3.46.1',
              checked_at: '2026-10-14T10:00:00',
            },
          },
        ],
      }),
    )

    render(<ServicePage />)
    await user.click(await screen.findByRole('button', { name: 'Run health check' }))

    expect(await screen.findByText('Database structure OK')).toBeInTheDocument()
    expect(screen.getByText('Orphaned records found')).toBeInTheDocument()
    expect(screen.getByText(/3 row\(s\) in invoice_lines refer to a missing record in invoices/)).toBeInTheDocument()
  })

  it('saves backup settings', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetch(base({ 'PUT /service/settings': [{ status: 200, body: STATUS }] }))

    render(<ServicePage />)
    const folder = await screen.findByLabelText('Backup folder', { selector: 'input' })
    await user.type(folder, 'D:\\ShipManBackups')
    await user.click(screen.getByLabelText('Automatic daily backup'))
    await user.click(screen.getByRole('button', { name: 'Save settings' }))

    const call = await waitFor(() => {
      const c = fetchMock.mock.calls.find(([, o]) => o?.method === 'PUT')
      if (!c) throw new Error('no PUT yet')
      return c
    })
    expect(JSON.parse(call[1]!.body as string)).toEqual({
      backup_dir: 'D:\\ShipManBackups',
      auto_backup_enabled: false,
      keep_daily: 14,
      keep_monthly: 12,
    })
  })

  it('shows the server error when an action fails', async () => {
    const user = userEvent.setup()
    mockFetch(base({ 'POST /service/backups': [{ status: 422, body: { detail: 'Backup folder is not writable' } }] }))

    render(<ServicePage />)
    await user.click(await screen.findByRole('button', { name: 'Back up now' }))

    expect(await screen.findByText('Backup folder is not writable')).toBeInTheDocument()
  })
})
