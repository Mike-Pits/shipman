import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  calculateVoyageEstimate,
  createVoyageEstimate,
  deleteVoyageEstimate,
  listVoyageEstimates,
  promoteVoyageEstimate,
  updateVoyageEstimate,
  updateVoyageEstimateStatus,
} from '../api/voyageEstimates'
import { createPort, deletePort, listPorts } from '../api/ports'
import { listVessels } from '../api/vessels'
import Badge, { type BadgeTone } from '../components/ui/Badge'
import VoyageEstimateResults from '../components/VoyageEstimateResults'
import type {
  Condition,
  EstimateCargoLot,
  EstimatePortStop,
  EstimateResults,
  EstimateStatus,
  LaytimeBasis,
  LaytimeUnit,
  Port,
  FuelGrade,
  Vessel,
  VoyageEstimate,
  VoyageEstimateCreate,
} from '../api/types'

const MAX_PORT_STOPS = 10
const MAX_CARGO_LOTS = 3

const LAYTIME_UNITS: { value: LaytimeUnit; key: string }[] = [
  { value: 'hours', key: 'voyageEstimates.unitHours' },
  { value: 'days', key: 'voyageEstimates.unitDays' },
  { value: 'mt_per_hour', key: 'voyageEstimates.unitMtPerHour' },
  { value: 'mt_per_day', key: 'voyageEstimates.unitMtPerDay' },
]
const LAYTIME_BASES: LaytimeBasis[] = ['CQD', 'WIBON', 'WIPON', 'FIO', 'SHINC', 'SHEX']

// A load port is reached in ballast, a discharge port laden — the operator can override either.
const DEFAULT_CONDITION: Record<EstimatePortStop['stop_type'], Condition> = { load: 'ballast', discharge: 'laden' }
const FUEL_GRADES: FuelGrade[] = ['IFO', 'MGO']

const newStop = (type: EstimatePortStop['stop_type'] = 'load'): EstimatePortStop => ({
  port_name: '',
  stop_type: type,
  distance_nm: 0,
  condition: DEFAULT_CONDITION[type],
  cargo_quantity_mt: 0,
  laytime_value: 0,
  laytime_unit: 'days',
  laytime_basis: 'SHINC',
  rate_mt_per_day: 0,
})
const newLot = (): EstimateCargoLot => ({ grade: '', quantity_mt: 0, freight_rate: 0 })

const emptyForm = (): VoyageEstimateCreate => ({
  name: '',
  vessel_id: null,
  currency: 'USD',
  laycan_start: '',
  laycan_end: '',
  freight_mode: 'per_mt',
  lumpsum_freight: 0,
  extra_sea_days: 0,
  extra_costs: 0,
  canal_fees: 0,
  port_charges: 0,
  agent_fees: 0,
  bunker_surcharge: 0,
  demurrage_rate: 0,
  port_stops: [newStop()],
  cargo_lots: [newLot()],
  fuel_prices: [],
  cost_items: [],
})

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

const toCreate = (est: VoyageEstimate): VoyageEstimateCreate => ({
  name: est.name,
  vessel_id: est.vessel_id,
  currency: est.currency,
  laycan_start: est.laycan_start ?? '',
  laycan_end: est.laycan_end ?? '',
  freight_mode: est.freight_mode,
  lumpsum_freight: est.lumpsum_freight,
  extra_sea_days: est.extra_sea_days,
  extra_costs: est.extra_costs,
  canal_fees: est.canal_fees,
  port_charges: est.port_charges,
  agent_fees: est.agent_fees,
  bunker_surcharge: est.bunker_surcharge,
  demurrage_rate: est.demurrage_rate,
  port_stops: est.port_stops.map((s) => ({ ...s })),
  cargo_lots: est.cargo_lots.map((l) => ({ ...l })),
  fuel_prices: est.fuel_prices.map((p) => ({ ...p })),
  cost_items: est.cost_items.map((i) => ({ ...i })),
})

const money = (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 0 })

