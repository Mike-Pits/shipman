import { Fragment, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  addFdaLines,
  createDisbursementAccount,
  disputeDisbursementAccount,
  listDisbursementAccounts,
  reconcileDisbursementAccount,
} from '../api/disbursementAccounts'
import { listVoyages } from '../api/voyages'
import type { DisbursementAccount, DisbursementAccountCreate, Voyage } from '../api/types'

const EMPTY_FORM: DisbursementAccountCreate = {
  voyage_id: 0,
  port: '',
  pda_amount: 0,
  pda_currency: '',
  pda_date: '',
}

const EMPTY_LINE_FORM = { line_type: 'pilotage', description: '', amount: '', currency: '' }

const STATUS_KEYS: Record<DisbursementAccount['status'], string> = {
  pda_only: 'disbursementAccounts.statusPdaOnly',
  fda_pending: 'disbursementAccounts.statusFdaPending',
  reconciled: 'disbursementAccounts.statusReconciled',
  disputed: 'disbursementAccounts.statusDisputed',
}

const LINE_TYPE_KEYS: Record<string, string> = {
  pilotage: 'disbursementAccounts.lineTypePilotage',
  towage: 'disbursementAccounts.lineTypeTowage',
  mooring: 'disbursementAccounts.lineTypeMooring',
  agency_fee: 'disbursementAccounts.lineTypeAgencyFee',
  husbandry: 'disbursementAccounts.lineTypeHusbandry',
  customs: 'disbursementAccounts.lineTypeCustoms',
  security: 'disbursementAccounts.lineTypeSecurity',
  other: 'disbursementAccounts.lineTypeOther',
}

