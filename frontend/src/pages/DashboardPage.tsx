import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getClaimsStatus, getDaReconciliation, getFleetPnl, getFleetVettingStatus } from '../api/reports'
import { listVessels } from '../api/vessels'
import { listVoyages } from '../api/voyages'
import StatCard from '../components/ui/StatCard'
import type { FleetPnl } from '../api/types'

function monthToDateRange(): [string, string] {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  const iso = (d: Date) => d.toISOString().slice(0, 10)
  return [iso(start), iso(now)]
}

export default function DashboardPage() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [fleetSize, setFleetSize] = useState(0)
  const [activeVoyages, setActiveVoyages] = useState(0)
  const [fleetPnl, setFleetPnl] = useState<FleetPnl | null>(null)
  const [unreconciledDas, setUnreconciledDas] = useState(0)
  const [vettingIssues, setVettingIssues] = useState(0)
  const [openClaims, setOpenClaims] = useState(0)

  useEffect(() => {
    const [start, end] = monthToDateRange()
    Promise.all([
      listVessels().then((v) => setFleetSize(v.length)),
      listVoyages().then((v) => setActiveVoyages(v.filter((voyage) => !voyage.end_date).length)),
      getFleetPnl(start, end).then(setFleetPnl),
      getDaReconciliation().then((rows) => setUnreconciledDas(rows.length)),
      getFleetVettingStatus().then((rows) =>
        setVettingIssues(rows.filter((row) => row.status === 'expired' || row.status === 'failed').length),
      ),
      getClaimsStatus().then((rows) => setOpenClaims(rows.length)),
    ]).finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <h1>{t('dashboard.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <div className="stat-grid">
          <StatCard label={t('dashboard.fleetSize')} value={fleetSize} />
          <StatCard label={t('dashboard.activeVoyages')} value={activeVoyages} />
          <StatCard
            label={t('dashboard.monthToDatePnl')}
            value={`${fleetPnl?.net_result ?? 0} ${fleetPnl?.currency ?? ''}`}
            tone={fleetPnl && fleetPnl.net_result < 0 ? 'danger' : 'success'}
            sub={t('dashboard.netResult')}
          />
          <StatCard
            label={t('dashboard.unreconciledDas')}
            value={unreconciledDas}
            tone={unreconciledDas > 0 ? 'warning' : 'success'}
          />
          <StatCard
            label={t('dashboard.vettingIssues')}
            value={vettingIssues}
            tone={vettingIssues > 0 ? 'danger' : 'success'}
          />
          <StatCard label={t('dashboard.openClaims')} value={openClaims} tone={openClaims > 0 ? 'warning' : 'success'} />
        </div>
      )}
    </div>
  )
}