export default function VoyageEstimatesPage() {
  const { t } = useTranslation()
  const [estimates, setEstimates] = useState<VoyageEstimate[]>([])
  const [vessels, setVessels] = useState<Vessel[]>([])
  const [ports, setPorts] = useState<Port[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<VoyageEstimateCreate>(emptyForm)
  const [results, setResults] = useState<EstimateResults | null>(null)
  const [promotingId, setPromotingId] = useState<number | null>(null)
  const [charterer, setCharterer] = useState('')
  const [promoteGrade, setPromoteGrade] = useState('')
  const [newPort, setNewPort] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)

  const refresh = () => listVoyageEstimates().then(setEstimates)
  const refreshPorts = () => listPorts().then(setPorts)

  useEffect(() => {
    Promise.all([refresh(), listVessels().then(setVessels), refreshPorts()]).finally(() => setLoading(false))
  }, [])

  const vessel = vessels.find((v) => v.id === form.vessel_id)
  const vesselName = (id: number | null) => (id == null ? '' : (vessels.find((v) => v.id === id)?.name ?? `#${id}`))

  const set = <K extends keyof VoyageEstimateCreate>(key: K, value: VoyageEstimateCreate[K]) =>
    setForm((f) => ({ ...f, [key]: value }))
  const numField = (key: keyof VoyageEstimateCreate) => (e: React.ChangeEvent<HTMLInputElement>) =>
    set(key, Number(e.target.value) as never)
  const textField = (key: keyof VoyageEstimateCreate) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    set(key, e.target.value as never)

  const updateStop = (i: number, patch: Partial<EstimatePortStop>) =>
    set('port_stops', form.port_stops.map((s, j) => (j === i ? { ...s, ...patch } : s)))
  const changeStopType = (i: number, type: EstimatePortStop['stop_type']) =>
    updateStop(i, { stop_type: type, condition: DEFAULT_CONDITION[type] })
  const updateLot = (i: number, patch: Partial<EstimateCargoLot>) =>
    set('cargo_lots', form.cargo_lots.map((l, j) => (j === i ? { ...l, ...patch } : l)))
  const setPrice = (grade: FuelGrade, value: string) => {
    const others = form.fuel_prices.filter((p) => p.grade !== grade)
    set('fuel_prices', value === '' ? others : [...others, { grade, price_per_mt: Number(value) }])
  }

  const handleCurrencyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const hasMoney =
      form.lumpsum_freight || form.canal_fees || form.port_charges || form.agent_fees || form.bunker_surcharge ||
      form.extra_costs || form.demurrage_rate || form.fuel_prices.length || form.cost_items.length ||
      form.cargo_lots.some((l) => l.freight_rate)
    if (hasMoney && !window.confirm(t('voyageEstimates.currencySwitchConfirm'))) return
    setForm((f) => ({
      ...f,
      currency: e.target.value as VoyageEstimateCreate['currency'],
      lumpsum_freight: 0,
      canal_fees: 0,
      port_charges: 0,
      agent_fees: 0,
      bunker_surcharge: 0,
      extra_costs: 0,
      demurrage_rate: 0,
      fuel_prices: [],
      cost_items: [],
      cargo_lots: f.cargo_lots.map((l) => ({ ...l, freight_rate: 0 })),
    }))
  }

  const payloadFromForm = (): VoyageEstimateCreate => ({
    ...form,
    laycan_start: form.laycan_start || null,
    laycan_end: form.laycan_end || null,
    cargo_lots:
      form.freight_mode === 'per_mt' ? form.cargo_lots.filter((l) => l.quantity_mt > 0 || l.freight_rate > 0) : [],
    cost_items: form.cost_items.filter((i) => i.description.trim() || i.amount > 0),
  })

  const calcSeq = useRef(0)
  const locked = editingId !== null && estimates.find((e) => e.id === editingId)?.status === 'fixed'

  // Recalculate as the operator types: the results panel always reflects the current inputs.
  // An incomplete form (no port name yet, no cargo lot…) simply shows no results.
  useEffect(() => {
    if (locked || form.port_stops.some((s) => !s.port_name.trim())) return
    const seq = ++calcSeq.current
    const timer = setTimeout(() => {
      calculateVoyageEstimate({ ...payloadFromForm(), name: form.name || '—' })
        .then((r) => seq === calcSeq.current && setResults(r))
        .catch(() => seq === calcSeq.current && setResults(null))
    }, 400)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form, locked])

  const handleEdit = (est: VoyageEstimate) => {
    setError(null)
    setEditingId(est.id)
    const created = toCreate(est)
    setForm({ ...created, cargo_lots: created.cargo_lots.length ? created.cargo_lots : [newLot()] })
    setResults(est.results)
    window.scrollTo?.({ top: document.body.scrollHeight, behavior: 'smooth' })
  }

  const handleReset = () => {
    setEditingId(null)
    setForm(emptyForm())
    setResults(null)
  }

  const fail = (err: unknown, fallback: string) => setError(err instanceof Error ? err.message : fallback)

  const handleCalculate = async () => {
    setError(null)
    try {
      setResults(await calculateVoyageEstimate({ ...payloadFromForm(), name: form.name || '—' }))
    } catch (err) {
      fail(err, 'Failed to calculate')
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const saved =
        editingId !== null
          ? await updateVoyageEstimate(editingId, payloadFromForm())
          : await createVoyageEstimate(payloadFromForm())
      setEditingId(saved.id)
      setResults(saved.results)
      await refresh()
    } catch (err) {
      fail(err, 'Failed to save estimate')
    }
  }

  const handleDuplicate = async (est: VoyageEstimate) => {
    setError(null)
    try {
      await createVoyageEstimate({ ...toCreate(est), name: `${est.name} ${t('voyageEstimates.copySuffix')}` })
      await refresh()
    } catch (err) {
      fail(err, 'Failed to duplicate estimate')
    }
  }

  const handleDelete = async (est: VoyageEstimate) => {
    if (!window.confirm(t('voyageEstimates.deleteConfirm', { name: est.name }))) return
    setError(null)
    try {
      await deleteVoyageEstimate(est.id)
      if (editingId === est.id) handleReset()
      await refresh()
    } catch (err) {
      fail(err, 'Failed to delete estimate')
    }
  }

  const handleStatusChange = async (estimate: VoyageEstimate, status: 'under_negotiation' | 'declined') => {
    setError(null)
    try {
      await updateVoyageEstimateStatus(estimate.id, status)
      await refresh()
    } catch (err) {
      fail(err, 'Failed to update status')
    }
  }

  const startPromotion = (est: VoyageEstimate) => {
    setPromotingId(promotingId === est.id ? null : est.id)
    setPromoteGrade(est.cargo_lots[0]?.grade ?? '')
  }

  const handlePromote = async (estimate: VoyageEstimate, e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const perMt = estimate.freight_mode === 'per_mt'
    try {
      await promoteVoyageEstimate(estimate.id, {
        fixture_type: 'voyage_charter',
        charterer,
        contract_currency: estimate.currency,
        freight_rate: perMt ? (estimate.cargo_lots[0]?.freight_rate ?? 0) : estimate.lumpsum_freight,
        freight_rate_basis: perMt ? 'per_tonne' : 'lump_sum',
        laycan_start: estimate.laycan_start ?? undefined,
        laycan_end: estimate.laycan_end ?? undefined,
        load_port: estimate.port_stops.find((s) => s.stop_type === 'load')?.port_name,
        discharge_port: estimate.port_stops.find((s) => s.stop_type === 'discharge')?.port_name,
        cargo_grade: promoteGrade,
        vat_applicable: false,
        brokers: [],
      })
      setPromotingId(null)
      setCharterer('')
      await refresh()
    } catch (err) {
      fail(err, 'Failed to promote estimate')
    }
  }

  const handlePrint = () => {
    document.body.classList.add('printing-estimate')
    window.print()
    document.body.classList.remove('printing-estimate')
  }

  const handleAddPort = async () => {
    const name = newPort.trim()
    if (!name) return
    setError(null)
    try {
      await createPort(name)
      setNewPort('')
      await refreshPorts()
    } catch (err) {
      fail(err, 'Failed to add port')
    }
  }

  const handleRemovePort = async (port: Port) => {
    setError(null)
    try {
      await deletePort(port.id)
      await refreshPorts()
    } catch (err) {
      fail(err, 'Failed to remove port')
    }
  }

  const route = (est: VoyageEstimate) => est.port_stops.map((s) => s.port_name).join(' → ')
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
                <th>{t('voyageEstimates.name')}</th>
                <th>{t('voyageEstimates.vessel')}</th>
                <th>{t('voyageEstimates.columnRoute')}</th>
                <th>{t('voyageEstimates.columnDays')}</th>
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
                  <td>
                    {est.name}
                    {est.warnings.map((w, i) => (
                      <p key={i} role="alert">
                        {w}
                      </p>
                    ))}
                  </td>
                  <td>{vesselName(est.vessel_id)}</td>
                  <td>{route(est)}</td>
                  <td>{est.results.total_voyage_days}</td>
                  <td>
                    {money(est.results.freight_revenue)} {est.currency}
                  </td>
                  <td>
                    {money(est.results.total_costs)} {est.currency}
                  </td>
                  <td>
                    {money(est.results.net_result)} {est.currency}
                  </td>
                  <td>
                    {money(est.results.tce_per_day)} {est.currency}
                  </td>
                  <td>
                    <Badge tone={STATUS_TONES[est.status]}>{t(STATUS_KEYS[est.status])}</Badge>
                  </td>
                  <td>
                    <button type="button" onClick={() => handleEdit(est)}>
                      {est.status === 'fixed' ? t('common.view') : t('common.edit')}
                    </button>
                    <button type="button" onClick={() => handleDuplicate(est)}>
                      {t('voyageEstimates.duplicateButton')}
                    </button>
                    {est.status !== 'fixed' && (
                      <button type="button" onClick={() => handleDelete(est)}>
                        {t('common.delete')}
                      </button>
                    )}
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
                        <button type="button" onClick={() => startPromotion(est)}>
                          {t('voyageEstimates.promoteButton')}
                        </button>
                        {promotingId === est.id && (
                          <form onSubmit={(e) => handlePromote(est, e)}>
                            <h3>{t('voyageEstimates.promoteHeading')}</h3>
                            <label>
                              {t('voyageEstimates.charterer')}
                              <input value={charterer} onChange={(e) => setCharterer(e.target.value)} required />
                            </label>
                            <label>
                              {t('voyageEstimates.cargoGrade')}
                              <input value={promoteGrade} onChange={(e) => setPromoteGrade(e.target.value)} required />
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
      {editingId !== null && !locked && <p role="alert">{t('voyageEstimates.editWarning')}</p>}
      {locked && <p role="alert">{t('voyageEstimates.fixedLocked')}</p>}

      <datalist id="port-suggestions">
        {ports.map((p) => (
          <option key={p.id} value={p.name} />
        ))}
      </datalist>

      <form className="estimate-form" onSubmit={handleSave}>
        <fieldset disabled={locked}>
          <legend>{t('voyageEstimates.sectionVoyage')}</legend>
          <div className="field-grid">
            <label>
              {t('voyageEstimates.name')}
              <input value={form.name} onChange={textField('name')} required />
            </label>
            <label>
              {t('voyageEstimates.vessel')}
              <select
                value={form.vessel_id ?? ''}
                onChange={(e) => set('vessel_id', e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">{t('voyageEstimates.selectVessel')}</option>
                {vessels.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('voyageEstimates.currency')}
              <select value={form.currency} onChange={handleCurrencyChange}>
                <option value="USD">USD</option>
                <option value="RUB">RUB</option>
              </select>
            </label>
            <label>
              {t('voyageEstimates.laycanStart')}
              <input value={form.laycan_start ?? ''} onChange={textField('laycan_start')} placeholder="YYYY-MM-DD" />
            </label>
            <label>
              {t('voyageEstimates.laycanEnd')}
              <input value={form.laycan_end ?? ''} onChange={textField('laycan_end')} placeholder="YYYY-MM-DD" />
            </label>
          </div>
        </fieldset>

        <fieldset disabled={locked}>
          <legend>{t('voyageEstimates.sectionItinerary')}</legend>
          <p className="hint">{t('voyageEstimates.itineraryHint')}</p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>{t('voyageEstimates.port')}</th>
                  <th>{t('voyageEstimates.stopType')}</th>
                  <th>{t('voyageEstimates.condition')}</th>
                  <th>{t('voyageEstimates.distance')}</th>
                  <th>{t('voyageEstimates.stopCargo')}</th>
                  <th>{t('voyageEstimates.laytime')}</th>
                  <th>{t('voyageEstimates.laytimeUnit')}</th>
                  <th>{t('voyageEstimates.laytimeBasis')}</th>
                  <th>{t('voyageEstimates.workRate')}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {form.port_stops.map((s, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td>
                      <input
                        list="port-suggestions"
                        aria-label={`${t('voyageEstimates.port')} ${i + 1}`}
                        value={s.port_name}
                        onChange={(e) => updateStop(i, { port_name: e.target.value })}
                        required
                      />
                    </td>
                    <td>
                      <select
                        aria-label={`${t('voyageEstimates.stopType')} ${i + 1}`}
                        value={s.stop_type}
                        onChange={(e) => changeStopType(i, e.target.value as EstimatePortStop['stop_type'])}
                      >
                        <option value="load">{t('voyageEstimates.typeLoad')}</option>
                        <option value="discharge">{t('voyageEstimates.typeDischarge')}</option>
                      </select>
                    </td>
                    <td>
                      <select
                        aria-label={`${t('voyageEstimates.condition')} ${i + 1}`}
                        value={s.condition}
                        disabled={i === 0}
                        onChange={(e) => updateStop(i, { condition: e.target.value as Condition })}
                      >
                        <option value="laden">{t('voyageEstimates.conditionLaden')}</option>
                        <option value="ballast">{t('voyageEstimates.conditionBallast')}</option>
                      </select>
                    </td>
                    <td>
                      <input
                        type="number"
                        step="any"
                        min="0"
                        aria-label={`${t('voyageEstimates.distance')} ${i + 1}`}
                        disabled={i === 0}
                        value={i === 0 ? 0 : s.distance_nm || ''}
                        placeholder="0"
                        onChange={(e) => updateStop(i, { distance_nm: Number(e.target.value) })}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        step="any"
                        min="0"
                        aria-label={`${t('voyageEstimates.stopCargo')} ${i + 1}`}
                        value={s.cargo_quantity_mt || ''} placeholder="0"
                        onChange={(e) => updateStop(i, { cargo_quantity_mt: Number(e.target.value) })}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        step="any"
                        min="0"
                        aria-label={`${t('voyageEstimates.laytime')} ${i + 1}`}
                        value={s.laytime_value || ''} placeholder="0"
                        onChange={(e) => updateStop(i, { laytime_value: Number(e.target.value) })}
                      />
                    </td>
                    <td>
                      <select
                        aria-label={`${t('voyageEstimates.laytimeUnit')} ${i + 1}`}
                        value={s.laytime_unit}
                        onChange={(e) => updateStop(i, { laytime_unit: e.target.value as LaytimeUnit })}
                      >
                        {LAYTIME_UNITS.map((u) => (
                          <option key={u.value} value={u.value}>
                            {t(u.key)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <select
                        aria-label={`${t('voyageEstimates.laytimeBasis')} ${i + 1}`}
                        value={s.laytime_basis}
                        onChange={(e) => updateStop(i, { laytime_basis: e.target.value as LaytimeBasis })}
                      >
                        {LAYTIME_BASES.map((b) => (
                          <option key={b} value={b}>
                            {b}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="number"
                        step="any"
                        min="0"
                        aria-label={`${t('voyageEstimates.workRate')} ${i + 1}`}
                        value={s.rate_mt_per_day || ''} placeholder="0"
                        onChange={(e) => updateStop(i, { rate_mt_per_day: Number(e.target.value) })}
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        aria-label={`${t('common.delete')} ${t('voyageEstimates.port')} ${i + 1}`}
                        disabled={form.port_stops.length === 1}
                        onClick={() => set('port_stops', form.port_stops.filter((_, j) => j !== i))}
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            type="button"
            disabled={form.port_stops.length >= MAX_PORT_STOPS}
            onClick={() => set('port_stops', [...form.port_stops, newStop('discharge')])}
          >
            {t('voyageEstimates.addPort')}
          </button>
        </fieldset>

        <fieldset disabled={locked}>
          <legend>{t('voyageEstimates.sectionSeaPassage')}</legend>
          <p className="hint">{t('voyageEstimates.seaPassageHint')}</p>
          <div className="field-grid">
            <label>
              {t('voyageEstimates.extraSeaDays')}
              <input type="number" step="any" min="0" value={form.extra_sea_days || ''} placeholder="0" onChange={numField('extra_sea_days')} />
            </label>
            <label>
              {t('voyageEstimates.extraCosts')} ({form.currency})
              <input type="number" step="any" min="0" value={form.extra_costs || ''} placeholder="0" onChange={numField('extra_costs')} />
            </label>
          </div>
        </fieldset>

        <fieldset disabled={locked}>
          <legend>{t('voyageEstimates.sectionCargoFreight')}</legend>
          <div className="inline-row">
            <label>
              <input
                type="radio"
                name="freight_mode"
                checked={form.freight_mode === 'per_mt'}
                onChange={() => set('freight_mode', 'per_mt')}
              />{' '}
              {t('voyageEstimates.perMt')}
            </label>
            <label>
              <input
                type="radio"
                name="freight_mode"
                checked={form.freight_mode === 'lumpsum'}
                onChange={() => set('freight_mode', 'lumpsum')}
              />{' '}
              {t('voyageEstimates.lumpSum')}
            </label>
          </div>
          {form.freight_mode === 'lumpsum' ? (
            <div className="field-grid">
              <label>
                {t('voyageEstimates.lumpsumFreight')} ({form.currency})
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={form.lumpsum_freight || ''} placeholder="0"
                  onChange={numField('lumpsum_freight')}
                />
              </label>
            </div>
          ) : (
            <>
              {form.cargo_lots.map((l, i) => (
                <div className="inline-row" key={i}>
                  <input
                    aria-label={`${t('voyageEstimates.cargoGrade')} ${i + 1}`}
                    placeholder={t('voyageEstimates.cargoGrade')}
                    value={l.grade}
                    onChange={(e) => updateLot(i, { grade: e.target.value })}
                  />
                  <input
                    type="number"
                    step="any"
                    min="0"
                    aria-label={`${t('voyageEstimates.lotQuantity')} ${i + 1}`}
                    placeholder={t('voyageEstimates.lotQuantity')}
                    value={l.quantity_mt || ''}
                    onChange={(e) => updateLot(i, { quantity_mt: Number(e.target.value) })}
                  />
                  <input
                    type="number"
                    step="any"
                    min="0"
                    aria-label={`${t('voyageEstimates.lotRate')} ${i + 1}`}
                    placeholder={`${t('voyageEstimates.lotRate')} (${form.currency}/MT)`}
                    value={l.freight_rate || ''}
                    onChange={(e) => updateLot(i, { freight_rate: Number(e.target.value) })}
                  />
                  <button
                    type="button"
                    aria-label={`${t('common.delete')} ${t('voyageEstimates.cargoGrade')} ${i + 1}`}
                    disabled={form.cargo_lots.length === 1}
                    onClick={() => set('cargo_lots', form.cargo_lots.filter((_, j) => j !== i))}
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                type="button"
                disabled={form.cargo_lots.length >= MAX_CARGO_LOTS}
                onClick={() => set('cargo_lots', [...form.cargo_lots, newLot()])}
              >
                {t('voyageEstimates.addCargoLot')}
              </button>
            </>
          )}
        </fieldset>

        <fieldset disabled={locked}>
          <legend>{t('voyageEstimates.sectionFuelPrices')}</legend>
          <p className="hint">{t('voyageEstimates.fuelPricesHint')}</p>
          <div className="field-grid">
            {FUEL_GRADES.map((grade) => (
              <label key={grade}>
                {grade} ({form.currency}/MT)
                <input
                  type="number"
                  step="any"
                  min="0"
                  aria-label={`${t('voyageEstimates.fuelPrice')} ${grade}`}
                  value={form.fuel_prices.find((p) => p.grade === grade)?.price_per_mt ?? ''}
                  onChange={(e) => setPrice(grade, e.target.value)}
                />
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset disabled={locked}>
          <legend>{t('voyageEstimates.sectionCosts')}</legend>
          <div className="field-grid">
            <label>
              {t('voyageEstimates.canalFees')} ({form.currency})
              <input type="number" step="any" min="0" value={form.canal_fees || ''} placeholder="0" onChange={numField('canal_fees')} />
            </label>
            <label>
              {t('voyageEstimates.portCharges')} ({form.currency})
              <input type="number" step="any" min="0" value={form.port_charges || ''} placeholder="0" onChange={numField('port_charges')} />
            </label>
            <label>
              {t('voyageEstimates.agentFees')} ({form.currency})
              <input type="number" step="any" min="0" value={form.agent_fees || ''} placeholder="0" onChange={numField('agent_fees')} />
            </label>
            <label>
              {t('voyageEstimates.bunkerSurcharge')} ({form.currency})
              <input
                type="number"
                step="any"
                min="0"
                value={form.bunker_surcharge || ''} placeholder="0"
                onChange={numField('bunker_surcharge')}
              />
            </label>
          </div>
          {form.cost_items.map((item, i) => (
            <div className="inline-row" key={i}>
              <input
                aria-label={`${t('voyageEstimates.costDescription')} ${i + 1}`}
                placeholder={t('voyageEstimates.costDescription')}
                value={item.description}
                onChange={(e) =>
                  set('cost_items', form.cost_items.map((c, j) => (j === i ? { ...c, description: e.target.value } : c)))
                }
              />
              <input
                type="number"
                step="any"
                min="0"
                aria-label={`${t('voyageEstimates.costAmount')} ${i + 1}`}
                placeholder={t('voyageEstimates.costAmount')}
                value={item.amount || ''}
                onChange={(e) =>
                  set('cost_items', form.cost_items.map((c, j) => (j === i ? { ...c, amount: Number(e.target.value) } : c)))
                }
              />
              <button
                type="button"
                aria-label={`${t('common.delete')} ${t('voyageEstimates.costDescription')} ${i + 1}`}
                onClick={() => set('cost_items', form.cost_items.filter((_, j) => j !== i))}
              >
                ×
              </button>
            </div>
          ))}
          <button type="button" onClick={() => set('cost_items', [...form.cost_items, { description: '', amount: 0 }])}>
            {t('voyageEstimates.addCostItem')}
          </button>
        </fieldset>

        <fieldset disabled={locked}>
          <legend>{t('voyageEstimates.sectionDemurrage')}</legend>
          <div className="field-grid">
            <label>
              {t('voyageEstimates.demurrageRate')} ({form.currency})
              <input type="number" step="any" min="0" value={form.demurrage_rate || ''} placeholder="0" onChange={numField('demurrage_rate')} />
            </label>
          </div>
        </fieldset>

        <div className="estimate-actions no-print">
          <button type="button" onClick={handleCalculate}>
            {t('voyageEstimates.calculateButton')}
          </button>
          {!locked && (
            <button type="submit">
              {editingId !== null ? t('voyageEstimates.updateButton') : t('voyageEstimates.createButton')}
            </button>
          )}
          <button type="button" onClick={handleReset}>
            {editingId !== null ? t('common.cancel') : t('voyageEstimates.resetButton')}
          </button>
          {results && (
            <button type="button" onClick={handlePrint}>
              {t('voyageEstimates.printButton')}
            </button>
          )}
        </div>
      </form>

      {error && (
        <p role="alert" className="alert-danger">
          {error}
        </p>
      )}

      {results && <VoyageEstimateResults results={results} form={form} vesselName={vessel?.name ?? ''} />}

      <h2>{t('voyageEstimates.portListHeading')}</h2>
      <p className="hint">{t('voyageEstimates.portListHint')}</p>
      <div className="inline-row">
        <input
          aria-label={t('voyageEstimates.newPort')}
          placeholder={t('voyageEstimates.newPort')}
          value={newPort}
          onChange={(e) => setNewPort(e.target.value)}
        />
        <button type="button" onClick={handleAddPort}>
          {t('voyageEstimates.addPortToList')}
        </button>
      </div>
      <div className="inline-row">
        {ports.map((p) => (
          <Badge key={p.id} tone="neutral">
            {p.name}{' '}
            <button type="button" aria-label={`${t('common.delete')} ${p.name}`} onClick={() => handleRemovePort(p)}>
              ×
            </button>
          </Badge>
        ))}
      </div>
    </div>
  )
}
