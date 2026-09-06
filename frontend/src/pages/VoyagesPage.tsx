import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { listFixtures } from '../api/fixtures'
import { listVessels } from '../api/vessels'
import { createVoyage, listVoyages, updateVoyage } from '../api/voyages'
import type { Fixture, Vessel, Voyage, VoyageCreate } from '../api/types'

const EMPTY_FORM: VoyageCreate = {
  fixture_id: 0,
  vessel_id: 0,
  voyage_number: '',
  load_port: '',
  discharge_port: '',
  start_date: '',
  end_date: '',
  cargo_grade: '',
  cargo_quantity_mt: 0,
  laden: false,
  ice_notes: '',
}

export default function VoyagesPage() {
  const { t } = useTranslation()
  const [voyages, setVoyages] = useState<Voyage[]>([])
  const [vessels, setVessels] = useState<Vessel[]>([])
  const [fixtures, setFixtures] = useState<Fixture[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<VoyageCreate>(EMPTY_FORM)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)

  const refresh = () => listVoyages().then(setVoyages)

  useEffect(() => {
    Promise.all([refresh(), listVessels().then(setVessels), listFixtures().then(setFixtures)]).finally(() =>
      setLoading(false),
    )
  }, [])

  const vesselName = (id: number) => vessels.find((v) => v.id === id)?.name ?? `#${id}`

  const field =
    (key: keyof VoyageCreate, numeric = false) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: numeric ? Number(e.target.value) : e.target.value }))

  const handleEdit = (voyage: Voyage) => {
    setError(null)
    setEditingId(voyage.id)
    const { warnings, ...rest } = voyage
    setForm(rest)
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setForm(EMPTY_FORM)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const payload: VoyageCreate = { ...form, end_date: form.end_date || null }
    try {
      if (editingId !== null) {
        await updateVoyage(editingId, payload)
      } else {
        await createVoyage(payload)
      }
      handleCancelEdit()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save voyage')
    }
  }

  return (
    <div>
      <h1>{t('voyages.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t('voyages.columnVoyageNumber')}</th>
              <th>{t('voyages.columnVessel')}</th>
              <th>{t('voyages.columnLoadPort')}</th>
              <th>{t('voyages.columnDischargePort')}</th>
              <th>{t('voyages.columnStartDate')}</th>
              <th>{t('voyages.columnCargoQty')}</th>
              <th></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {voyages.map((v) => (
              <tr key={v.id}>
                <td>{v.voyage_number}</td>
                <td>{vesselName(v.vessel_id)}</td>
                <td>{v.load_port}</td>
                <td>{v.discharge_port}</td>
                <td>{v.start_date}</td>
                <td>{v.cargo_quantity_mt}</td>
                <td>
                  {v.warnings.map((w, i) => (
                    <p key={i} role="alert">
                      {w}
                    </p>
                  ))}
                </td>
                <td>
                  <button type="button" onClick={() => handleEdit(v)}>
                    {t('common.edit')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>{editingId !== null ? t('voyages.editVoyage') : t('voyages.createVoyage')}</h2>
      {editingId !== null && <p role="alert">{t('voyages.editWarning')}</p>}
      <form onSubmit={handleSubmit}>
        <label>
          {t('voyages.fixture')}
          <select value={form.fixture_id || ''} onChange={field('fixture_id', true)} required>
            <option value="" disabled>
              {t('voyages.selectFixture')}
            </option>
            {fixtures.map((f) => (
              <option key={f.id} value={f.id}>
                #{f.id} — {f.charterer} ({f.fixture_type})
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('voyages.vessel')}
          <select value={form.vessel_id || ''} onChange={field('vessel_id', true)} required>
            <option value="" disabled>
              {t('voyages.selectVessel')}
            </option>
            {vessels.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('voyages.voyageNumber')}
          <input value={form.voyage_number} onChange={field('voyage_number')} required />
        </label>
        <label>
          {t('voyages.loadPort')}
          <input value={form.load_port} onChange={field('load_port')} required />
        </label>
        <label>
          {t('voyages.dischargePort')}
          <input value={form.discharge_port} onChange={field('discharge_port')} required />
        </label>
        <label>
          {t('voyages.startDate')}
          <input value={form.start_date} onChange={field('start_date')} placeholder="YYYY-MM-DD" required />
        </label>
        <label>
          {t('voyages.endDate')}
          <input value={form.end_date ?? ''} onChange={field('end_date')} placeholder="YYYY-MM-DD" />
        </label>
        <label>
          {t('voyages.cargoGrade')}
          <input value={form.cargo_grade} onChange={field('cargo_grade')} required />
        </label>
        <label>
          {t('voyages.cargoQuantity')}
          <input type="number" value={form.cargo_quantity_mt} onChange={field('cargo_quantity_mt', true)} required />
        </label>
        <label>
          {t('voyages.laden')}
          <input
            type="checkbox"
            checked={form.laden}
            onChange={(e) => setForm((f) => ({ ...f, laden: e.target.checked }))}
          />
        </label>
        <label>
          {t('voyages.iceNsrNotes')}
          <input value={form.ice_notes ?? ''} onChange={field('ice_notes')} />
        </label>

        <button type="submit">{editingId !== null ? t('voyages.updateVoyage') : t('voyages.createVoyage')}</button>
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
