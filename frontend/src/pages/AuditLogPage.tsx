import { Fragment, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { listAuditLog } from '../api/auditLog'
import Badge, { type BadgeTone } from '../components/ui/Badge'
import type { AuditLogEntry } from '../api/types'

const ACTION_TONES: Record<string, BadgeTone> = {
  insert: 'success',
  update: 'info',
  delete: 'danger',
}

export default function AuditLogPage() {
  const { t } = useTranslation()
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [tableFilter, setTableFilter] = useState('')
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    listAuditLog()
      .then(setEntries)
      .finally(() => setLoading(false))
  }, [])

  const tableNames = Array.from(new Set(entries.map((e) => e.table_name))).sort()
  const visibleEntries = tableFilter ? entries.filter((e) => e.table_name === tableFilter) : entries

  return (
    <div>
      <h1>{t('auditLog.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <>
          <label>
            {t('auditLog.table')}
            <select value={tableFilter} onChange={(e) => setTableFilter(e.target.value)}>
              <option value="">{t('auditLog.allTables')}</option>
              {tableNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>

          <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('auditLog.columnId')}</th>
                <th>{t('auditLog.columnTable')}</th>
                <th>{t('auditLog.columnRecordId')}</th>
                <th>{t('auditLog.columnAction')}</th>
                <th>{t('auditLog.columnUser')}</th>
                <th>{t('auditLog.columnTimestamp')}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {visibleEntries.map((entry) => (
                <Fragment key={entry.id}>
                  <tr>
                    <td>{entry.id}</td>
                    <td>{entry.table_name}</td>
                    <td>{entry.record_id}</td>
                    <td>
                      <Badge tone={ACTION_TONES[entry.action] ?? 'neutral'}>{entry.action}</Badge>
                    </td>
                    <td>{entry.user}</td>
                    <td>{entry.timestamp}</td>
                    <td>
                      <button type="button" onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}>
                        {expandedId === entry.id ? t('auditLog.hideChanges') : t('auditLog.viewChanges')}
                      </button>
                    </td>
                  </tr>
                  {expandedId === entry.id && (
                    <tr>
                      <td colSpan={7}>
                        <div>
                          <h3>{t('auditLog.oldValues')}</h3>
                          <pre>{entry.old_values ?? ''}</pre>
                        </div>
                        <div>
                          <h3>{t('auditLog.newValues')}</h3>
                          <pre>{entry.new_values ?? ''}</pre>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
          </div>
        </>
      )}
    </div>
  )
}
