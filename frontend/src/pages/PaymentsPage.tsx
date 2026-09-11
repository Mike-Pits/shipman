import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  createPayment,
  deletePayment,
  getPaymentWithDisplay,
  listPayments,
  updatePayment,
  updatePaymentStatus,
} from '../api/payments'
import { listVessels } from '../api/vessels'
import { listVoyages } from '../api/voyages'
import type {
  CostCategory,
  Currency,
  Payment,
  PaymentCreate,
  PaymentStatus,
  Vessel,
  Voyage,
} from '../api/types'

const EMPTY_FORM: PaymentCreate = {
  vessel_id: 0,
  voyage_id: null,
  vendor_name: '',
  cost_category: '' as CostCategory,
  cost_type_name: '',
  original_currency: '' as Currency,
  original_amount: 0,
  invoice_date: '',
  due_date: '',
  payment_date: '',
  document_number: '',
  notes: '',
}

const STATUS_KEYS: Record<PaymentStatus, string> = {
  draft: 'payments.statusDraft',
  pending: 'payments.statusPending',
  invoiced: 'payments.statusInvoiced',
  partial: 'payments.statusPartial',
  paid: 'payments.statusPaid',
  overdue: 'payments.statusOverdue',
}

const STATUS_OPTIONS: PaymentStatus[] = ['draft', 'pending', 'invoiced', 'partial', 'paid', 'overdue']
const OTHER_CURRENCY: Record<Currency, Currency> = { RUB: 'USD', USD: 'RUB' }

