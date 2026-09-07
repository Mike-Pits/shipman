import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  createVoyageEstimate,
  listVoyageEstimates,
  promoteVoyageEstimate,
  updateVoyageEstimate,
  updateVoyageEstimateStatus,
} from '../api/voyageEstimates'
import { listVessels } from '../api/vessels'
import Badge, { type BadgeTone } from '../components/ui/Badge'
import type { Currency, EstimateStatus, RateBasis, Vessel, VoyageEstimate, VoyageEstimateCreate } from '../api/types'

const EMPTY_FORM: VoyageEstimateCreate = {
  vessel_id: null,
  load_port: '',
  discharge_port: '',
  laycan_start: '',
  laycan_end: '',
  cargo_grade: '',
  estimated_cargo_quantity_mt: 0,
  estimated_rate: 0,
  estimated_rate_basis: '' as RateBasis,
  currency: '' as Currency,
  estimated_bunker_consumption_mt: 0,
  estimated_bunker_cost: 0,
  estimated_port_costs: 0,
  estimated_duration_days: 0,
}

const STATUS_KEYS: Record<EstimateStatus, string> = {
  draft: 'voyageEstimates.statusDraft',
  under_negotiation: 'voyageEstimates.statusUnderNegotiation',
  fixed: 'voyageEstimates.statusFixed',
  declined: 'voyageEstimates.statusDeclined',
}

const STATUS_TONES: Record<EstimateStatus, BadgeTone> = {
  draft: 'neutral',
  under_negotiation: 'info',
  fixed: 'success',
  declined: 'danger',
}

