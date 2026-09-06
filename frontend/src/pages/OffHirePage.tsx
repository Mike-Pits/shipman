import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createOffHirePeriod, listOffHirePeriods } from '../api/offHirePeriods'
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
    setError(null)
    if (id === '') return
    setPeriods(await listOffHirePeriods(id))
  }

  const field =
    (key: 'start_datetime' | 'end_datetime' | 'reason') => (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (voyageId === '') return
    setError(null)
    try {
      await createOffHirePeriod(voyageId, {
        ...form,
        override_deduction: overrideText.trim() === '' ? null : Number(overrideText),
      })
      setForm(EMPTY_FORM)
      setOverrideText('')
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

      {error && <p role="alert">{error}</p>}

      {voyageId !== '' && (
        <>
          <section>
            <h2>{t('offHire.historyHeading')}</h2>
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
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h2>{t('offHire.createHeading')}</h2>
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
              <button type="submit">{t('offHire.createButton')}</button>
            </form>
          </section>
        </>
      )}
    </div>
  )
}
