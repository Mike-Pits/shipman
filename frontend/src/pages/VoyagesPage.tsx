import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { listFixtures } from '../api/fixtures'
import { listVessels } from '../api/vessels'
import { createVoyage, listVoyages, updateVoyage } from '../api/voyages'
import Badge, { type BadgeTone } from '../components/ui/Badge'
import type { Fixture, FixtureType, Vessel, Voyage, VoyageCreate, VoyagePurpose } from '../api/types'

const FIXTURE_TYPE_LABEL_KEYS: Record<FixtureType, string> = {
  voyage_charter: 'fixtures.typeVoyageCharter',
  time_charter_out: 'fixtures.typeTimeCharterOut',
  coa: 'fixtures.typeCoa',
}

const fixtureLabel = (f: Fixture, t: (key: string) => string) =>
  `${f.charterer} — ${f.charter_party_ref ?? `#${f.id}`} (${t(FIXTURE_TYPE_LABEL_KEYS[f.fixture_type])})`

const PURPOSE_LABEL_KEYS: Record<VoyagePurpose, string> = {
  employment: 'voyages.purposeEmployment',
  ballast_passage: 'voyages.purposeBallastPassage',
  drydock_repair: 'voyages.purposeDrydockRepair',
}

const PURPOSE_TONES: Record<VoyagePurpose, BadgeTone> = {
  employment: 'success',
  ballast_passage: 'warning',
  drydock_repair: 'neutral',
}

const LOAD_PORT_LABEL_KEYS: Record<VoyagePurpose, string> = {
  employment: 'voyages.loadPort',
  ballast_passage: 'voyages.fromPort',
  drydock_repair: 'voyages.yardPort',
}

const EMPTY_FORM: VoyageCreate = {
  voyage_purpose: 'employment',
  fixture_id: null,
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

  const handlePurposeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setForm({ ...EMPTY_FORM, voyage_purpose: e.target.value as VoyagePurpose })
  }

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

  const purpose = form.voyage_purpose

  return (
    <div>
      <h1>{t('voyages.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('voyages.columnVoyageNumber')}</th>
                <th>{t('voyages.columnPurpose')}</th>
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
                  <td>
                    <Badge tone={PURPOSE_TONES[v.voyage_purpose]}>{t(PURPOSE_LABEL_KEYS[v.voyage_purpose])}</Badge>
                  </td>
                  <td>{vesselName(v.vessel_id)}</td>
                  <td>{v.load_port}</td>
                  <td>{v.discharge_port ?? '—'}</td>
                  <td>{v.start_date}</td>
                  <td>{v.cargo_quantity_mt ?? '—'}</td>
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
        </div>
      )}

      <h2>{editingId !== null ? t('voyages.editVoyage') : t('voyages.createVoyage')}</h2>
      {editingId !== null && <p role="alert">{t('voyages.editWarning')}</p>}
      <form onSubmit={handleSubmit}>
        <label>
          {t('voyages.purpose')}
          <select value={purpose} onChange={handlePurposeChange} disabled={editingId !== null}>
            <option value="employment">{t('voyages.purposeEmployment')}</option>
            <option value="ballast_passage">{t('voyages.purposeBallastPassage')}</option>
            <option value="drydock_repair">{t('voyages.purposeDrydockRepair')}</option>
          </select>
        </label>
        {purpose === 'employment' && (
          <label>
            {t('voyages.fixture')}
            <select value={form.fixture_id ?? ''} onChange={field('fixture_id', true)} required>
              <option value="" disabled>
                {t('voyages.selectFixture')}
              </option>
              {fixtures.map((f) => (
                <option key={f.id} value={f.id}>
                  {fixtureLabel(f, t)}
                </option>
              ))}
            </select>
          </label>
        )}
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
          {t(LOAD_PORT_LABEL_KEYS[purpose])}
          <input value={form.load_port} onChange={field('load_port')} required />
        </label>
        {purpose !== 'drydock_repair' && (
          <label>
            {t(purpose === 'ballast_passage' ? 'voyages.toPort' : 'voyages.dischargePort')}
            <input value={form.discharge_port ?? ''} onChange={field('discharge_port')} required />
          </label>
        )}
        <label>
          {t('voyages.startDate')}
          <input value={form.start_date} onChange={field('start_date')} placeholder="YYYY-MM-DD" required />
        </label>
        <label>
          {t('voyages.endDate')}
          <input value={form.end_date ?? ''} onChange={field('end_date')} placeholder="YYYY-MM-DD" />
        </label>
        {purpose === 'employment' && (
          <>
            <label>
              {t('voyages.cargoGrade')}
              <input value={form.cargo_grade ?? ''} onChange={field('cargo_grade')} required />
            </label>
            <label>
              {t('voyages.cargoQuantity')}
              <input
                type="number"
                value={form.cargo_quantity_mt ?? ''}
                onChange={field('cargo_quantity_mt', true)}
                required
              />
            </label>
            <label>
              {t('voyages.laden')}
              <input
                type="checkbox"
                checked={form.laden}
                onChange={(e) => setForm((f) => ({ ...f, laden: e.target.checked }))}
              />
            </label>
          </>
        )}
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
      {error && (
        <p role="alert" className="alert-danger">
          {error}
        </p>
      )}
    </div>
  )
}
