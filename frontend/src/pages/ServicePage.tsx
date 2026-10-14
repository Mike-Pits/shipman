import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  EXPORT_URL,
  backupDownloadUrl,
  compactDatabase,
  createBackup,
  deleteBackup,
  getHealthReport,
  getServiceStatus,
  importBackup,
  listBackups,
  restoreBackup,
  updateServiceSettings,
} from '../api/service'
import Badge, { type BadgeTone } from '../components/ui/Badge'
import type { BackupEntry, BackupKind, HealthReport, ServiceSettings, ServiceStatus } from '../api/types'

const RESTORE_WORD = 'RESTORE'

const KIND_KEYS: Record<BackupKind, string> = {
  manual: 'service.kindManual',
  auto: 'service.kindAuto',
  'pre-restore': 'service.kindPreRestore',
  'pre-compact': 'service.kindPreCompact',
  imported: 'service.kindImported',
  external: 'service.kindExternal',
}

const KIND_TONES: Record<BackupKind, BadgeTone> = {
  manual: 'info',
  auto: 'neutral',
  'pre-restore': 'warning',
  'pre-compact': 'warning',
  imported: 'info',
  external: 'neutral',
}

const formatBytes = (n: number) =>
  n < 1024 ? `${n} B` : n < 1024 * 1024 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`

const formatWhen = (iso: string) => iso.replace('T', ' ')

export default function ServicePage() {
  const { t } = useTranslation()
  const [status, setStatus] = useState<ServiceStatus | null>(null)
  const [backups, setBackups] = useState<BackupEntry[]>([])
  const [settings, setSettings] = useState<ServiceSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [restoring, setRestoring] = useState<string | null>(null)
  const [confirmText, setConfirmText] = useState('')
  const [health, setHealth] = useState<HealthReport | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const refresh = async () => {
    const [s, b] = await Promise.all([getServiceStatus(), listBackups()])
    setStatus(s)
    setBackups(b)
    setSettings({
      backup_dir: s.backup_dir_is_default ? '' : s.backup_dir,
      auto_backup_enabled: s.auto_backup_enabled,
      keep_daily: s.keep_daily,
      keep_monthly: s.keep_monthly,
    })
  }

  useEffect(() => {
    refresh()
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  const run = async (label: string, action: () => Promise<string | void>) => {
    setBusy(label)
    setError(null)
    setNotice(null)
    try {
      const message = await action()
      if (message) setNotice(message)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setBusy(null)
    }
  }

  const handleBackup = () =>
    run('backup', async () => {
      const made = await createBackup()
      return t('service.backupDone', { name: made.name })
    })

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    run('import', async () => {
      const made = await importBackup(file)
      return t('service.importDone', { name: made.name })
    })
  }

  const handleDelete = (b: BackupEntry) => {
    if (!window.confirm(t('service.deleteConfirm', { name: b.name }))) return
    run('delete', () => deleteBackup(b.name))
  }

  const handleRestore = (b: BackupEntry) =>
    run('restore', async () => {
      const result = await restoreBackup(b.name, confirmText)
      setRestoring(null)
      setConfirmText('')
      return t('service.restoreDone', { name: result.restored, safety: result.safety_backup })
    })

  const handleCompact = () =>
    run('compact', async () => {
      const r = await compactDatabase()
      return t('service.compactDone', { before: formatBytes(r.size_before), after: formatBytes(r.size_after) })
    })

  const handleHealth = () =>
    run('health', async () => {
      setHealth(await getHealthReport())
    })

  const handleSaveSettings = (e: React.FormEvent) => {
    e.preventDefault()
    if (!settings) return
    run('settings', async () => {
      await updateServiceSettings({ ...settings, backup_dir: settings.backup_dir?.trim() || null })
      return t('service.settingsSaved')
    })
  }

  if (loading) return <p>{t('common.loading')}</p>

  const stale = status && (status.last_backup_age_hours === null || status.last_backup_age_hours > 48)

  return (
    <div>
      <h1>{t('service.title')}</h1>

      {error && (
        <p role="alert" className="alert-danger">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}

      {status && (
        <>
          <h2>{t('service.backupsHeading')}</h2>
          <dl className="service-facts">
            <dt>{t('service.database')}</dt>
            <dd>
              {status.database_path} ({formatBytes(status.database_size_bytes)})
            </dd>
            <dt>{t('service.backupFolder')}</dt>
            <dd>{status.backup_dir}</dd>
            <dt>{t('service.lastBackup')}</dt>
            <dd>
              {status.last_backup ? (
                <>
                  {formatWhen(status.last_backup.created_at)} (
                  {t('service.hoursAgo', { hours: Math.round(status.last_backup_age_hours ?? 0) })})
                </>
              ) : (
                t('service.never')
              )}
              {stale && <Badge tone="danger">{t('service.backupOverdue')}</Badge>}
            </dd>
            <dt>{t('service.automatic')}</dt>
            <dd>
              {status.auto_backup_enabled
                ? t('service.automaticOn', { daily: status.keep_daily, monthly: status.keep_monthly })
                : t('service.automaticOff')}
            </dd>
          </dl>

          <div className="estimate-actions">
            <button type="button" disabled={busy !== null} onClick={handleBackup}>
              {t('service.backupNow')}
            </button>
            <button type="button" disabled={busy !== null} onClick={() => fileInput.current?.click()}>
              {t('service.importButton')}
            </button>
            <input
              ref={fileInput}
              type="file"
              accept=".db,.sqlite,.sqlite3"
              hidden
              aria-label={t('service.importButton')}
              onChange={handleImport}
            />
          </div>
          <p className="hint">{t('service.offMachineHint')}</p>
        </>
      )}

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{t('service.colCreated')}</th>
              <th>{t('service.colType')}</th>
              <th>{t('service.colSize')}</th>
              <th>{t('service.colVerified')}</th>
              <th>{t('service.colFile')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {backups.length === 0 && (
              <tr>
                <td colSpan={6}>{t('service.noBackups')}</td>
              </tr>
            )}
            {backups.map((b) => (
              <tr key={b.name}>
                <td>{formatWhen(b.created_at)}</td>
                <td>
                  <Badge tone={KIND_TONES[b.kind]}>{t(KIND_KEYS[b.kind])}</Badge>
                </td>
                <td>{formatBytes(b.size_bytes)}</td>
                <td>
                  {b.integrity_ok === null ? (
                    '—'
                  ) : b.integrity_ok && b.fk_violations.length === 0 ? (
                    <Badge tone="success">{t('service.verifiedOk')}</Badge>
                  ) : (
                    <Badge tone="danger">{t('service.verifiedProblem')}</Badge>
                  )}
                </td>
                <td>{b.name}</td>
                <td>
                  <a href={backupDownloadUrl(b.name)} download>
                    {t('service.download')}
                  </a>{' '}
                  <button
                    type="button"
                    disabled={busy !== null || b.restore_blockers.length > 0}
                    onClick={() => {
                      setRestoring(restoring === b.name ? null : b.name)
                      setConfirmText('')
                    }}
                  >
                    {t('service.restore')}
                  </button>
                  <button type="button" disabled={busy !== null} onClick={() => handleDelete(b)}>
                    {t('common.delete')}
                  </button>
                  {b.restore_blockers.length > 0 && (
                    <p role="alert">{t('service.cannotRestore', { columns: b.restore_blockers.join('; ') })}</p>
                  )}
                  {restoring === b.name && (
                    <form
                      onSubmit={(e) => {
                        e.preventDefault()
                        handleRestore(b)
                      }}
                    >
                      <p role="alert">{t('service.restoreWarning')}</p>
                      <label>
                        {t('service.typeToConfirm', { word: RESTORE_WORD })}
                        <input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} />
                      </label>
                      <button type="submit" disabled={confirmText !== RESTORE_WORD || busy !== null}>
                        {t('service.confirmRestore')}
                      </button>
                    </form>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {settings && (
        <>
          <h2>{t('service.settingsHeading')}</h2>
          <form onSubmit={handleSaveSettings}>
            <label>
              {t('service.settingFolder')}
              <input
                value={settings.backup_dir ?? ''}
                placeholder={t('service.settingFolderPlaceholder')}
                onChange={(e) => setSettings({ ...settings, backup_dir: e.target.value })}
              />
            </label>
            <label>
              <span>
                <input
                  type="checkbox"
                  checked={settings.auto_backup_enabled}
                  onChange={(e) => setSettings({ ...settings, auto_backup_enabled: e.target.checked })}
                />{' '}
                {t('service.settingAuto')}
              </span>
            </label>
            <label>
              {t('service.settingKeepDaily')}
              <input
                type="number"
                min={1}
                max={365}
                value={settings.keep_daily}
                onChange={(e) => setSettings({ ...settings, keep_daily: Number(e.target.value) })}
              />
            </label>
            <label>
              {t('service.settingKeepMonthly')}
              <input
                type="number"
                min={0}
                max={120}
                value={settings.keep_monthly}
                onChange={(e) => setSettings({ ...settings, keep_monthly: Number(e.target.value) })}
              />
            </label>
            <button type="submit" disabled={busy !== null}>
              {t('service.saveSettings')}
            </button>
          </form>
          <p className="hint">{t('service.settingsHint')}</p>
        </>
      )}

      <h2>{t('service.maintenanceHeading')}</h2>
      <div className="estimate-actions">
        <button type="button" disabled={busy !== null} onClick={handleCompact}>
          {t('service.compact')}
        </button>
        <button type="button" disabled={busy !== null} onClick={handleHealth}>
          {t('service.healthCheck')}
        </button>
        <a href={EXPORT_URL} download>
          {t('service.exportWorkbook')}
        </a>
      </div>
      <p className="hint">{t('service.maintenanceHint')}</p>

      {health && (
        <section className="estimate-results" aria-label={t('service.healthHeading')}>
          <h3>{t('service.healthHeading')}</h3>
          <p>
            {health.integrity_ok ? (
              <Badge tone="success">{t('service.integrityOk')}</Badge>
            ) : (
              <Badge tone="danger">{t('service.integrityBad')}</Badge>
            )}{' '}
            {health.fk_violations.length === 0 ? (
              <Badge tone="success">{t('service.noOrphans')}</Badge>
            ) : (
              <Badge tone="danger">{t('service.orphansFound')}</Badge>
            )}
          </p>
          {health.integrity_problems.map((p) => (
            <p key={p} role="alert">
              {p}
            </p>
          ))}
          {health.fk_violations.map((v) => (
            <p key={`${v.table}-${v.parent}`} role="alert">
              {t('service.orphanRows', { table: v.table, parent: v.parent, rows: v.rows })}
            </p>
          ))}
          <p>
            {t('service.healthSize', {
              size: formatBytes(health.size_bytes),
              reclaimable: formatBytes(health.reclaimable_bytes),
              mode: health.journal_mode,
              version: health.sqlite_version,
            })}
          </p>
          <table>
            <thead>
              <tr>
                <th>{t('service.colTable')}</th>
                <th>{t('service.colRows')}</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(health.row_counts).map(([table, rows]) => (
                <tr key={table}>
                  <td>{table}</td>
                  <td>{rows}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}
