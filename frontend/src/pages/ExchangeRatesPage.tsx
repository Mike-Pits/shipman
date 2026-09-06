import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchTodaysRate, getRateForDate, overrideRateForDate } from '../api/exchangeRates'
import type { ExchangeRate } from '../api/types'

const today = () => new Date().toISOString().slice(0, 10)

export default function ExchangeRatesPage() {
  const { t } = useTranslation()
  const [todaysRate, setTodaysRate] = useState<ExchangeRate | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [lookupDate, setLookupDate] = useState('')
  const [lookupResult, setLookupResult] = useState<ExchangeRate | null | 'not_found'>(null)
  const [overrideValue, setOverrideValue] = useState('')

  useEffect(() => {
    getRateForDate(today()).then(setTodaysRate)
  }, [])

  const handleFetchToday = async () => {
    setError(null)
    try {
      const rate = await fetchTodaysRate()
      setTodaysRate(rate)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch rate')
    }
  }

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const rate = await getRateForDate(lookupDate)
      setLookupResult(rate ?? 'not_found')
      setOverrideValue(rate ? String(rate.usd_rub_rate) : '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to look up rate')
    }
  }

  const handleSaveOverride = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const rate = await overrideRateForDate(lookupDate, Number(overrideValue))
      setLookupResult(rate)
      if (lookupDate === today()) setTodaysRate(rate)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save rate')
    }
  }

  return (
    <div>
      <h1>{t('exchangeRates.title')}</h1>

      <h2>{t('exchangeRates.todaysRateHeading')}</h2>
      {todaysRate ? (
        <p>
          {t('exchangeRates.rateLabel')}: {todaysRate.usd_rub_rate}
          {todaysRate.manual_override && <> — {t('exchangeRates.manualOverride')}</>}
        </p>
      ) : (
        <p>{t('exchangeRates.notFetchedYet')}</p>
      )}
      {todaysRate?.stale && <p role="alert">{t('exchangeRates.staleWarning')}</p>}
      <button type="button" onClick={handleFetchToday}>
        {t('exchangeRates.fetchButton')}
      </button>

      <h2>{t('exchangeRates.lookupHeading')}</h2>
      <form onSubmit={handleLookup}>
        <label>
          {t('exchangeRates.dateLabel')}
          <input
            value={lookupDate}
            onChange={(e) => setLookupDate(e.target.value)}
            placeholder="YYYY-MM-DD"
            required
          />
        </label>
        <button type="submit">{t('exchangeRates.lookupButton')}</button>
      </form>

      {lookupResult === 'not_found' && <p>{t('exchangeRates.notFoundForDate')}</p>}
      {lookupResult && lookupResult !== 'not_found' && lookupResult.manual_override && (
        <p>{t('exchangeRates.manualOverride')}</p>
      )}

      {lookupResult !== null && (
        <form onSubmit={handleSaveOverride}>
          <label>
            {t('exchangeRates.overrideRateLabel')}
            <input
              type="number"
              step="0.0001"
              value={overrideValue}
              onChange={(e) => setOverrideValue(e.target.value)}
              required
            />
          </label>
          <button type="submit">{t('exchangeRates.saveButton')}</button>
        </form>
      )}

      {error && (
        <p role="alert" className="alert-danger">
          {error}
        </p>
      )}
    </div>
  )
}
