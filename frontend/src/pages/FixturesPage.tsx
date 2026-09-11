import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createFixture, listFixtures, updateFixture } from '../api/fixtures'
import type { Currency, Fixture, FixtureCreate, FixtureType } from '../api/types'

const EMPTY_FORM: FixtureCreate = {
  fixture_type: 'voyage_charter',
  charterer: '',
  contract_currency: '' as Currency,
  vat_applicable: false,
  brokers: [],
}

type BrokerRow = { name: string; commission: string }
const EMPTY_BROKERS: BrokerRow[] = [
  { name: '', commission: '' },
  { name: '', commission: '' },
  { name: '', commission: '' },
]

const FIXTURE_TYPE_LABEL_KEYS: Record<FixtureType, string> = {
  voyage_charter: 'fixtures.typeVoyageCharter',
  time_charter_out: 'fixtures.typeTimeCharterOut',
  coa: 'fixtures.typeCoa',
}

export default function FixturesPage() {
  const { t } = useTranslation()
  const [fixtures, setFixtures] = useState<Fixture[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<FixtureCreate>(EMPTY_FORM)
  const [brokers, setBrokers] = useState<BrokerRow[]>(EMPTY_BROKERS)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)

  const refresh = () => listFixtures().then(setFixtures)

  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [])

  const vatSummary = (f: Fixture) => {
    if (!f.vat_applicable) return t('fixtures.vatNotApplicable')
    const treatmentKey = f.vat_treatment === 'inclusive' ? 'fixtures.vatInclusiveShort' : 'fixtures.vatExclusiveShort'
    return `${f.vat_rate_percent}% ${t(treatmentKey)}`
  }

  const field =
    (key: keyof FixtureCreate, numeric = false) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: numeric ? Number(e.target.value) : e.target.value }))

  const brokerField = (index: number, key: 'name' | 'commission') => (e: React.ChangeEvent<HTMLInputElement>) =>
    setBrokers((rows) => rows.map((row, i) => (i === index ? { ...row, [key]: e.target.value } : row)))

  const handleEdit = (fixture: Fixture) => {
    setError(null)
    setEditingId(fixture.id)
    const { brokers: existingBrokers, ...rest } = fixture
    setForm(rest)
    setBrokers(
      Array.from({ length: 3 }, (_, i) => ({
        name: existingBrokers[i]?.broker_name ?? '',
        commission: existingBrokers[i] ? String(existingBrokers[i].commission_percentage) : '',
      })),
    )
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setForm(EMPTY_FORM)
    setBrokers(EMPTY_BROKERS)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const payload: FixtureCreate = {
        ...form,
        brokers: brokers
          .filter((row) => row.name.trim() !== '')
          .map((row) => ({ broker_name: row.name, commission_percentage: Number(row.commission) || 0 })),
      }
      if (editingId !== null) {
        await updateFixture(editingId, payload)
      } else {
        await createFixture(payload)
      }
      handleCancelEdit()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save fixture')
    }
  }

  const type = form.fixture_type

  return (
    <div>
      <h1>{t('fixtures.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('fixtures.columnType')}</th>
                <th>{t('fixtures.columnCharterer')}</th>
                <th>{t('fixtures.columnCurrency')}</th>
                <th>{t('fixtures.columnKeyRate')}</th>
                <th>{t('fixtures.columnVat')}</th>
                <th>{t('fixtures.columnDateConcluded')}</th>
                <th>{t('fixtures.columnCpRef')}</th>
                <th>{t('fixtures.columnCpType')}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {fixtures.map((f) => (
                <tr key={f.id}>
                  <td>{t(FIXTURE_TYPE_LABEL_KEYS[f.fixture_type])}</td>
                  <td>{f.charterer}</td>
                  <td>{f.contract_currency}</td>
                  <td>{f.freight_rate ?? f.hire_rate ?? f.rate_per_tonne ?? '—'}</td>
                  <td>{vatSummary(f)}</td>
                  <td>{f.date_concluded ?? '—'}</td>
                  <td>{f.charter_party_ref ?? '—'}</td>
                  <td>{f.charter_party_type ?? '—'}</td>
                  <td>
                    <button type="button" onClick={() => handleEdit(f)}>
                      {t('common.edit')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2>{editingId !== null ? t('fixtures.editFixture') : t('fixtures.createFixture')}</h2>
      {editingId !== null && <p role="alert">{t('fixtures.editWarning')}</p>}
      <form onSubmit={handleSubmit}>
        <label>
          {t('fixtures.fixtureType')}
          <select value={form.fixture_type} onChange={field('fixture_type')}>
            <option value="voyage_charter">{t('fixtures.typeVoyageCharter')}</option>
            <option value="time_charter_out">{t('fixtures.typeTimeCharterOut')}</option>
            <option value="coa">{t('fixtures.typeCoa')}</option>
          </select>
        </label>
        <label>
          {t('fixtures.charterer')}
          <input value={form.charterer} onChange={field('charterer')} required />
        </label>
        <label>
          {t('fixtures.contractCurrency')}
          <select value={form.contract_currency} onChange={field('contract_currency')} required>
            <option value="" disabled>
              {t('fixtures.selectCurrency')}
            </option>
            <option value="RUB">RUB</option>
            <option value="USD">USD</option>
          </select>
        </label>
        <label>
          {t('fixtures.vatApplicable')}
          <input
            type="checkbox"
            checked={form.vat_applicable}
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
              {t('fixtures.vatTreatment')}
              <select value={form.vat_treatment ?? ''} onChange={field('vat_treatment')} required>
                <option value="" disabled>
                  {t('fixtures.selectVatTreatment')}
                </option>
                <option value="inclusive">{t('fixtures.vatInclusive')}</option>
                <option value="exclusive">{t('fixtures.vatExclusive')}</option>
              </select>
            </label>
            <label>
              {t('fixtures.vatRatePercent')}
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
        <label>
          {t('fixtures.dateConcluded')}
          <input value={form.date_concluded ?? ''} onChange={field('date_concluded')} placeholder="YYYY-MM-DD" />
        </label>
        <label>
          {t('fixtures.charterPartyRef')}
          <input value={form.charter_party_ref ?? ''} onChange={field('charter_party_ref')} maxLength={15} />
        </label>
        <label>
          {t('fixtures.charterPartyType')}
          <input value={form.charter_party_type ?? ''} onChange={field('charter_party_type')} />
        </label>

        {type === 'voyage_charter' && (
          <>
            <label>
              {t('fixtures.freightRate')}
              <input type="number" value={form.freight_rate ?? ''} onChange={field('freight_rate', true)} />
            </label>
            <label>
              {t('fixtures.freightRateBasis')}
              <select value={form.freight_rate_basis ?? ''} onChange={field('freight_rate_basis')}>
                <option value="">—</option>
                <option value="per_tonne">{t('fixtures.perTonne')}</option>
                <option value="lump_sum">{t('fixtures.lumpSum')}</option>
              </select>
            </label>
            <label>
              {t('fixtures.laycanStart')}
              <input value={form.laycan_start ?? ''} onChange={field('laycan_start')} />
            </label>
            <label>
              {t('fixtures.laycanEnd')}
              <input value={form.laycan_end ?? ''} onChange={field('laycan_end')} />
            </label>
            <label>
              {t('fixtures.loadPort')}
              <input value={form.load_port ?? ''} onChange={field('load_port')} />
            </label>
            <label>
              {t('fixtures.dischargePort')}
              <input value={form.discharge_port ?? ''} onChange={field('discharge_port')} />
            </label>
            <label>
              {t('fixtures.cargoGrade')}
              <input value={form.cargo_grade ?? ''} onChange={field('cargo_grade')} />
            </label>
            <label>
              {t('fixtures.demurrageRate')}
              <input type="number" value={form.demurrage_rate ?? ''} onChange={field('demurrage_rate', true)} />
            </label>
            <label>
              {t('fixtures.despatchRate')}
              <input type="number" value={form.despatch_rate ?? ''} onChange={field('despatch_rate', true)} />
            </label>
            <label>
              {t('fixtures.laytimeTerms')}
              <input value={form.laytime_terms ?? ''} onChange={field('laytime_terms')} />
            </label>
          </>
        )}

        {type === 'time_charter_out' && (
          <>
            <label>
              {t('fixtures.hireRate')}
              <input type="number" value={form.hire_rate ?? ''} onChange={field('hire_rate', true)} />
            </label>
            <label>
              {t('fixtures.hireRateBasis')}
              <select value={form.hire_rate_basis ?? ''} onChange={field('hire_rate_basis')}>
                <option value="">—</option>
                <option value="daily">{t('fixtures.daily')}</option>
                <option value="monthly">{t('fixtures.monthly')}</option>
              </select>
            </label>
            <label>
              {t('fixtures.charterPeriodFrom')}
              <input
                value={form.charter_period_from ?? ''}
                onChange={field('charter_period_from')}
                placeholder="YYYY-MM-DD HH:MM"
              />
            </label>
            <label>
              {t('fixtures.charterPeriodTo')}
              <input
                value={form.charter_period_to ?? ''}
                onChange={field('charter_period_to')}
                placeholder="YYYY-MM-DD HH:MM"
              />
            </label>
            <label>
              {t('fixtures.deliveryPort')}
              <input value={form.delivery_port ?? ''} onChange={field('delivery_port')} />
            </label>
            <h3>{t('fixtures.deliveryRobHeading')}</h3>
            <label>
              {t('fixtures.robGradeIfo')}
              <input
                type="number"
                step="0.01"
                value={form.delivery_rob_ifo_mt ?? ''}
                onChange={field('delivery_rob_ifo_mt', true)}
              />
            </label>
            <label>
              {t('fixtures.robGradeMgo')}
              <input
                type="number"
                step="0.01"
                value={form.delivery_rob_mgo_mt ?? ''}
                onChange={field('delivery_rob_mgo_mt', true)}
              />
            </label>
            <label>
              {t('fixtures.redeliveryPort')}
              <input value={form.redelivery_port ?? ''} onChange={field('redelivery_port')} />
            </label>
            <h3>{t('fixtures.redeliveryRobHeading')}</h3>
            <label>
              {t('fixtures.robGradeIfo')}
              <input
                type="number"
                step="0.01"
                value={form.redelivery_rob_ifo_mt ?? ''}
                onChange={field('redelivery_rob_ifo_mt', true)}
              />
            </label>
            <label>
              {t('fixtures.robGradeMgo')}
              <input
                type="number"
                step="0.01"
                value={form.redelivery_rob_mgo_mt ?? ''}
                onChange={field('redelivery_rob_mgo_mt', true)}
              />
            </label>
            <label>
              {t('fixtures.redeliveryConditions')}
              <input value={form.redelivery_conditions ?? ''} onChange={field('redelivery_conditions')} />
            </label>
            <label>
              {t('fixtures.hirePaymentBasis')}
              <select value={form.hire_payment_basis ?? ''} onChange={field('hire_payment_basis')}>
                <option value="">—</option>
                <option value="advance">{t('fixtures.basisAdvance')}</option>
                <option value="arrears">{t('fixtures.basisArrears')}</option>
                <option value="days_after_invoice">{t('fixtures.basisDaysAfterInvoice')}</option>
              </select>
            </label>
            <label>
              {t('fixtures.hirePaymentFrequency')}
              <input
                type="number"
                value={form.hire_payment_frequency_days ?? ''}
                onChange={field('hire_payment_frequency_days', true)}
              />
            </label>
            {form.hire_payment_basis === 'days_after_invoice' && (
              <label>
                {t('fixtures.hirePaymentDaysAfterInvoice')}
                <input
                  type="number"
                  value={form.hire_payment_days_after_invoice ?? ''}
                  onChange={field('hire_payment_days_after_invoice', true)}
                />
              </label>
            )}
          </>
        )}

        {type === 'coa' && (
          <>
            <label>
              {t('fixtures.contractPeriodFrom')}
              <input value={form.contract_period_from ?? ''} onChange={field('contract_period_from')} />
            </label>
            <label>
              {t('fixtures.contractPeriodTo')}
              <input value={form.contract_period_to ?? ''} onChange={field('contract_period_to')} />
            </label>
            <label>
              {t('fixtures.totalContractedQuantity')}
              <input
                type="number"
                value={form.total_contracted_quantity ?? ''}
                onChange={field('total_contracted_quantity', true)}
              />
            </label>
            <label>
              {t('fixtures.numberOfLifts')}
              <input type="number" value={form.number_of_lifts ?? ''} onChange={field('number_of_lifts', true)} />
            </label>
            <label>
              {t('fixtures.ratePerTonne')}
              <input type="number" value={form.rate_per_tonne ?? ''} onChange={field('rate_per_tonne', true)} />
            </label>
            <label>
              {t('fixtures.minCargoQuantityPerLift')}
              <input
                type="number"
                value={form.min_cargo_quantity_per_lift ?? ''}
                onChange={field('min_cargo_quantity_per_lift', true)}
              />
            </label>
            <label>
              {t('fixtures.maxCargoQuantityPerLift')}
              <input
                type="number"
                value={form.max_cargo_quantity_per_lift ?? ''}
                onChange={field('max_cargo_quantity_per_lift', true)}
              />
            </label>
          </>
        )}

        <h3>{t('fixtures.brokersHeading')}</h3>
        {brokers.map((row, i) => (
          <div key={i}>
            <label>
              {t('fixtures.brokerName', { n: i + 1 })}
              <input value={row.name} onChange={brokerField(i, 'name')} />
            </label>
            <label>
              {t('fixtures.brokerCommission', { n: i + 1 })}
              <input type="number" step="0.01" value={row.commission} onChange={brokerField(i, 'commission')} />
            </label>
          </div>
        ))}

        <button type="submit">{editingId !== null ? t('fixtures.updateFixture') : t('fixtures.createFixture')}</button>
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
