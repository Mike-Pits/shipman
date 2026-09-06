import { ApiError, apiGet, apiPost, apiPut } from './client'
import type { ExchangeRate } from './types'

export const fetchTodaysRate = () => apiPost<ExchangeRate>('/exchange-rates/fetch', undefined)

export const getRateForDate = async (rateDate: string): Promise<ExchangeRate | null> => {
  try {
    return await apiGet<ExchangeRate>(`/exchange-rates/${rateDate}`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

export const overrideRateForDate = (rateDate: string, usdRubRate: number) =>
  apiPut<ExchangeRate>(`/exchange-rates/${rateDate}`, { usd_rub_rate: usdRubRate })