export default function VoyageEstimatesPage() {
  const { t } = useTranslation()
  const [estimates, setEstimates] = useState<VoyageEstimate[]>([])
  const [vessels, setVessels] = useState<Vessel[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<VoyageEstimateCreate>(EMPTY_FORM)
  const [promotingId, setPromotingId] = useState<number | null>(null)
  const [charterer, setCharterer] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)

  const refresh = () => listVoyageEstimates().then(setEstimates)

  useEffect(() => {
    Promise.all([refresh(), listVessels().then(setVessels)]).finally(() => setLoading(false))
  }, [])

  const vesselName = (id: number | null) => (id == null ? '' : (vessels.find((v) => v.id === id)?.name ?? `#${id}`))

  const field =
    (key: keyof VoyageEstimateCreate, numeric = false) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: numeric ? Number(e.target.value) : e.target.value }))

  const handleEdit = (est: VoyageEstimate) => {
    setError(null)
    setEditingId(est.id)
    setForm({
      vessel_id: est.vessel_id,
      load_port: est.load_port,
      discharge_port: est.discharge_port,
      laycan_start: est.laycan_start,
      laycan_end: est.laycan_end,
      cargo_grade: est.cargo_grade,
      estimated_cargo_quantity_mt: est.estimated_cargo_quantity_mt,
      estimated_rate: est.estimated_rate,
      estimated_rate_basis: est.estimated_rate_basis,
      currency: est.currency,
      estimated_bunker_consumption_mt: est.estimated_bunker_consumption_mt,
      estimated_bunker_cost: est.estimated_bunker_cost,
      estimated_port_costs: est.estimated_port_costs,
      estimated_duration_days: est.estimated_duration_days,
    })
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setForm(EMPTY_FORM)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const payload = { ...form, vessel_id: form.vessel_id || null }
      if (editingId !== null) {
        await updateVoyageEstimate(editingId, payload)
      } else {
        await createVoyageEstimate(payload)
      }
      handleCancelEdit()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create estimate')
    }
  }

  const handleStatusChange = async (estimate: VoyageEstimate, status: 'under_negotiation' | 'declined') => {
    setError(null)
    try {
      await updateVoyageEstimateStatus(estimate.id, status)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status')
    }
  }

  const handlePromote = async (estimate: VoyageEstimate, e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await promoteVoyageEstimate(estimate.id, {
        fixture_type: 'voyage_charter',
        charterer,
        contract_currency: estimate.currency,
        freight_rate: estimate.estimated_rate,
        freight_rate_basis: estimate.estimated_rate_basis,
        laycan_start: estimate.laycan_start,
        laycan_end: estimate.laycan_end,
        load_port: estimate.load_port,
        discharge_port: estimate.discharge_port,
        cargo_grade: estimate.cargo_grade,
        brokers: [],
      })
      setPromotingId(null)
      setCharterer('')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to promote estimate')
    }
  }

  const canProgress = (status: EstimateStatus) => status === 'draft' || status === 'under_negotiation'

  return (
    <div>
      <h1>{t('voyageEstimates.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{t('voyageEstimates.vessel')}</th>
              <th>{t('voyageEstimates.loadPort')}</th>
              <th>{t('voyageEstimates.dischargePort')}</th>
              <th>{t('voyageEstimates.columnCargo')}</th>
              <th>{t('voyageEstimates.columnRevenue')}</th>
              <th>{t('voyageEstimates.columnCosts')}</th>
              <th>{t('voyageEstimates.columnNetResult')}</th>
              <th>{t('voyageEstimates.columnTce')}</th>
              <th>{t('voyageEstimates.columnStatus')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {estimates.map((est) => (
              <tr key={est.id}>
                <td>{vesselName(est.vessel_id)}</td>
                <td>{est.load_port}</td>
                <td>{est.discharge_port}</td>
                <td>
                  {est.cargo_grade} ({est.estimated_cargo_quantity_mt})
                  {est.warnings.map((w, i) => (
                    <p key={i} role="alert">
                      {w}
                    </p>
                  ))}
                </td>
                <td>{est.estimated_revenue}</td>
                <td>{est.estimated_costs}</td>
                <td>{est.estimated_net_result}</td>
                <td>{est.estimated_tce_per_day}</td>
                <td>
                  <Badge tone={STATUS_TONES[est.status]}>{t(STATUS_KEYS[est.status])}</Badge>
                </td>
                <td>
                  <button type="button" onClick={() => handleEdit(est)}>
                    {t('common.edit')}
                  </button>
                  {canProgress(est.status) && (
                    <>
                      {est.status === 'draft' && (
                        <button type="button" onClick={() => handleStatusChange(est, 'under_negotiation')}>
                          {t('voyageEstimates.negotiateButton')}
                        </button>
                      )}
                      <button type="button" onClick={() => handleStatusChange(est, 'declined')}>
                        {t('voyageEstimates.declineButton')}
                      </button>
                      <button type="button" onClick={() => setPromotingId(promotingId === est.id ? null : est.id)}>
                        {t('voyageEstimates.promoteButton')}
                      </button>
                      {promotingId === est.id && (
                        <form onSubmit={(e) => handlePromote(est, e)}>
                          <h3>{t('voyageEstimates.promoteHeading')}</h3>
                          <label>
                            {t('voyageEstimates.charterer')}
                            <input value={charterer} onChange={(e) => setCharterer(e.target.value)} required />
                          </label>
                          <button type="submit">{t('voyageEstimates.confirmPromoteButton')}</button>
                        </form>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}

      <h2>{editingId !== null ? t('voyageEstimates.editHeading') : t('voyageEstimates.createHeading')}</h2>
      {editingId !== null && <p role="alert">{t('voyageEstimates.editWarning')}</p>}
      <form onSubmit={handleSubmit}>
        <label>
          {t('voyageEstimates.vessel')}
          <select value={form.vessel_id ?? ''} onChange={field('vessel_id', true)}>
            <option value="">{t('voyageEstimates.selectVessel')}</option>
            {vessels.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('voyageEstimates.loadPort')}
          <input value={form.load_port} onChange={field('load_port')} required />
        </label>
        <label>
          {t('voyageEstimates.dischargePort')}
          <input value={form.discharge_port} onChange={field('discharge_port')} required />
        </label>
        <label>
          {t('voyageEstimates.laycanStart')}
          <input value={form.laycan_start} onChange={field('laycan_start')} placeholder="YYYY-MM-DD" required />
        </label>
        <label>
          {t('voyageEstimates.laycanEnd')}
          <input value={form.laycan_end} onChange={field('laycan_end')} placeholder="YYYY-MM-DD" required />
        </label>
        <label>
          {t('voyageEstimates.cargoGrade')}
          <input value={form.cargo_grade} onChange={field('cargo_grade')} required />
        </label>
        <label>
          {t('voyageEstimates.cargoQuantity')}
          <input
            type="number"
            step="0.01"
            value={form.estimated_cargo_quantity_mt || ''}
            onChange={field('estimated_cargo_quantity_mt', true)}
            required
          />
        </label>
        <label>
          {t('voyageEstimates.rate')}
          <input
            type="number"
            step="0.01"
            value={form.estimated_rate || ''}
            onChange={field('estimated_rate', true)}
            required
          />
        </label>
        <label>
          {t('voyageEstimates.rateBasis')}
          <select value={form.estimated_rate_basis} onChange={field('estimated_rate_basis')} required>
            <option value="" disabled>
              {t('voyageEstimates.selectRateBasis')}
            </option>
            <option value="per_tonne">{t('voyageEstimates.perTonne')}</option>
            <option value="lump_sum">{t('voyageEstimates.lumpSum')}</option>
          </select>
        </label>
        <label>
          {t('voyageEstimates.currency')}
          <select value={form.currency} onChange={field('currency')} required>
            <option value="" disabled>
              {t('voyageEstimates.selectCurrency')}
            </option>
            <option value="RUB">RUB</option>
            <option value="USD">USD</option>
          </select>
        </label>
        <label>
          {t('voyageEstimates.bunkerConsumption')}
          <input
            type="number"
            step="0.01"
            value={form.estimated_bunker_consumption_mt || ''}
            onChange={field('estimated_bunker_consumption_mt', true)}
            required
          />
        </label>
        <label>
          {t('voyageEstimates.bunkerCost')}
          <input
            type="number"
            step="0.01"
            value={form.estimated_bunker_cost || ''}
            onChange={field('estimated_bunker_cost', true)}
            required
          />
        </label>
        <label>
          {t('voyageEstimates.portCosts')}
          <input
            type="number"
            step="0.01"
            value={form.estimated_port_costs || ''}
            onChange={field('estimated_port_costs', true)}
            required
          />
        </label>
        <label>
          {t('voyageEstimates.duration')}
          <input
            type="number"
            step="0.01"
            value={form.estimated_duration_days || ''}
            onChange={field('estimated_duration_days', true)}
            required
          />
        </label>
        <button type="submit">
          {editingId !== null ? t('voyageEstimates.updateButton') : t('voyageEstimates.createButton')}
        </button>
        {editingId !== null && (
          <button type="button" onClick={handleCancelEdit}>
            {t('common.cancel')}
          </button>
        )}
      </form>
      {error && (
        <p role="alert" className="alert-danger">
          {error}
        </p>
      )}
    </div>
  )
}
