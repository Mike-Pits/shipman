import { Fragment, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../api/client'
import {
  approveDailyReport,
  createDailyReport,
  getImapFolderMapping,
  getImapSettings,
  listDailyReports,
  pollImap,
  updateDailyReport,
  updateImapSettings,
} from '../api/dailyReports'
import { listVessels } from '../api/vessels'
import Badge from '../components/ui/Badge'
import type { DailyReport, ImapFolderMapping, ImapPollResult, Vessel } from '../api/types'

export default function DailyReportsPage() {
  const { t } = useTranslation()
  const [reports, setReports] = useState<DailyReport[]>([])
  const [vessels, setVessels] = useState<Vessel[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedVesselId, setSelectedVesselId] = useState<number>(0)
  const [rawText, setRawText] = useState('')
  const [error, setError] = useState<string | null>(null)

  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editText, setEditText] = useState('')

  const [imapFolder, setImapFolder] = useState('')
  const [folderMapping, setFolderMapping] = useState<ImapFolderMapping | null>(null)
  const [pollResult, setPollResult] = useState<ImapPollResult | null>(null)
  const [pollElapsedSeconds, setPollElapsedSeconds] = useState<number | null>(null)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refresh = () => listDailyReports().then(setReports)

  useEffect(() => {
    Promise.all([
      refresh(),
      listVessels().then(setVessels),
      getImapSettings().then((s) => setImapFolder(s.folder)),
    ]).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!imapFolder) {
      setFolderMapping(null)
      return
    }
    getImapFolderMapping(imapFolder).then(setFolderMapping)
  }, [imapFolder])

  const vesselName = (id: number) => vessels.find((v) => v.id === id)?.name ?? `#${id}`

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await createDailyReport({ vessel_id: selectedVesselId, raw_text: rawText })
      setRawText('')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit report')
    }
  }

  const handleApprove = async (report: DailyReport) => {
    setError(null)
    try {
      await approveDailyReport(report.id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve report')
    }
  }

  const handleStartEdit = (report: DailyReport) => {
    if (report.approved && !window.confirm(t('dailyReports.editApprovedConfirm'))) return
    setError(null)
    setEditingId(report.id)
    setEditText(report.raw_text)
  }

  const handleSaveEdit = async (report: DailyReport) => {
    setError(null)
    try {
      await updateDailyReport(report.id, { raw_text: editText, override: report.approved })
      setEditingId(null)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save report')
    }
  }

  const handleSaveFolder = async () => {
    setError(null)
    try {
      const updated = await updateImapSettings(imapFolder)
      setImapFolder(updated.folder)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save IMAP folder')
    }
  }

  const handlePoll = async () => {
    setError(null)
    setPollResult(null)
    setPollElapsedSeconds(0)
    pollTimerRef.current = setInterval(() => {
      setPollElapsedSeconds((s) => (s ?? 0) + 1)
    }, 1000)
    try {
      let result
      try {
        result = await pollImap(selectedVesselId)
      } catch (err) {
        if (err instanceof ApiError && err.status === 409 && window.confirm(`${err.message}\n\n${t('dailyReports.confirmVesselChangePrompt')}`)) {
          result = await pollImap(selectedVesselId, true)
        } else {
          throw err
        }
      }
      setPollResult(result)
      setFolderMapping({ folder: imapFolder, vessel_id: selectedVesselId })
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to poll IMAP')
    } finally {
      if (pollTimerRef.current !== null) clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
      setPollElapsedSeconds(null)
    }
  }

  useEffect(() => {
    return () => {
      if (pollTimerRef.current !== null) clearInterval(pollTimerRef.current)
    }
  }, [])

  return (
    <div>
      <h1>{t('dailyReports.title')}</h1>

      <label>
        {t('dailyReports.vesselContext')}
        <select
          value={selectedVesselId || ''}
          onChange={(e) => setSelectedVesselId(Number(e.target.value))}
        >
          <option value="" disabled>
            {t('dailyReports.selectVessel')}
          </option>
          {vessels.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </select>
      </label>

      <h2>{t('dailyReports.imapHeading')}</h2>
      <label>
        {t('dailyReports.imapFolder')}
        <input value={imapFolder} onChange={(e) => setImapFolder(e.target.value)} />
      </label>
      <button type="button" onClick={handleSaveFolder}>
        {t('dailyReports.imapSaveFolder')}
      </button>
      {folderMapping && selectedVesselId !== 0 && folderMapping.vessel_id !== selectedVesselId && (
        <p role="alert">
          {t('dailyReports.folderMappedToOtherVessel', { vesselName: vesselName(folderMapping.vessel_id) })}
        </p>
      )}
      <button type="button" onClick={handlePoll} disabled={!selectedVesselId || pollElapsedSeconds !== null}>
        {t('dailyReports.imapPollButton')}
      </button>
      {pollElapsedSeconds !== null && (
        <p role="status">{t('dailyReports.imapPolling', { seconds: pollElapsedSeconds })}</p>
      )}
      {pollResult && (
        <p>
          {t('dailyReports.imapPollResult', {
            ingested: pollResult.ingested.length,
            skipped: pollResult.skipped_duplicates.length,
            errors: pollResult.errors.length,
          })}
        </p>
      )}

      <h2>{t('dailyReports.submitHeading')}</h2>
      <form onSubmit={handleSubmit}>
        <label>
          {t('dailyReports.rawTextLabel')}
          <textarea value={rawText} onChange={(e) => setRawText(e.target.value)} required rows={6} />
        </label>
        <p>
          <small>{t('dailyReports.rawTextHint')}</small>
        </p>
        <button type="submit" disabled={!selectedVesselId}>
          {t('dailyReports.submitButton')}
        </button>
      </form>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{t('dailyReports.columnDatetime')}</th>
              <th>{t('dailyReports.columnVessel')}</th>
              <th>{t('dailyReports.columnPosition')}</th>
              <th>{t('dailyReports.columnStatus')}</th>
              <th>{t('dailyReports.columnSource')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <Fragment key={r.id}>
                <tr>
                  <td>{r.report_datetime}</td>
                  <td>{vesselName(r.vessel_id)}</td>
                  <td>{r.fields['2'] ?? '—'}</td>
                  <td>
                    <Badge tone={r.approved ? 'success' : 'neutral'}>
                      {r.approved ? t('dailyReports.statusApproved') : t('dailyReports.statusPending')}
                    </Badge>
                  </td>
                  <td>{r.source_message_id ? t('dailyReports.sourceImap') : t('dailyReports.sourceManual')}</td>
                  <td>
                    <button
                      type="button"
                      onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}
                    >
                      {expandedId === r.id ? t('dailyReports.hideFields') : t('dailyReports.viewFields')}
                    </button>
                    <button type="button" onClick={() => handleStartEdit(r)}>
                      {t('dailyReports.edit')}
                    </button>
                    {!r.approved && (
                      <button type="button" onClick={() => handleApprove(r)}>
                        {t('dailyReports.approve')}
                      </button>
                    )}
                  </td>
                </tr>
                {r.warnings.map((w, i) => (
                  <tr key={`${r.id}-warning-${i}`}>
                    <td colSpan={6}>
                      <p role="alert">{w}</p>
                    </td>
                  </tr>
                ))}
                {editingId === r.id && (
                  <tr key={`${r.id}-edit`}>
                    <td colSpan={6}>
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        rows={6}
                        className="w-full"
                      />
                      <button type="button" onClick={() => handleSaveEdit(r)}>
                        {t('dailyReports.save')}
                      </button>
                      <button type="button" onClick={() => setEditingId(null)}>
                        {t('dailyReports.cancel')}
                      </button>
                    </td>
                  </tr>
                )}
                {expandedId === r.id && (
                  <tr key={`${r.id}-fields`}>
                    <td colSpan={6}>
                      <table>
                        <thead>
                          <tr>
                            <th>{t('dailyReports.fieldsColumnCode')}</th>
                            <th>{t('dailyReports.fieldsColumnLabel')}</th>
                            <th>{t('dailyReports.fieldsColumnValue')}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(r.fields).map(([code, value]) => (
                            <tr key={code}>
                              <td>{code}</td>
                              <td>{t(`dailyReports.codes.${code}`, { defaultValue: `Code ${code}` })}</td>
                              <td>{value}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
        </div>
      )}
      {error && (
        <p role="alert" className="alert-danger">
          {error}
        </p>
      )}
    </div>
  )
}
