import { Fragment, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  createInvoice,
  deleteInvoice,
  issueInvoice,
  listInvoices,
  updateInvoice,
  voidInvoice,
} from '../api/invoices'
import { listClaims } from '../api/claims'
import { listFixtures } from '../api/fixtures'
import { listVessels } from '../api/vessels'
import { listVoyages } from '../api/voyages'
import Badge, { type BadgeTone } from '../components/ui/Badge'
import type {
  Claim,
  Currency,
  Fixture,
  Invoice,
  InvoiceCreate,
  InvoiceStatus,
  InvoiceType,
  Vessel,
  VatTreatment,
  Voyage,
} from '../api/types'

const EMPTY_FORM: InvoiceCreate = {
  invoice_type: 'hire',
  date_of_issue: '',
  due_date: '',
  currency: '' as Currency,
  vat_applicable: false,
  counterparty: '',
  subject: '',
  fixture_id: null,
  voyage_id: null,
  vessel_id: null,
  claim_id: null,
  hire_period_start: '',
  hire_period_end: '',
}

type LineRow = { description: string; quantity: string; unit: string; unitPrice: string }
const EMPTY_LINE_ROW: LineRow = { description: '', quantity: '', unit: '', unitPrice: '' }

const TYPE_LABEL_KEYS: Record<InvoiceType, string> = {
  hire: 'invoicing.typeHire',
  freight: 'invoicing.typeFreight',
  demurrage: 'invoicing.typeDemurrage',
  free_form: 'invoicing.typeFreeForm',
}

const STATUS_LABEL_KEYS: Record<InvoiceStatus, string> = {
  draft: 'invoicing.statusDraft',
  issued: 'invoicing.statusIssued',
  void: 'invoicing.statusVoid',
}

const STATUS_TONES: Record<InvoiceStatus, BadgeTone> = {
  draft: 'neutral',
  issued: 'success',
  void: 'danger',
}

