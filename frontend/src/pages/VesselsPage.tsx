import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createVessel, deleteVessel, listVessels, updateVessel } from '../api/vessels'
import type { FuelConsumptionMode, Vessel, VesselCreate } from '../api/types'

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
    const { fuel_consumption_profiles, ...rest } = vessel
    setForm({ ...rest, fuel_consumption_profiles: [] })
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
      if (editingId !== null) {
        await updateVessel(editingId, { ...form, fuel_consumption_profiles })
      } else {
        await createVessel({ ...form, fuel_consumption_profiles })
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
        <div style={{ maxHeight: '27rem', overflowY: 'auto', border: '1px solid #ccc' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead style={{ position: 'sticky', top: 0, background: '#fff' }}>
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
        <h3 style={{ gridColumn: '1 / -1', marginBottom: 0 }}>{t('vessels.fuelConsumptionHeading')}</h3>
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

        <button type="submit">{editingId !== null ? t('vessels.updateVessel') : t('vessels.registerVessel')}</button>
        {editingId !== null && (
          <button type="button" onClick={handleCancelEdit}>
            {t('common.cancel')}
          </button>
        )}
      </form>
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