export default function DisbursementAccountsPage() {
  const { t } = useTranslation()
  const [das, setDas] = useState<DisbursementAccount[]>([])
  const [voyages, setVoyages] = useState<Voyage[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<DisbursementAccountCreate>(EMPTY_FORM)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [lineForms, setLineForms] = useState<Record<number, typeof EMPTY_LINE_FORM>>({})
  const [error, setError] = useState<string | null>(null)

  const refresh = () => listDisbursementAccounts().then(setDas)

  useEffect(() => {
    Promise.all([refresh(), listVoyages().then(setVoyages)]).finally(() => setLoading(false))
  }, [])

  const voyageNumber = (id: number) => voyages.find((v) => v.id === id)?.voyage_number ?? `#${id}`
  const lineFormFor = (daId: number) => lineForms[daId] ?? EMPTY_LINE_FORM

  const field =
    (key: keyof DisbursementAccountCreate, numeric = false) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: numeric ? Number(e.target.value) : e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await createDisbursementAccount(form)
      setForm(EMPTY_FORM)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record PDA')
    }
  }

  const handleAddLine = async (da: DisbursementAccount, e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const lineForm = lineFormFor(da.id)
    try {
      await addFdaLines(da.id, [
        {
          line_type: lineForm.line_type,
          description: lineForm.description,
          amount: Number(lineForm.amount) || 0,
          currency: lineForm.currency,
        },
      ])
      setLineForms((f) => ({ ...f, [da.id]: EMPTY_LINE_FORM }))
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add FDA line')
    }
  }

  const handleReconcile = async (da: DisbursementAccount) => {
    setError(null)
    try {
      await reconcileDisbursementAccount(da.id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reconcile')
    }
  }

  const handleDispute = async (da: DisbursementAccount) => {
    setError(null)
    try {
      await disputeDisbursementAccount(da.id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to mark disputed')
    }
  }

  return (
    <div>
      <h1>{t('disbursementAccounts.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t('disbursementAccounts.columnVoyage')}</th>
              <th>{t('disbursementAccounts.columnPort')}</th>
              <th>{t('disbursementAccounts.columnStatus')}</th>
              <th>{t('disbursementAccounts.columnPdaAmount')}</th>
              <th>{t('disbursementAccounts.columnFdaTotal')}</th>
              <th>{t('disbursementAccounts.columnVariance')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {das.map((da) => (
              <Fragment key={da.id}>
                <tr>
                  <td>{voyageNumber(da.voyage_id)}</td>
                  <td>{da.port}</td>
                  <td>{t(STATUS_KEYS[da.status])}</td>
                  <td>{da.pda_amount}</td>
                  <td>{da.fda_total}</td>
                  <td>{da.variance}</td>
                  <td>
                    <button type="button" onClick={() => setExpandedId(expandedId === da.id ? null : da.id)}>
                      {expandedId === da.id ? t('disbursementAccounts.hideLines') : t('disbursementAccounts.viewLines')}
                    </button>
                    {da.lines.length > 0 && da.status !== 'reconciled' && (
                      <button type="button" onClick={() => handleReconcile(da)}>
                        {t('disbursementAccounts.reconcileButton')}
                      </button>
                    )}
                    {da.status !== 'disputed' && (
                      <button type="button" onClick={() => handleDispute(da)}>
                        {t('disbursementAccounts.disputeButton')}
                      </button>
                    )}
                  </td>
                </tr>
                {expandedId === da.id && (
                  <tr>
                    <td colSpan={7}>
                      <table>
                        <thead>
                          <tr>
                            <th>{t('disbursementAccounts.lineColumnType')}</th>
                            <th>{t('disbursementAccounts.lineColumnDescription')}</th>
                            <th>{t('disbursementAccounts.lineColumnAmount')}</th>
                            <th>{t('disbursementAccounts.lineColumnCurrency')}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {da.lines.map((line) => (
                            <tr key={line.id}>
                              <td>{t(LINE_TYPE_KEYS[line.line_type] ?? line.line_type)}</td>
                              <td>{line.description}</td>
                              <td>{line.amount}</td>
                              <td>{line.currency}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
                <tr>
                  <td colSpan={7}>
                      <h3>{t('disbursementAccounts.addFdaLineHeading')}</h3>
                      <form onSubmit={(e) => handleAddLine(da, e)}>
                        <label>
                          {t('disbursementAccounts.lineType')}
                          <select
                            value={lineFormFor(da.id).line_type}
                            onChange={(e) =>
                              setLineForms((f) => ({ ...f, [da.id]: { ...lineFormFor(da.id), line_type: e.target.value } }))
                            }
                          >
                            {Object.entries(LINE_TYPE_KEYS).map(([value, key]) => (
                              <option key={value} value={value}>
                                {t(key)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          {t('disbursementAccounts.description')}
                          <input
                            value={lineFormFor(da.id).description}
                            onChange={(e) =>
                              setLineForms((f) => ({ ...f, [da.id]: { ...lineFormFor(da.id), description: e.target.value } }))
                            }
                            required
                          />
                        </label>
                        <label>
                          {t('disbursementAccounts.amount')}
                          <input
                            type="number"
                            step="0.01"
                            value={lineFormFor(da.id).amount}
                            onChange={(e) =>
                              setLineForms((f) => ({ ...f, [da.id]: { ...lineFormFor(da.id), amount: e.target.value } }))
                            }
                            required
                          />
                        </label>
                        <label>
                          {t('disbursementAccounts.currency')}
                          <input
                            value={lineFormFor(da.id).currency}
                            onChange={(e) =>
                              setLineForms((f) => ({ ...f, [da.id]: { ...lineFormFor(da.id), currency: e.target.value } }))
                            }
                            required
                          />
                        </label>
                        <button type="submit">{t('disbursementAccounts.addLineButton')}</button>
                      </form>
                  </td>
                </tr>
              </Fragment>
            ))}
          </tbody>
        </table>
      )}

      <h2>{t('disbursementAccounts.createHeading')}</h2>
      <form onSubmit={handleSubmit}>
        <label>
          {t('disbursementAccounts.voyage')}
          <select value={form.voyage_id || ''} onChange={field('voyage_id', true)} required>
            <option value="" disabled>
              {t('disbursementAccounts.selectVoyage')}
            </option>
            {voyages.map((v) => (
              <option key={v.id} value={v.id}>
                {v.voyage_number}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('disbursementAccounts.port')}
          <input value={form.port} onChange={field('port')} required />
        </label>
        <label>
          {t('disbursementAccounts.pdaAmount')}
          <input type="number" step="0.01" value={form.pda_amount || ''} onChange={field('pda_amount', true)} required />
        </label>
        <label>
          {t('disbursementAccounts.pdaCurrency')}
          <input value={form.pda_currency} onChange={field('pda_currency')} required />
        </label>
        <label>
          {t('disbursementAccounts.pdaDate')}
          <input value={form.pda_date} onChange={field('pda_date')} placeholder="YYYY-MM-DD" required />
        </label>
        <button type="submit">{t('disbursementAccounts.createButton')}</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