export default function InvoicingPage() {
  const { t } = useTranslation()
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [fixtures, setFixtures] = useState<Fixture[]>([])
  const [voyages, setVoyages] = useState<Voyage[]>([])
  const [vessels, setVessels] = useState<Vessel[]>([])
  const [claims, setClaims] = useState<Claim[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<InvoiceCreate>(EMPTY_FORM)
  const [lines, setLines] = useState<LineRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const refresh = () => listInvoices().then(setInvoices)

  useEffect(() => {
    Promise.all([
      refresh(),
      listFixtures().then(setFixtures),
      listVoyages().then(setVoyages),
      listVessels().then(setVessels),
      listClaims().then(setClaims),
    ]).finally(() => setLoading(false))
  }, [])

  const fixtureById = (id: number | null) => fixtures.find((f) => f.id === id)

  const tcOutFixtures = fixtures.filter((f) => f.fixture_type === 'time_charter_out')
  const freightEligibleVoyages = voyages.filter((v) => {
    const fixture = fixtureById(v.fixture_id)
    return fixture && (fixture.fixture_type === 'voyage_charter' || fixture.fixture_type === 'coa')
  })
  const demurrageClaims = claims.filter(
    (c) => c.claim_type === 'demurrage_dispute' && (form.voyage_id == null || c.voyage_id === form.voyage_id),
  )

  const field =
    (key: keyof InvoiceCreate, numeric = false) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: numeric ? Number(e.target.value) : e.target.value }))

  const lineField = (index: number, key: keyof LineRow) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setLines((rows) => rows.map((row, i) => (i === index ? { ...row, [key]: e.target.value } : row)))

  const addLine = () => setLines((rows) => [...rows, EMPTY_LINE_ROW])
  const removeLine = (index: number) => setLines((rows) => rows.filter((_, i) => i !== index))

  const usesManualLines = form.invoice_type === 'demurrage' || form.invoice_type === 'free_form'

  const handleTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const invoice_type = e.target.value as InvoiceType
    setForm({ ...EMPTY_FORM, invoice_type })
    setLines([])
  }

  const handleEdit = (invoice: Invoice) => {
    setError(null)
    setEditingId(invoice.id)
    setForm({
      invoice_type: invoice.invoice_type,
      date_of_issue: invoice.date_of_issue,
      due_date: invoice.due_date ?? '',
      currency: invoice.currency,
      vat_applicable: invoice.vat_applicable,
      vat_treatment: invoice.vat_treatment as VatTreatment | undefined,
      vat_rate_percent: invoice.vat_rate_percent,
      counterparty: invoice.counterparty,
      subject: invoice.subject ?? '',
      fixture_id: invoice.fixture_id,
      voyage_id: invoice.voyage_id,
      vessel_id: invoice.vessel_id,
      claim_id: invoice.claim_id,
      hire_period_start: invoice.hire_period_start ?? '',
      hire_period_end: invoice.hire_period_end ?? '',
    })
    setLines(
      invoice.invoice_type === 'demurrage' || invoice.invoice_type === 'free_form'
        ? invoice.lines.map((l) => ({
            description: l.description,
            quantity: String(l.quantity),
            unit: l.unit,
            unitPrice: String(l.unit_price),
          }))
        : [],
    )
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setForm(EMPTY_FORM)
    setLines([])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const payload: InvoiceCreate = {
        ...form,
        lines: usesManualLines
          ? lines.map((l) => ({
              description: l.description,
              quantity: Number(l.quantity) || 0,
              unit: l.unit,
              unit_price: Number(l.unitPrice) || 0,
            }))
          : [],
      }
      if (editingId !== null) {
        await updateInvoice(editingId, payload)
      } else {
        await createInvoice(payload)
      }
      handleCancelEdit()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save invoice')
    }
  }

  const handleIssue = async (invoice: Invoice) => {
    setError(null)
    try {
      await issueInvoice(invoice.id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to issue invoice')
    }
  }

  const handleVoid = async (invoice: Invoice) => {
    if (!window.confirm(t('invoicing.voidConfirm', { number: invoice.invoice_number ?? '' }))) return
    setError(null)
    try {
      await voidInvoice(invoice.id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to void invoice')
    }
  }

  const handleDelete = async (invoice: Invoice) => {
    if (!window.confirm(t('invoicing.deleteConfirm'))) return
    setError(null)
    try {
      await deleteInvoice(invoice.id)
      if (editingId === invoice.id) handleCancelEdit()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete invoice')
    }
  }

  const type = form.invoice_type

  return (
    <div>
      <h1>{t('invoicing.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('invoicing.columnNumber')}</th>
                <th>{t('invoicing.columnType')}</th>
                <th>{t('invoicing.columnStatus')}</th>
                <th>{t('invoicing.columnCounterparty')}</th>
                <th>{t('invoicing.columnTotal')}</th>
                <th>{t('invoicing.columnDateOfIssue')}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <Fragment key={inv.id}>
                  <tr>
                    <td>{inv.invoice_number ?? '—'}</td>
                    <td>{t(TYPE_LABEL_KEYS[inv.invoice_type])}</td>
                    <td>
                      <Badge tone={STATUS_TONES[inv.status]}>{t(STATUS_LABEL_KEYS[inv.status])}</Badge>
                    </td>
                    <td>{inv.counterparty}</td>
                    <td>
                      {inv.total_amount_due} {inv.currency}
                    </td>
                    <td>{inv.date_of_issue}</td>
                    <td>
                      <button type="button" onClick={() => setExpandedId(expandedId === inv.id ? null : inv.id)}>
                        {expandedId === inv.id ? t('invoicing.hideLines') : t('invoicing.viewLines')}
                      </button>
                      {inv.status === 'draft' && (
                        <>
                          <button type="button" onClick={() => handleEdit(inv)}>
                            {t('common.edit')}
                          </button>
                          <button type="button" onClick={() => handleDelete(inv)}>
                            {t('common.delete')}
                          </button>
                          <button type="button" onClick={() => handleIssue(inv)}>
                            {t('invoicing.issueButton')}
                          </button>
                        </>
                      )}
                      {inv.status === 'issued' && (
                        <button type="button" onClick={() => handleVoid(inv)}>
                          {t('invoicing.voidButton')}
                        </button>
                      )}
                    </td>
                  </tr>
                  {expandedId === inv.id && (
                    <tr>
                      <td colSpan={7}>
                        <table>
                          <thead>
                            <tr>
                              <th>{t('invoicing.lineColumnDescription')}</th>
                              <th>{t('invoicing.lineColumnQuantity')}</th>
                              <th>{t('invoicing.lineColumnUnit')}</th>
                              <th>{t('invoicing.lineColumnUnitPrice')}</th>
                              <th>{t('invoicing.lineColumnAmount')}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {inv.lines.map((line) => (
                              <tr key={line.id}>
                                <td>{line.description}</td>
                                <td>{line.quantity}</td>
                                <td>{line.unit}</td>
                                <td>{line.unit_price}</td>
                                <td>{line.amount}</td>
                              </tr>
                            ))}
                            {inv.vat_applicable && (
                              <tr>
                                <td colSpan={4}>{t('invoicing.vatAmount')}</td>
                                <td>{inv.vat_amount}</td>
                              </tr>
                            )}
                            <tr>
                              <td colSpan={4}>
                                <strong>{t('invoicing.totalAmountDue')}</strong>
                              </td>
                              <td>
                                <strong>
                                  {inv.total_amount_due} {inv.currency}
                                </strong>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2>{editingId !== null ? t('invoicing.editHeading') : t('invoicing.createHeading')}</h2>
      {editingId !== null && <p role="alert">{t('invoicing.editWarning')}</p>}
      <form onSubmit={handleSubmit}>
        <label>
          {t('invoicing.invoiceType')}
          <select value={form.invoice_type} onChange={handleTypeChange} disabled={editingId !== null}>
            <option value="hire">{t('invoicing.typeHire')}</option>
            <option value="freight">{t('invoicing.typeFreight')}</option>
            <option value="demurrage">{t('invoicing.typeDemurrage')}</option>
            <option value="free_form">{t('invoicing.typeFreeForm')}</option>
          </select>
        </label>
        <label>
          {t('invoicing.dateOfIssue')}
          <input value={form.date_of_issue} onChange={field('date_of_issue')} placeholder="YYYY-MM-DD" required />
        </label>
        <label>
          {t('invoicing.dueDate')}
          <input value={form.due_date ?? ''} onChange={field('due_date')} placeholder="YYYY-MM-DD" />
        </label>

        {type === 'hire' && (
          <>
            <label>
              {t('invoicing.fixture')}
              <select value={form.fixture_id ?? ''} onChange={field('fixture_id', true)} required>
                <option value="" disabled>
                  {t('invoicing.selectFixture')}
                </option>
                {tcOutFixtures.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.charterer} ({f.charter_party_ref ?? `#${f.id}`})
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('invoicing.vessel')}
              <select value={form.vessel_id ?? ''} onChange={field('vessel_id', true)} required>
                <option value="" disabled>
                  {t('invoicing.selectVessel')}
                </option>
                {vessels.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('invoicing.hirePeriodStart')}
              <input
                value={form.hire_period_start ?? ''}
                onChange={field('hire_period_start')}
                placeholder="YYYY-MM-DD HH:MM"
                required
              />
            </label>
            <label>
              {t('invoicing.hirePeriodEnd')}
              <input
                value={form.hire_period_end ?? ''}
                onChange={field('hire_period_end')}
                placeholder="YYYY-MM-DD HH:MM"
                required
              />
            </label>
          </>
        )}

        {(type === 'freight' || type === 'demurrage') && (
          <label>
            {t('invoicing.voyage')}
            <select value={form.voyage_id ?? ''} onChange={field('voyage_id', true)} required>
              <option value="" disabled>
                {t('invoicing.selectVoyage')}
              </option>
              {(type === 'freight' ? freightEligibleVoyages : voyages).map((v) => (
                <option key={v.id} value={v.id}>
                  {v.voyage_number}
                </option>
              ))}
            </select>
          </label>
        )}

        {type === 'demurrage' && (
          <label>
            {t('invoicing.claim')}
            <select value={form.claim_id ?? ''} onChange={field('claim_id', true)}>
              <option value="">{t('invoicing.noClaim')}</option>
              {demurrageClaims.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.counterparty} — {c.amount_claimed} {c.currency}
                </option>
              ))}
            </select>
          </label>
        )}

        {type === 'free_form' && (
          <>
            <label>
              {t('invoicing.vessel')}
              <select value={form.vessel_id ?? ''} onChange={field('vessel_id', true)} required>
                <option value="" disabled>
                  {t('invoicing.selectVessel')}
                </option>
                {vessels.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('invoicing.voyage')}
              <select value={form.voyage_id ?? ''} onChange={field('voyage_id', true)}>
                <option value="">{t('invoicing.selectVoyage')}</option>
                {voyages.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.voyage_number}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('invoicing.subject')}
              <input value={form.subject ?? ''} onChange={field('subject')} required />
            </label>
            <label>
              {t('invoicing.counterparty')}
              <input value={form.counterparty ?? ''} onChange={field('counterparty')} required />
            </label>
            <label>
              {t('invoicing.currency')}
              <select value={form.currency ?? ''} onChange={field('currency')} required>
                <option value="" disabled>
                  {t('invoicing.selectCurrency')}
                </option>
                <option value="RUB">RUB</option>
                <option value="USD">USD</option>
              </select>
            </label>
            <label>
              {t('invoicing.vatApplicable')}
              <input
                type="checkbox"
                checked={form.vat_applicable ?? false}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    vat_applicable: e.target.checked,
                    vat_treatment: e.target.checked ? f.vat_treatment : undefined,
                    vat_rate_percent: e.target.checked ? f.vat_rate_percent : undefined,
                  }))
                }
              />
            </label>
            {form.vat_applicable && (
              <>
                <label>
                  {t('invoicing.vatTreatment')}
                  <select value={form.vat_treatment ?? ''} onChange={field('vat_treatment')} required>
                    <option value="" disabled>
                      {t('invoicing.selectVatTreatment')}
                    </option>
                    <option value="inclusive">{t('invoicing.vatInclusive')}</option>
                    <option value="exclusive">{t('invoicing.vatExclusive')}</option>
                  </select>
                </label>
                <label>
                  {t('invoicing.vatRatePercent')}
                  <input
                    type="number"
                    step="0.01"
                    value={form.vat_rate_percent ?? ''}
                    onChange={field('vat_rate_percent', true)}
                    required
                  />
                </label>
              </>
            )}
          </>
        )}

        {usesManualLines && (
          <>
            <h3>{t('invoicing.linesHeading')}</h3>
            {lines.map((row, i) => (
              <div key={i}>
                <label>
                  {t('invoicing.lineDescription')}
                  <input value={row.description} onChange={lineField(i, 'description')} required />
                </label>
                <label>
                  {t('invoicing.lineQuantity')}
                  <input type="number" step="0.01" value={row.quantity} onChange={lineField(i, 'quantity')} required />
                </label>
                <label>
                  {t('invoicing.lineUnit')}
                  <input value={row.unit} onChange={lineField(i, 'unit')} required />
                </label>
                <label>
                  {t('invoicing.lineUnitPrice')}
                  <input
                    type="number"
                    step="0.01"
                    value={row.unitPrice}
                    onChange={lineField(i, 'unitPrice')}
                    required
                  />
                </label>
                <button type="button" onClick={() => removeLine(i)}>
                  {t('invoicing.removeLineButton')}
                </button>
              </div>
            ))}
            <button type="button" onClick={addLine}>
              {t('invoicing.addLineButton')}
            </button>
          </>
        )}

        <button type="submit">{editingId !== null ? t('invoicing.updateButton') : t('invoicing.createButton')}</button>
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
