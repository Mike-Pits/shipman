import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getVoyagePnl, getVoyageTce, voyagePnlExportUrl, voyageTceExportUrl } from '../api/reports'
import { listVoyages } from '../api/voyages'
import type { Voyage, VoyagePnl, VoyageTce } from '../api/types'

export default function VoyageReportsPage() {
  const { t } = useTranslation()
  const [voyages, setVoyages] = useState<Voyage[]>([])
  const [loading, setLoading] = useState(true)
  const [voyageId, setVoyageId] = useState<number | ''>('')
  const [pnl, setPnl] = useState<VoyagePnl | null>(null)
  const [tce, setTce] = useState<VoyageTce | null>(null)
  const [tceError, setTceError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listVoyages()
      .then(setVoyages)
      .finally(() => setLoading(false))
  }, [])

  const handleVoyageChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value ? Number(e.target.value) : ''
    setVoyageId(id)
    setPnl(null)
    setTce(null)
    setTceError(null)
    setError(null)
    if (id === '') return

    try {
      setPnl(await getVoyagePnl(id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load P&L')
    }

    try {
      setTce(await getVoyageTce(id))
    } catch (err) {
      setTceError(err instanceof Error ? err.message : 'Failed to load TCE')
    }
  }

  return (
    <div>
      <h1>{t('voyageReports.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <label>
          {t('voyageReports.voyage')}
          <select value={voyageId} onChange={handleVoyageChange}>
            <option value="">{t('voyageReports.selectVoyage')}</option>
            {voyages.map((v) => (
              <option key={v.id} value={v.id}>
                {v.voyage_number}
              </option>
            ))}
          </select>
        </label>
      )}

      {voyageId === '' && <p>{t('voyageReports.selectVoyagePrompt')}</p>}

      {error && <p role="alert">{error}</p>}

      {pnl && (
        <section>
          <h2>{t('voyageReports.pnlHeading')}</h2>
          <table>
            <tbody>
              <tr>
                <th>{t('voyageReports.revenue')}</th>
                <td>{pnl.revenue}</td>
              </tr>
              <tr>
                <th>{t('voyageReports.costs')}</th>
                <td>{pnl.costs}</td>
              </tr>
              <tr>
                <th>{t('voyageReports.netResult')}</th>
                <td>{pnl.net_result}</td>
              </tr>
              <tr>
                <th>{t('voyageReports.currency')}</th>
                <td>{pnl.currency}</td>
              </tr>
              {pnl.estimated_net_result !== undefined && (
                <tr>
                  <th>{t('voyageReports.estimatedNetResult')}</th>
                  <td>{pnl.estimated_net_result}</td>
                </tr>
              )}
              {pnl.variance_vs_estimate !== undefined && (
                <tr>
                  <th>{t('voyageReports.varianceVsEstimate')}</th>
                  <td>{pnl.variance_vs_estimate}</td>
                </tr>
              )}
            </tbody>
          </table>
          <a href={voyagePnlExportUrl(pnl.voyage_id)}>{t('voyageReports.exportPnl')}</a>
        </section>
      )}

      {tceError && <p>{tceError}</p>}

      {tce && (
        <section>
          <h2>{t('voyageReports.tceHeading')}</h2>
          <table>
            <tbody>
              <tr>
                <th>{t('voyageReports.durationDays')}</th>
                <td>{tce.duration_days}</td>
              </tr>
              <tr>
                <th>{t('voyageReports.offHireDays')}</th>
                <td>{tce.off_hire_days}</td>
              </tr>
              <tr>
                <th>{t('voyageReports.earningDays')}</th>
                <td>{tce.earning_days}</td>
              </tr>
              <tr>
                <th>{t('voyageReports.tcePerDay')}</th>
                <td>{tce.tce_per_day}</td>
              </tr>
            </tbody>
          </table>
          <a href={voyageTceExportUrl(tce.voyage_id)}>{t('voyageReports.exportTce')}</a>
        </section>
      )}
    </div>
  )
}
