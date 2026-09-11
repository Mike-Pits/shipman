import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  claimsStatusExportUrl,
  daReconciliationExportUrl,
  fleetPnlExportUrl,
  fleetVettingStatusExportUrl,
  getClaimsStatus,
  getDaReconciliation,
  getFleetPnl,
  getFleetVettingStatus,
} from '../api/reports'
import type { ClaimsStatusRow, ClaimStatus, ClaimType, DaReconciliationRow, DisbursementAccountStatus, FleetPnl, FleetVettingStatusRow, VettingStatus } from '../api/types'

const DA_STATUS_KEYS: Record<DisbursementAccountStatus, string> = {
  pda_only: 'disbursementAccounts.statusPdaOnly',
  fda_pending: 'disbursementAccounts.statusFdaPending',
  reconciled: 'disbursementAccounts.statusReconciled',
  disputed: 'disbursementAccounts.statusDisputed',
}

const VETTING_STATUS_KEYS: Record<VettingStatus, string> = {
  approved: 'vetting.statusApproved',
  pending: 'vetting.statusPending',
  expired: 'vetting.statusExpired',
  failed: 'vetting.statusFailed',
}

const CLAIM_STATUS_KEYS: Record<ClaimStatus, string> = {
  open: 'claims.statusOpen',
  negotiating: 'claims.statusNegotiating',
  settled: 'claims.statusSettled',
  rejected: 'claims.statusRejected',
}

const CLAIM_TYPE_KEYS: Record<ClaimType, string> = {
  cargo_quantity: 'claims.typeCargoQuantity',
  cargo_quality: 'claims.typeCargoQuality',
  demurrage_dispute: 'claims.typeDemurrageDispute',
  off_hire_dispute: 'claims.typeOffHireDispute',
  other: 'claims.typeOther',
}

export default function ReportsPage() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [fleetPnl, setFleetPnl] = useState<FleetPnl | null>(null)
  const [daRows, setDaRows] = useState<DaReconciliationRow[]>([])
  const [vettingRows, setVettingRows] = useState<FleetVettingStatusRow[]>([])
  const [claimsRows, setClaimsRows] = useState<ClaimsStatusRow[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      getDaReconciliation().then(setDaRows),
      getFleetVettingStatus().then(setVettingRows),
      getClaimsStatus().then(setClaimsRows),
    ]).finally(() => setLoading(false))
  }, [])

  const handleRunFleetPnl = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      setFleetPnl(await getFleetPnl(startDate, endDate))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run fleet P&L')
    }
  }

  return (
    <div>
      <h1>{t('reports.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <>
          {error && (
            <p role="alert" className="alert-danger">
              {error}
            </p>
          )}

          <section>
            <h2>{t('reports.fleetPnlHeading')}</h2>
            <form onSubmit={handleRunFleetPnl}>
              <label>
                {t('reports.startDate')}
                <input value={startDate} onChange={(e) => setStartDate(e.target.value)} placeholder="YYYY-MM-DD" required />
              </label>
              <label>
                {t('reports.endDate')}
                <input value={endDate} onChange={(e) => setEndDate(e.target.value)} placeholder="YYYY-MM-DD" required />
              </label>
              <button type="submit">{t('reports.runFleetPnlButton')}</button>
            </form>
            {fleetPnl && (
              <table>
                <tbody>
                  <tr>
                    <th>{t('reports.revenue')}</th>
                    <td>{fleetPnl.revenue}</td>
                  </tr>
                  <tr>
                    <th>{t('reports.costs')}</th>
                    <td>{fleetPnl.costs}</td>
                  </tr>
                  <tr>
                    <th>{t('reports.netResult')}</th>
                    <td>{fleetPnl.net_result}</td>
                  </tr>
                  <tr>
                    <th>{t('reports.invoicedRevenue')}</th>
                    <td>{fleetPnl.invoiced_revenue}</td>
                  </tr>
                  <tr>
                    <th>{t('reports.varianceVsInvoiced')}</th>
                    <td>{fleetPnl.variance_vs_invoiced}</td>
                  </tr>
                  <tr>
                    <th>{t('reports.voyageCount')}</th>
                    <td>{fleetPnl.voyage_count}</td>
                  </tr>
                  <tr>
                    <th>{t('reports.currency')}</th>
                    <td>{fleetPnl.currency}</td>
                  </tr>
                </tbody>
              </table>
            )}
            <a href={fleetPnlExportUrl(startDate || '1900-01-01', endDate || '2999-12-31')}>
              {t('reports.exportFleetPnl')}
            </a>
          </section>

          <section>
            <h2>{t('reports.daReconciliationHeading')}</h2>
            <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t('reports.columnVoyage')}</th>
                  <th>{t('reports.columnPort')}</th>
                  <th>{t('reports.columnStatus')}</th>
                  <th>{t('reports.columnPdaAmount')}</th>
                  <th>{t('reports.columnFdaTotal')}</th>
                  <th>{t('reports.columnVariance')}</th>
                </tr>
              </thead>
              <tbody>
                {daRows.map((row) => (
                  <tr key={row.id}>
                    <td>#{row.voyage_id}</td>
                    <td>{row.port}</td>
                    <td>{t(DA_STATUS_KEYS[row.status])}</td>
                    <td>{row.pda_amount}</td>
                    <td>{row.fda_total}</td>
                    <td>{row.variance}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
            <a href={daReconciliationExportUrl()}>{t('reports.exportDaReconciliation')}</a>
          </section>

          <section>
            <h2>{t('reports.vettingStatusHeading')}</h2>
            <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t('reports.columnVessel')}</th>
                  <th>{t('reports.columnStatus')}</th>
                  <th>{t('reports.columnExpiryDate')}</th>
                </tr>
              </thead>
              <tbody>
                {vettingRows.map((row) => (
                  <tr key={row.vessel_id}>
                    <td>{row.vessel_name}</td>
                    <td>{row.status ? t(VETTING_STATUS_KEYS[row.status]) : t('reports.noStatus')}</td>
                    <td>{row.expiry_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
            <a href={fleetVettingStatusExportUrl()}>{t('reports.exportVettingStatus')}</a>
          </section>

          <section>
            <h2>{t('reports.claimsStatusHeading')}</h2>
            <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t('reports.columnVoyage')}</th>
                  <th>{t('reports.columnType')}</th>
                  <th>{t('reports.columnCounterparty')}</th>
                  <th>{t('reports.columnAmountClaimed')}</th>
                  <th>{t('reports.columnStatus')}</th>
                  <th>{t('reports.columnAgeDays')}</th>
                </tr>
              </thead>
              <tbody>
                {claimsRows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.voyage_id != null ? `#${row.voyage_id}` : ''}</td>
                    <td>{t(CLAIM_TYPE_KEYS[row.claim_type])}</td>
                    <td>{row.counterparty}</td>
                    <td>
                      {row.amount_claimed} {row.currency}
                    </td>
                    <td>{t(CLAIM_STATUS_KEYS[row.status])}</td>
                    <td>{row.age_days}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
            <a href={claimsStatusExportUrl()}>{t('reports.exportClaimsStatus')}</a>
          </section>
        </>
      )}
    </div>
  )
}
