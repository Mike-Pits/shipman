import { useEffect, useState } from 'react'
import { createVessel, listVessels } from '../api/vessels'
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

const FUEL_MODES: { mode: FuelConsumptionMode; label: string }[] = [
  { mode: 'laden', label: 'Laden' },
  { mode: 'ballast', label: 'Ballast' },
  { mode: 'idle_anchor', label: 'Idle / Anchor' },
  { mode: 'discharging', label: 'Discharging' },
]

type FuelRates = Record<FuelConsumptionMode, { ifo: string; mgo: string }>

const EMPTY_FUEL_RATES: FuelRates = {
  laden: { ifo: '', mgo: '' },
  ballast: { ifo: '', mgo: '' },
  idle_anchor: { ifo: '', mgo: '' },
  discharging: { ifo: '', mgo: '' },
}

export default function VesselsPage() {
  const [vessels, setVessels] = useState<Vessel[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<VesselCreate>(EMPTY_FORM)
  const [fuelRates, setFuelRates] = useState<FuelRates>(EMPTY_FUEL_RATES)
  const [error, setError] = useState<string | null>(null)

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const fuel_consumption_profiles = FUEL_MODES.map(({ mode }) => ({
        mode,
        ifo_mt_per_day: Number(fuelRates[mode].ifo) || 0,
        mgo_mt_per_day: Number(fuelRates[mode].mgo) || 0,
      }))
      await createVessel({ ...form, fuel_consumption_profiles })
      setForm(EMPTY_FORM)
      setFuelRates(EMPTY_FUEL_RATES)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to register vessel')
    }
  }

  return (
    <div>
      <h1>Vessels</h1>

      {loading ? (
        <p>Loading…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>IMO</th>
              <th>Ice Class</th>
            </tr>
          </thead>
          <tbody>
            {vessels.map((v) => (
              <tr key={v.id}>
                <td>{v.name}</td>
                <td>{v.imo_number}</td>
                <td>{v.ice_class}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>Register Vessel</h2>
      <form onSubmit={handleSubmit}>
        <label>
          Name
          <input value={form.name} onChange={field('name')} required />
        </label>
        <label>
          IMO Number
          <input value={form.imo_number} onChange={field('imo_number')} required />
        </label>
        <label>
          Flag
          <input value={form.flag} onChange={field('flag')} required />
        </label>
        <label>
          Year Built
          <input type="number" value={form.year_built || ''} onChange={field('year_built', true)} required />
        </label>
        <label>
          DWT
          <input type="number" value={form.dwt || ''} onChange={field('dwt', true)} required />
        </label>
        <label>
          LOA
          <input type="number" value={form.loa || ''} onChange={field('loa', true)} required />
        </label>
        <label>
          Beam
          <input type="number" value={form.beam || ''} onChange={field('beam', true)} required />
        </label>
        <label>
          Draft
          <input type="number" value={form.draft || ''} onChange={field('draft', true)} required />
        </label>
        <label>
          Cargo Tank Capacity (cbm)
          <input
            type="number"
            value={form.cargo_tank_capacity_cbm || ''}
            onChange={field('cargo_tank_capacity_cbm', true)}
            required
          />
        </label>
        <label>
          Ice Class
          <input value={form.ice_class} onChange={field('ice_class')} required />
        </label>
        <label>
          Engine Power (kW)
          <input
            type="number"
            value={form.engine_power_kw || ''}
            onChange={field('engine_power_kw', true)}
            required
          />
        </label>
        <h3 style={{ gridColumn: '1 / -1', marginBottom: 0 }}>Fuel Consumption (MT/day)</h3>
        {FUEL_MODES.map(({ mode, label }) => (
          <label key={`${mode}-ifo`}>
            {label} IFO
            <input type="number" step="0.01" value={fuelRates[mode].ifo} onChange={fuelField(mode, 'ifo')} />
          </label>
        ))}
        {FUEL_MODES.map(({ mode, label }) => (
          <label key={`${mode}-mgo`}>
            {label} MGO
            <input type="number" step="0.01" value={fuelRates[mode].mgo} onChange={fuelField(mode, 'mgo')} />
          </label>
        ))}

        <button type="submit">Register Vessel</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
