import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createVessel, deleteVessel, listVessels, updateVessel } from '../api/vessels'
import type {
  FuelConsumptionMode,
  PortConsumption,
  PortConsumptionKind,
  SeaConsumption,
  SeaMode,
  Vessel,
  VesselCreate,
} from '../api/types'

const EMPTY_FORM: VesselCreate = {
  name: '',
  imo_number: '',
  flag: '',
  year_built: 0,
  vessel_type: 'clean/product tanker',
  dwt: 0,
  loa: 0,
  beam: 0,
  draft: 0,
  cargo_tank_capacity_cbm: 0,
  ice_class: '',
  engine_power_kw: 0,
  fuel_consumption_profiles: [],
}

const FUEL_MODE_KEYS: { mode: FuelConsumptionMode; labelKey: string }[] = [
  { mode: 'laden', labelKey: 'vessels.modeLaden' },
  { mode: 'ballast', labelKey: 'vessels.modeBallast' },
  { mode: 'idle_anchor', labelKey: 'vessels.modeIdleAnchor' },
  { mode: 'discharging', labelKey: 'vessels.modeDischarging' },
]

const SEA_MODES: { mode: SeaMode; labelKey: string }[] = [
  { mode: 'laden', labelKey: 'vessels.modeLaden' },
  { mode: 'ballast', labelKey: 'vessels.modeBallast' },
  { mode: 'eco', labelKey: 'vessels.modeEco' },
]

const PORT_KINDS: { kind: PortConsumptionKind; labelKey: string }[] = [
  { kind: 'port_load', labelKey: 'vessels.portLoad' },
  { kind: 'port_discharge', labelKey: 'vessels.portDischarge' },
  { kind: 'inerting', labelKey: 'vessels.inerting' },
]

type FuelRates = Record<FuelConsumptionMode, { ifo: string; mgo: string }>

const EMPTY_FUEL_RATES: FuelRates = {
  laden: { ifo: '', mgo: '' },
  ballast: { ifo: '', mgo: '' },
  idle_anchor: { ifo: '', mgo: '' },
  discharging: { ifo: '', mgo: '' },
}

