import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createVettingInspection, getVettingStatus, listVettingInspections } from '../api/vettingInspections'
import { listVessels } from '../api/vessels'
import type { Vessel, VettingInspection, VettingInspectionCreate, VettingStatus, VettingStatusRead } from '../api/types'

const EMPTY_FORM: VettingInspectionCreate = {
  inspection_date: '',
  inspecting_body: '',
  inspection_type: '',
  expiry_date: '',
  status: '' as VettingStatus,
  observations: '',
}

const STATUS_KEYS: Record<VettingStatus, string> = {
  approved: 'vetting.statusApproved',
  pending: 'vetting.statusPending',
  expired: 'vetting.statusExpired',
  failed: 'vetting.statusFailed',
}

export default function VettingInspectionsPage() {
  const { t } = useTranslation()
  const [vessels, setVessels] = useState<Vessel[]>([])
  const [loading, setLoading] = useState(true)
  const [vesselId, setVesselId] = useState<number | ''>('')
  const [status, setStatus] = useState<VettingStatusRead | null>(null)
  const [inspections, setInspections] = useState<VettingInspection[]>([])
  const [form, setForm] = useState<VettingInspectionCreate>(EMPTY_FORM)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listVessels()
      .then(setVessels)
      .finally(() => setLoading(false))
  }, [])

  const handleVesselChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value ? Number(e.target.value) : ''
    setVesselId(id)
    setStatus(null)
    setInspections([])
    setForm(EMPTY_FORM)
    setError(null)
    if (id === '') return
    setStatus(await getVettingStatus(id))
    setInspections(await listVettingInspections(id))
  }

  const field =
    (key: keyof VettingInspectionCreate) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (vesselId === '') return
    setError(null)
    try {
      await createVettingInspection(vesselId, form)
      setForm(EMPTY_FORM)
      setStatus(await getVettingStatus(vesselId))
      setInspections(await listVettingInspections(vesselId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record inspection')
    }
  }

  return (
    <div>
      <h1>{t('vetting.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <label>
          {t('vetting.vessel')}
          <select value={vesselId} onChange={handleVesselChange}>
            <option value="">{t('vetting.selectVessel')}</option>
            {vessels.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </label>
      )}

      {error && <p role="alert">{error}</p>}

      {vesselId !== '' && status && (
        <section>
          <h2>{t('vetting.currentStatusHeading')}</h2>
          {status.status === null ? (
            <p>{t('vetting.noInspections')}</p>
          ) : (
            <table>
              <tbody>
                <tr>
                  <th>{t('vetting.statusLabel')}</th>
                  <td>{t(STATUS_KEYS[status.status])}</td>
                </tr>
                <tr>
                  <th>{t('vetting.inspectingBody')}</th>
                  <td>{status.inspecting_body}</td>
                </tr>
                <tr>
                  <th>{t('vetting.expiryDate')}</th>
                  <td>{status.expiry_date}</td>
                </tr>
              </tbody>
            </table>
          )}
        </section>
      )}

      {vesselId !== '' && inspections.length > 0 && (
        <section>
          <h2>{t('vetting.historyHeading')}</h2>
          <table>
            <thead>
              <tr>
                <th>{t('vetting.columnInspectionDate')}</th>
                <th>{t('vetting.columnInspectingBody')}</th>
                <th>{t('vetting.columnInspectionType')}</th>
                <th>{t('vetting.columnExpiryDate')}</th>
                <th>{t('vetting.columnStatus')}</th>
                <th>{t('vetting.columnObservations')}</th>
              </tr>
            </thead>
            <tbody>
              {inspections.map((insp) => (
                <tr key={insp.id}>
                  <td>{insp.inspection_date}</td>
                  <td>{insp.inspecting_body}</td>
                  <td>{insp.inspection_type}</td>
                  <td>{insp.expiry_date}</td>
                  <td>{t(STATUS_KEYS[insp.status])}</td>
                  <td>{insp.observations}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {vesselId !== '' && (
        <section>
          <h2>{t('vetting.createHeading')}</h2>
          <form onSubmit={handleSubmit}>
            <label>
              {t('vetting.inspectionDate')}
              <input value={form.inspection_date} onChange={field('inspection_date')} placeholder="YYYY-MM-DD" required />
            </label>
            <label>
              {t('vetting.inspectingBody')}
              <input value={form.inspecting_body} onChange={field('inspecting_body')} required />
            </label>
            <label>
              {t('vetting.inspectionType')}
              <input value={form.inspection_type} onChange={field('inspection_type')} required />
            </label>
            <label>
              {t('vetting.expiryDate')}
              <input value={form.expiry_date} onChange={field('expiry_date')} placeholder="YYYY-MM-DD" required />
            </label>
            <label>
              {t('vetting.statusLabel')}
              <select value={form.status} onChange={field('status')} required>
                <option value="" disabled>
                  {t('vetting.selectStatus')}
                </option>
                <option value="approved">{t('vetting.statusApproved')}</option>
                <option value="pending">{t('vetting.statusPending')}</option>
                <option value="expired">{t('vetting.statusExpired')}</option>
                <option value="failed">{t('vetting.statusFailed')}</option>
              </select>
            </label>
            <label>
              {t('vetting.observations')}
              <input value={form.observations ?? ''} onChange={field('observations')} />
            </label>
            <button type="submit">{t('vetting.createButton')}</button>
          </form>
        </section>
      )}
    </div>
  )
}
