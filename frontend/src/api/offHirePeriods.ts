import { apiGet, apiPost, apiPut } from './client'
import type { OffHirePeriod, OffHirePeriodCreate } from './types'

export const listOffHirePeriods = (voyageId: number) =>
  apiGet<OffHirePeriod[]>(`/voyages/${voyageId}/off-hire-periods`)
export const createOffHirePeriod = (voyageId: number, payload: OffHirePeriodCreate) =>
  apiPost<OffHirePeriod>(`/voyages/${voyageId}/off-hire-periods`, payload)
export const updateOffHirePeriod = (voyageId: number, periodId: number, payload: OffHirePeriodCreate) =>
  apiPut<OffHirePeriod>(`/voyages/${voyageId}/off-hire-periods/${periodId}`, payload)