export default function VesselsPage() {
  const { t } = useTranslation()
  const [vessels, setVessels] = useState<Vessel[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<VesselCreate>(EMPTY_FORM)
  const [fuelRates, setFuelRates] = useState<FuelRates>(EMPTY_FUEL_RATES)
  const [seaRows, setSeaRows] = useState<SeaConsumption[]>([])
  const [portRows, setPortRows] = useState<PortConsumption[]>([])
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)

  const refresh = () => listVessels().then(setVessels)

  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [])

  const field =
    (key: keyof VesselCreate, numeric = false) =>
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [key]: numeric ? Number(e.target.value) : e.target.value }))

  const fuelField =
    (mode: FuelConsumptionMode, grade: 'ifo' | 'mgo') => (e: React.ChangeEvent<HTMLInputElement>) =>
      setFuelRates((rates) => ({ ...rates, [mode]: { ...rates[mode], [grade]: e.target.value } }))

  const updateSeaRow = (index: number, patch: Partial<SeaConsumption>) =>
    setSeaRows((rows) => rows.map((r, i) => (i === index ? { ...r, ...patch } : r)))
  const updatePortRow = (index: number, patch: Partial<PortConsumption>) =>
    setPortRows((rows) => rows.map((r, i) => (i === index ? { ...r, ...patch } : r)))

  const handleDelete = async (vessel: Vessel) => {
    if (!window.confirm(t('vessels.deleteConfirm', { name: vessel.name }))) return
    setError(null)
    try {
      await deleteVessel(vessel.id)
      if (editingId === vessel.id) handleCancelEdit()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete vessel')
    }
  }

  const handleEdit = (vessel: Vessel) => {
    setError(null)
    setEditingId(vessel.id)
    const { fuel_consumption_profiles, sea_consumption, port_consumption, ...rest } = vessel
    setForm({ ...rest, fuel_consumption_profiles: [] })
    setSeaRows(sea_consumption ?? [])
    setPortRows(port_consumption ?? [])
    const rates = { ...EMPTY_FUEL_RATES }
    for (const profile of fuel_consumption_profiles) {
      rates[profile.mode] = { ifo: String(profile.ifo_mt_per_day), mgo: String(profile.mgo_mt_per_day) }
    }
    setFuelRates(rates)
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setForm(EMPTY_FORM)
    setFuelRates(EMPTY_FUEL_RATES)
    setSeaRows([])
    setPortRows([])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const fuel_consumption_profiles = FUEL_MODE_KEYS.map(({ mode }) => ({
        mode,
        ifo_mt_per_day: Number(fuelRates[mode].ifo) || 0,
        mgo_mt_per_day: Number(fuelRates[mode].mgo) || 0,
      }))
      const payload = {
        ...form,
        fuel_consumption_profiles,
        sea_consumption: seaRows.filter((r) => r.grade.trim()),
        port_consumption: portRows.filter((r) => r.grade.trim()),
      }
      if (editingId !== null) {
        await updateVessel(editingId, payload)
      } else {
        await createVessel(payload)
      }
      handleCancelEdit()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save vessel')
    }
  }

  return (
    <div>
      <h1>{t('vessels.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('vessels.columnName')}</th>
                <th>{t('vessels.columnImo')}</th>
                <th>{t('vessels.columnIceClass')}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {vessels.map((v) => (
                <tr key={v.id}>
                  <td>{v.name}</td>
                  <td>{v.imo_number}</td>
                  <td>{v.ice_class}</td>
                  <td>
                    <button type="button" onClick={() => handleEdit(v)}>
                      {t('common.edit')}
                    </button>
                    <button type="button" onClick={() => handleDelete(v)}>
                      {t('common.delete')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2>{editingId !== null ? t('vessels.editVessel') : t('vessels.registerVessel')}</h2>
      <form onSubmit={handleSubmit}>
        <label>
          {t('vessels.name')}
          <input value={form.name} onChange={field('name')} required />
        </label>
        <label>
          {t('vessels.imoNumber')}
          <input value={form.imo_number} onChange={field('imo_number')} required />
        </label>
        <label>
          {t('vessels.flag')}
          <input value={form.flag} onChange={field('flag')} required />
        </label>
        <label>
          {t('vessels.yearBuilt')}
          <input type="number" value={form.year_built} onChange={field('year_built', true)} required />
        </label>
        <label>
          {t('vessels.dwt')}
          <input type="number" value={form.dwt} onChange={field('dwt', true)} required />
        </label>
        <label>
          {t('vessels.loa')}
          <input type="number" value={form.loa} onChange={field('loa', true)} required />
        </label>
        <label>
          {t('vessels.beam')}
          <input type="number" value={form.beam} onChange={field('beam', true)} required />
        </label>
        <label>
          {t('vessels.draft')}
          <input type="number" value={form.draft} onChange={field('draft', true)} required />
        </label>
        <label>
          {t('vessels.cargoTankCapacity')}
          <input
            type="number"
            value={form.cargo_tank_capacity_cbm}
            onChange={field('cargo_tank_capacity_cbm', true)}
            required
          />
        </label>
        <label>
          {t('vessels.iceClass')}
          <input value={form.ice_class} onChange={field('ice_class')} required />
        </label>
        <label>
          {t('vessels.enginePower')}
          <input
            type="number"
            value={form.engine_power_kw}
            onChange={field('engine_power_kw', true)}
            required
          />
        </label>
        <h3 className="form-section-heading">{t('vessels.fuelConsumptionHeading')}</h3>
        {FUEL_MODE_KEYS.map(({ mode, labelKey }) => (
          <label key={`${mode}-ifo`}>
            {t(labelKey)} IFO
            <input type="number" step="0.01" value={fuelRates[mode].ifo} onChange={fuelField(mode, 'ifo')} />
          </label>
        ))}
        {FUEL_MODE_KEYS.map(({ mode, labelKey }) => (
          <label key={`${mode}-mgo`}>
            {t(labelKey)} MGO
            <input type="number" step="0.01" value={fuelRates[mode].mgo} onChange={fuelField(mode, 'mgo')} />
          </label>
        ))}

        <h3 className="form-section-heading">{t('vessels.calculatorHeading')}</h3>
        <p className="hint">{t('vessels.calculatorHint')}</p>
        {SEA_MODES.map(({ mode, labelKey }) => (
          <fieldset key={mode}>
            <legend>{t(labelKey)}</legend>
            {seaRows.map((row, i) =>
              row.mode !== mode ? null : (
                <div key={i} className="inline-row">
                  <input
                    aria-label={`${t(labelKey)} ${t('vessels.fuelGrade')}`}
                    placeholder={t('vessels.fuelGrade')}
                    value={row.grade}
                    onChange={(e) => updateSeaRow(i, { grade: e.target.value })}
                  />
                  <input
                    type="number"
                    step="0.1"
                    aria-label={`${t(labelKey)} ${t('vessels.speed')}`}
                    placeholder={t('vessels.speed')}
                    value={row.speed_kt || ''}
                    onChange={(e) => updateSeaRow(i, { speed_kt: Number(e.target.value) })}
                  />
                  <input
                    type="number"
                    step="0.01"
                    aria-label={`${t(labelKey)} ${t('vessels.consumption')}`}
                    placeholder={t('vessels.consumption')}
                    value={row.consumption_mt_per_day || ''}
                    onChange={(e) => updateSeaRow(i, { consumption_mt_per_day: Number(e.target.value) })}
                  />
                  <button type="button" onClick={() => setSeaRows((rows) => rows.filter((_, j) => j !== i))}>
                    {t('common.delete')}
                  </button>
                </div>
              ),
            )}
            <button
              type="button"
              onClick={() =>
                setSeaRows((rows) => [...rows, { mode, grade: '', speed_kt: 0, consumption_mt_per_day: 0 }])
              }
            >
              {t('vessels.addFuelGrade')} — {t(labelKey)}
            </button>
          </fieldset>
        ))}
        {PORT_KINDS.map(({ kind, labelKey }) => (
          <fieldset key={kind}>
            <legend>{t(labelKey)}</legend>
            {portRows.map((row, i) =>
              row.kind !== kind ? null : (
                <div key={i} className="inline-row">
                  <input
                    aria-label={`${t(labelKey)} ${t('vessels.fuelGrade')}`}
                    placeholder={t('vessels.fuelGrade')}
                    value={row.grade}
                    onChange={(e) => updatePortRow(i, { grade: e.target.value })}
                  />
                  <input
                    type="number"
                    step="0.01"
                    aria-label={`${t(labelKey)} ${t('vessels.consumption')}`}
                    placeholder={t('vessels.consumption')}
                    value={row.consumption_mt_per_day || ''}
                    onChange={(e) => updatePortRow(i, { consumption_mt_per_day: Number(e.target.value) })}
                  />
                  <button type="button" onClick={() => setPortRows((rows) => rows.filter((_, j) => j !== i))}>
                    {t('common.delete')}
                  </button>
                </div>
              ),
            )}
            <button
              type="button"
              onClick={() => setPortRows((rows) => [...rows, { kind, grade: '', consumption_mt_per_day: 0 }])}
            >
              {t('vessels.addFuelGrade')} — {t(labelKey)}
            </button>
          </fieldset>
        ))}

        <button type="submit">{editingId !== null ? t('vessels.updateVessel') : t('vessels.registerVessel')}</button>
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
