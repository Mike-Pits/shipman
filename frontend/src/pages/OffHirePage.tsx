import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createOffHirePeriod, listOffHirePeriods, updateOffHirePeriod } from '../api/offHirePeriods'
import { listVoyages } from '../api/voyages'
import type { OffHirePeriod, OffHirePeriodCreate, Voyage } from '../api/types'

const EMPTY_FORM: OffHirePeriodCreate = {
  start_datetime: '',
  end_datetime: '',
  reason: '',
  override_deduction: null,
}

export default function OffHirePage() {
  const { t } = useTranslation()
  const [voyages, setVoyages] = useState<Voyage[]>([])
  const [loading, setLoading] = useState(true)
  const [voyageId, setVoyageId] = useState<number | ''>('')
  const [periods, setPeriods] = useState<OffHirePeriod[]>([])
  const [form, setForm] = useState<OffHirePeriodCreate>(EMPTY_FORM)
  const [overrideText, setOverrideText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)

  useEffect(() => {
    listVoyages()
      .then(setVoyages)
      .finally(() => setLoading(false))
  }, [])

  const handleVoyageChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value ? Number(e.target.value) : ''
    setVoyageId(id)
    setPeriods([])
    setForm(EMPTY_FORM)
    setOverrideText('')
    setEditingId(null)
    setError(null)
    if (id === '') return
    setPeriods(await listOffHirePeriods(id))
  }

  const field =
    (key: 'start_datetime' | 'end_datetime' | 'reason') => (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }))

  const handleEdit = (period: OffHirePeriod) => {
    setError(null)
    setEditingId(period.id)
    setForm({
      start_datetime: period.start_datetime,
      end_datetime: period.end_datetime,
      reason: period.reason,
      override_deduction: period.override_deduction,
    })
    setOverrideText(period.override_deduction != null ? String(period.override_deduction) : '')
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setForm(EMPTY_FORM)
    setOverrideText('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (voyageId === '') return
    setError(null)
    try {
      const payload = {
        ...form,
        override_deduction: overrideText.trim() === '' ? null : Number(overrideText),
      }
      if (editingId !== null) {
        await updateOffHirePeriod(voyageId, editingId, payload)
      } else {
        await createOffHirePeriod(voyageId, payload)
      }
      handleCancelEdit()
      setPeriods(await listOffHirePeriods(voyageId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record off-hire period')
    }
  }

  return (
    <div>
      <h1>{t('offHire.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <label>
          {t('offHire.voyage')}
          <select value={voyageId} onChange={handleVoyageChange}>
            <option value="">{t('offHire.selectVoyage')}</option>
            {voyages.map((v) => (
              <option key={v.id} value={v.id}>
                {v.voyage_number}
              </option>
            ))}
          </select>
        </label>
      )}

      {error && (
        <p role="alert" className="alert-danger">
          {error}
        </p>
      )}

      {voyageId !== '' && (
        <>
          <section>
            <h2>{t('offHire.historyHeading')}</h2>
            <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t('offHire.columnStart')}</th>
                  <th>{t('offHire.columnEnd')}</th>
                  <th>{t('offHire.columnDuration')}</th>
                  <th>{t('offHire.columnReason')}</th>
                  <th>{t('offHire.columnCalculatedDeduction')}</th>
                  <th>{t('offHire.columnOverrideDeduction')}</th>
                  <th>{t('offHire.columnEffectiveDeduction')}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {periods.map((p) => (
                  <tr key={p.id}>
                    <td>{p.start_datetime}</td>
                    <td>{p.end_datetime}</td>
                    <td>{p.duration_days}</td>
                    <td>{p.reason}</td>
                    <td>{p.calculated_deduction}</td>
                    <td>{p.override_deduction ?? ''}</td>
                    <td>{p.effective_deduction}</td>
                    <td>
                      <button type="button" onClick={() => handleEdit(p)}>
                        {t('common.edit')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </section>

          <section>
            <h2>{editingId !== null ? t('offHire.editHeading') : t('offHire.createHeading')}</h2>
            {editingId !== null && <p role="alert">{t('offHire.editWarning')}</p>}
            <form onSubmit={handleSubmit}>
              <label>
                {t('offHire.startDatetime')}
                <input
                  value={form.start_datetime}
                  onChange={field('start_datetime')}
                  placeholder="YYYY-MM-DD HH:MM:SS"
                  required
                />
              </label>
              <label>
                {t('offHire.endDatetime')}
                <input
                  value={form.end_datetime}
                  onChange={field('end_datetime')}
                  placeholder="YYYY-MM-DD HH:MM:SS"
                  required
                />
              </label>
              <label>
                {t('offHire.reason')}
                <input value={form.reason} onChange={field('reason')} required />
              </label>
              <label>
                {t('offHire.overrideDeduction')}
                <input
                  type="number"
                  step="0.01"
                  value={overrideText}
                  onChange={(e) => setOverrideText(e.target.value)}
                />
              </label>
              <button type="submit">{editingId !== null ? t('offHire.updateButton') : t('offHire.createButton')}</button>
              {editingId !== null && (
                <button type="button" onClick={handleCancelEdit}>
                  {t('common.cancel')}
                </button>
              )}
            </form>
          </section>
        </>
      )}
    </div>
  )
}
