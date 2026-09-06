import { apiGet, apiPost, apiPut } from './client'
import type { BunkerReplenishment, BunkerReplenishmentCreate } from './types'

export const listBunkerReplenishments = () => apiGet<BunkerReplenishment[]>('/bunker-replenishments')
export const getBunkerReplenishment = (id: number) =>
  apiGet<BunkerReplenishment>(`/bunker-replenishments/${id}`)
export const createBunkerReplenishment = (payload: BunkerReplenishmentCreate) =>
  apiPost<BunkerReplenishment>('/bunker-replenishments', payload)
export const updateBunkerReplenishment = (id: number, payload: BunkerReplenishmentCreate) =>
  apiPut<BunkerReplenishment>(`/bunker-replenishments/${id}`, payload)
