import { apiGet, apiPost } from './client'
import type { OffHirePeriod, OffHirePeriodCreate } from './types'

export const listOffHirePeriods = (voyageId: number) =>
  apiGet<OffHirePeriod[]>(`/voyages/${voyageId}/off-hire-periods`)
export const createOffHirePeriod = (voyageId: number, payload: OffHirePeriodCreate) =>
  apiPost<OffHirePeriod>(`/voyages/${voyageId}/off-hire-periods`, payload)