export default function PaymentsPage() {
  const { t } = useTranslation()
  const [payments, setPayments] = useState<Payment[]>([])
  const [vessels, setVessels] = useState<Vessel[]>([])
  const [voyages, setVoyages] = useState<Voyage[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<PaymentCreate>(EMPTY_FORM)
  const [error, setError] = useState<string | null>(null)
  const [displayAmounts, setDisplayAmounts] = useState<Record<number, { currency: Currency; amount: number }>>({})
  const [editingId, setEditingId] = useState<number | null>(null)

  const refresh = () => listPayments().then(setPayments)

  useEffect(() => {
    Promise.all([refresh(), listVessels().then(setVessels), listVoyages().then(setVoyages)]).finally(() =>
      setLoading(false),
    )
  }, [])

  const vesselName = (id: number) => vessels.find((v) => v.id === id)?.name ?? `#${id}`
  const voyageNumber = (id: number | null | undefined) =>
    id == null ? '' : (voyages.find((v) => v.id === id)?.voyage_number ?? `#${id}`)

  const field =
    (key: keyof PaymentCreate, numeric = false) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: numeric ? Number(e.target.value) : e.target.value }))

  const handleEdit = (payment: Payment) => {
    setError(null)
    setEditingId(payment.id)
    const { id, rub_equivalent, exchange_rate_used, exchange_rate_date, ...rest } = payment
    void id
    void rub_equivalent
    void exchange_rate_used
    void exchange_rate_date
    setForm(rest)
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setForm(EMPTY_FORM)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const payload: PaymentCreate = {
        ...form,
        voyage_id: form.voyage_id || null,
      }
      if (editingId !== null) {
        await updatePayment(editingId, payload)
      } else {
        await createPayment(payload)
      }
      handleCancelEdit()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record payment')
    }
  }

  const handleDelete = async (payment: Payment) => {
    if (!window.confirm(t('payments.deleteConfirm', { costType: payment.cost_type_name }))) return
    setError(null)
    try {
      await deletePayment(payment.id)
      if (editingId === payment.id) handleCancelEdit()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete payment')
    }
  }

  const handleStatusChange = async (payment: Payment, status: PaymentStatus) => {
    setError(null)
    try {
      await updatePaymentStatus(payment.id, status)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status')
    }
  }

  const handleToggleDisplay = async (payment: Payment) => {
    setError(null)
    const current = displayAmounts[payment.id]
    const targetCurrency = current ? OTHER_CURRENCY[current.currency] : OTHER_CURRENCY[payment.original_currency]
    try {
      const result = await getPaymentWithDisplay(payment.id, targetCurrency)
      setDisplayAmounts((d) => ({ ...d, [payment.id]: { currency: result.display_currency, amount: result.display_amount } }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to convert')
    }
  }

  return (
    <div>
      <h1>{t('payments.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{t('payments.columnVessel')}</th>
              <th>{t('payments.columnVoyage')}</th>
              <th>{t('payments.columnCostType')}</th>
              <th>{t('payments.columnCategory')}</th>
              <th>{t('payments.columnOriginal')}</th>
              <th>{t('payments.columnRubEquivalent')}</th>
              <th>{t('payments.columnStatus')}</th>
              <th>{t('payments.columnInvoiceDate')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id}>
                <td>{vesselName(p.vessel_id)}</td>
                <td>{voyageNumber(p.voyage_id)}</td>
                <td>{p.cost_type_name}</td>
                <td>{p.cost_category}</td>
                <td>
                  {p.original_amount} {p.original_currency}
                </td>
                <td>{p.rub_equivalent}</td>
                <td>
                  <select
                    aria-label={t('payments.statusLabel', { costType: p.cost_type_name })}
                    value={p.status}
                    onChange={(e) => handleStatusChange(p, e.target.value as PaymentStatus)}
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {t(STATUS_KEYS[s])}
                      </option>
                    ))}
                  </select>
                </td>
                <td>{p.invoice_date}</td>
                <td>
                  <button type="button" onClick={() => handleToggleDisplay(p)}>
                    {displayAmounts[p.id]?.currency === 'RUB' || (!displayAmounts[p.id] && p.original_currency === 'USD')
                      ? t('payments.showInRub')
                      : t('payments.showInUsd')}
                  </button>
                  {displayAmounts[p.id] && (
                    <span>
                      {' '}
                      {t('payments.displayAmount', {
                        amount: displayAmounts[p.id].amount,
                        currency: displayAmounts[p.id].currency,
                      })}
                    </span>
                  )}
                  <button type="button" onClick={() => handleEdit(p)}>
                    {t('common.edit')}
                  </button>
                  <button type="button" onClick={() => handleDelete(p)}>
                    {t('common.delete')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}

      <h2>{editingId !== null ? t('payments.editHeading') : t('payments.createHeading')}</h2>
      {editingId !== null && <p role="alert">{t('payments.editWarning')}</p>}
      <form onSubmit={handleSubmit}>
        <label>
          {t('payments.vessel')}
          <select value={form.vessel_id || ''} onChange={field('vessel_id', true)} required>
            <option value="" disabled>
              {t('payments.selectVessel')}
            </option>
            {vessels.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('payments.voyage')}
          <select value={form.voyage_id ?? ''} onChange={field('voyage_id', true)}>
            <option value="">{t('payments.selectVoyage')}</option>
            {voyages.map((v) => (
              <option key={v.id} value={v.id}>
                {v.voyage_number}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('payments.vendorName')}
          <input value={form.vendor_name ?? ''} onChange={field('vendor_name')} />
        </label>
        <label>
          {t('payments.costCategory')}
          <select value={form.cost_category} onChange={field('cost_category')} required>
            <option value="" disabled>
              {t('payments.selectCostCategory')}
            </option>
            <option value="income">{t('payments.categoryIncome')}</option>
            <option value="expense">{t('payments.categoryExpense')}</option>
          </select>
        </label>
        <label>
          {t('payments.costType')}
          <input value={form.cost_type_name} onChange={field('cost_type_name')} required />
        </label>
        <label>
          {t('payments.originalCurrency')}
          <select value={form.original_currency} onChange={field('original_currency')} required>
            <option value="" disabled>
              {t('payments.selectCostCategory')}
            </option>
            <option value="RUB">RUB</option>
            <option value="USD">USD</option>
          </select>
        </label>
        <label>
          {t('payments.originalAmount')}
          <input
            type="number"
            step="0.01"
            value={form.original_amount || ''}
            onChange={field('original_amount', true)}
            required
          />
        </label>
        <label>
          {t('payments.invoiceDate')}
          <input value={form.invoice_date} onChange={field('invoice_date')} placeholder="YYYY-MM-DD" required />
        </label>
        <label>
          {t('payments.dueDate')}
          <input value={form.due_date ?? ''} onChange={field('due_date')} placeholder="YYYY-MM-DD" />
        </label>
        <label>
          {t('payments.paymentDate')}
          <input value={form.payment_date ?? ''} onChange={field('payment_date')} placeholder="YYYY-MM-DD" />
        </label>
        <label>
          {t('payments.documentNumber')}
          <input value={form.document_number ?? ''} onChange={field('document_number')} />
        </label>
        <label>
          {t('payments.notes')}
          <input value={form.notes ?? ''} onChange={field('notes')} />
        </label>
        <button type="submit">{editingId !== null ? t('payments.updateButton') : t('payments.createButton')}</button>
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
