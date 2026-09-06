import { Fragment, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createBunkerReplenishment, listBunkerReplenishments } from '../api/bunkerReplenishments'
import { listVessels } from '../api/vessels'
import type { BunkerReplenishment, BunkerReplenishmentCreate, Vessel } from '../api/types'

const EMPTY_FORM: Omit<BunkerReplenishmentCreate, 'lines'> = {
  vessel_id: 0,
  replenishment_datetime: '',
  port: '',
  supplier: '',
  invoice_number: '',
  currency: '',
}

type LineRow = { grade: string; labelKey: string; quantity: string; price: string }
const EMPTY_LINES: LineRow[] = [
  { grade: 'IFO', labelKey: 'bunkers.gradeIfo', quantity: '', price: '' },
  { grade: 'MGO', labelKey: 'bunkers.gradeMgo', quantity: '', price: '' },
]

export default function BunkerReplenishmentsPage() {
  const { t } = useTranslation()
  const [replenishments, setReplenishments] = useState<BunkerReplenishment[]>([])
  const [vessels, setVessels] = useState<Vessel[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState(EMPTY_FORM)
  const [lines, setLines] = useState<LineRow[]>(EMPTY_LINES)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = () => listBunkerReplenishments().then(setReplenishments)

  useEffect(() => {
    Promise.all([refresh(), listVessels().then(setVessels)]).finally(() => setLoading(false))
  }, [])

  const vesselName = (id: number) => vessels.find((v) => v.id === id)?.name ?? `#${id}`

  const field =
    (key: keyof typeof EMPTY_FORM, numeric = false) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: numeric ? Number(e.target.value) : e.target.value }))

  const lineField = (grade: string, key: 'quantity' | 'price') => (e: React.ChangeEvent<HTMLInputElement>) =>
    setLines((rows) => rows.map((row) => (row.grade === grade ? { ...row, [key]: e.target.value } : row)))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const payload: BunkerReplenishmentCreate = {
        ...form,
        lines: lines
          .filter((row) => row.quantity.trim() !== '' || row.price.trim() !== '')
          .map((row) => ({
            fuel_grade: row.grade,
            quantity_mt: Number(row.quantity) || 0,
            price_per_mt: Number(row.price) || 0,
          })),
      }
      await createBunkerReplenishment(payload)
      setForm(EMPTY_FORM)
      setLines(EMPTY_LINES)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record replenishment')
    }
  }

  return (
    <div>
      <h1>{t('bunkers.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t('bunkers.columnDatetime')}</th>
              <th>{t('bunkers.columnVessel')}</th>
              <th>{t('bunkers.columnPort')}</th>
              <th>{t('bunkers.columnSupplier')}</th>
              <th>{t('bunkers.columnCurrency')}</th>
              <th>{t('bunkers.columnTotalCost')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {replenishments.map((r) => (
              <Fragment key={r.id}>
                <tr>
                  <td>{r.replenishment_datetime}</td>
                  <td>{vesselName(r.vessel_id)}</td>
                  <td>{r.port}</td>
                  <td>{r.supplier}</td>
                  <td>{r.currency}</td>
                  <td>{r.total_cost}</td>
                  <td>
                    <button type="button" onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}>
                      {expandedId === r.id ? t('bunkers.hideLines') : t('bunkers.viewLines')}
                    </button>
                  </td>
                </tr>
                {expandedId === r.id && (
                  <tr>
                    <td colSpan={7}>
                      <table>
                        <thead>
                          <tr>
                            <th>{t('bunkers.lineColumnGrade')}</th>
                            <th>{t('bunkers.lineColumnQuantity')}</th>
                            <th>{t('bunkers.lineColumnPrice')}</th>
                            <th>{t('bunkers.lineColumnTotal')}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {r.lines.map((line) => (
                            <tr key={line.id}>
                              <td>{line.fuel_grade}</td>
                              <td>{line.quantity_mt}</td>
                              <td>{line.price_per_mt}</td>
                              <td>{line.total_cost}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}

      <h2>{t('bunkers.createHeading')}</h2>
      <form onSubmit={handleSubmit}>
        <label>
          {t('bunkers.vesselContext')}
          <select value={form.vessel_id || ''} onChange={field('vessel_id', true)} required>
            <option value="" disabled>
              {t('bunkers.selectVessel')}
            </option>
            {vessels.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('bunkers.datetime')}
          <input
            value={form.replenishment_datetime}
            onChange={field('replenishment_datetime')}
            placeholder="YYYY-MM-DD HH:MM:SS"
            required
          />
        </label>
        <label>
          {t('bunkers.port')}
          <input value={form.port} onChange={field('port')} required />
        </label>
        <label>
          {t('bunkers.supplier')}
          <input value={form.supplier} onChange={field('supplier')} required />
        </label>
        <label>
          {t('bunkers.invoiceNumber')}
          <input value={form.invoice_number ?? ''} onChange={field('invoice_number')} />
        </label>
        <label>
          {t('bunkers.currency')}
          <input value={form.currency} onChange={field('currency')} required />
        </label>

        <h3>{t('bunkers.linesHeading')}</h3>
        {lines.map((row) => (
          <div key={row.grade}>
            <label>
              {t(row.labelKey)} {t('bunkers.quantity')}
              <input type="number" step="0.01" value={row.quantity} onChange={lineField(row.grade, 'quantity')} />
            </label>
            <label>
              {t(row.labelKey)} {t('bunkers.pricePerMt')}
              <input type="number" step="0.01" value={row.price} onChange={lineField(row.grade, 'price')} />
            </label>
          </div>
        ))}

        <button type="submit">{t('bunkers.createButton')}</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
