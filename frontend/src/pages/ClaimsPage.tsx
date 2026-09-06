import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createClaim, listClaims, settleClaim, updateClaimStatus } from '../api/claims'
import { listVoyages } from '../api/voyages'
import type { Claim, ClaimCreate, ClaimStatus, ClaimType, Voyage } from '../api/types'

const EMPTY_FORM: ClaimCreate = {
  voyage_id: null,
  fixture_id: null,
  disbursement_account_id: null,
  claim_type: '' as ClaimType,
  counterparty: '',
  amount_claimed: 0,
  currency: '',
  date_raised: '',
  notes: '',
}

const STATUS_KEYS: Record<ClaimStatus, string> = {
  open: 'claims.statusOpen',
  negotiating: 'claims.statusNegotiating',
  settled: 'claims.statusSettled',
  rejected: 'claims.statusRejected',
}

const TYPE_KEYS: Record<ClaimType, string> = {
  cargo_quantity: 'claims.typeCargoQuantity',
  cargo_quality: 'claims.typeCargoQuality',
  demurrage_dispute: 'claims.typeDemurrageDispute',
  off_hire_dispute: 'claims.typeOffHireDispute',
  other: 'claims.typeOther',
}

export default function ClaimsPage() {
  const { t } = useTranslation()
  const [claims, setClaims] = useState<Claim[]>([])
  const [voyages, setVoyages] = useState<Voyage[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<ClaimCreate>(EMPTY_FORM)
  const [settlementAmounts, setSettlementAmounts] = useState<Record<number, string>>({})
  const [error, setError] = useState<string | null>(null)

  const refresh = () => listClaims().then(setClaims)

  useEffect(() => {
    Promise.all([refresh(), listVoyages().then(setVoyages)]).finally(() => setLoading(false))
  }, [])

  const voyageNumber = (id: number | null) => (id == null ? '' : (voyages.find((v) => v.id === id)?.voyage_number ?? `#${id}`))

  const field =
    (key: keyof ClaimCreate, numeric = false) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: numeric ? Number(e.target.value) : e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await createClaim({ ...form, voyage_id: form.voyage_id || null })
      setForm(EMPTY_FORM)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record claim')
    }
  }

  const handleStatusChange = async (claim: Claim, status: 'negotiating' | 'rejected') => {
    setError(null)
    try {
      await updateClaimStatus(claim.id, status)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status')
    }
  }

  const handleSettle = async (claim: Claim, e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await settleClaim(claim.id, Number(settlementAmounts[claim.id] ?? 0))
      setSettlementAmounts((s) => ({ ...s, [claim.id]: '' }))
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to settle claim')
    }
  }

  const canProgress = (status: ClaimStatus) => status === 'open' || status === 'negotiating'

  return (
    <div>
      <h1>{t('claims.title')}</h1>

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t('claims.columnVoyage')}</th>
              <th>{t('claims.columnType')}</th>
              <th>{t('claims.columnCounterparty')}</th>
              <th>{t('claims.columnAmountClaimed')}</th>
              <th>{t('claims.columnAmountSettled')}</th>
              <th>{t('claims.columnStatus')}</th>
              <th>{t('claims.columnDateRaised')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {claims.map((c) => (
              <tr key={c.id}>
                <td>{voyageNumber(c.voyage_id)}</td>
                <td>{t(TYPE_KEYS[c.claim_type])}</td>
                <td>{c.counterparty}</td>
                <td>
                  {c.amount_claimed} {c.currency}
                </td>
                <td>{c.amount_settled ?? ''}</td>
                <td>{t(STATUS_KEYS[c.status])}</td>
                <td>{c.date_raised}</td>
                <td>
                  {canProgress(c.status) && (
                    <>
                      {c.status === 'open' && (
                        <button type="button" onClick={() => handleStatusChange(c, 'negotiating')}>
                          {t('claims.negotiateButton')}
                        </button>
                      )}
                      <button type="button" onClick={() => handleStatusChange(c, 'rejected')}>
                        {t('claims.rejectButton')}
                      </button>
                      <form onSubmit={(e) => handleSettle(c, e)}>
                        <label>
                          {t('claims.settlementAmount')}
                          <input
                            type="number"
                            step="0.01"
                            value={settlementAmounts[c.id] ?? ''}
                            onChange={(e) => setSettlementAmounts((s) => ({ ...s, [c.id]: e.target.value }))}
                            required
                          />
                        </label>
                        <button type="submit">{t('claims.settleButton')}</button>
                      </form>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>{t('claims.createHeading')}</h2>
      <form onSubmit={handleSubmit}>
        <label>
          {t('claims.voyage')}
          <select value={form.voyage_id ?? ''} onChange={field('voyage_id', true)}>
            <option value="">{t('claims.selectVoyage')}</option>
            {voyages.map((v) => (
              <option key={v.id} value={v.id}>
                {v.voyage_number}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('claims.claimType')}
          <select value={form.claim_type} onChange={field('claim_type')} required>
            <option value="" disabled>
              {t('claims.selectClaimType')}
            </option>
            <option value="cargo_quantity">{t('claims.typeCargoQuantity')}</option>
            <option value="cargo_quality">{t('claims.typeCargoQuality')}</option>
            <option value="demurrage_dispute">{t('claims.typeDemurrageDispute')}</option>
            <option value="off_hire_dispute">{t('claims.typeOffHireDispute')}</option>
            <option value="other">{t('claims.typeOther')}</option>
          </select>
        </label>
        <label>
          {t('claims.counterparty')}
          <input value={form.counterparty} onChange={field('counterparty')} required />
        </label>
        <label>
          {t('claims.amountClaimed')}
          <input
            type="number"
            step="0.01"
            value={form.amount_claimed || ''}
            onChange={field('amount_claimed', true)}
            required
          />
        </label>
        <label>
          {t('claims.currency')}
          <input value={form.currency} onChange={field('currency')} required />
        </label>
        <label>
          {t('claims.dateRaised')}
          <input value={form.date_raised} onChange={field('date_raised')} placeholder="YYYY-MM-DD" required />
        </label>
        <label>
          {t('claims.notes')}
          <input value={form.notes ?? ''} onChange={field('notes')} />
        </label>
        <button type="submit">{t('claims.createButton')}</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
