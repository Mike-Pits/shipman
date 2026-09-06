import { apiGet, apiPost } from './client'
import type { BunkerReplenishment, BunkerReplenishmentCreate } from './types'

export const listBunkerReplenishments = () => apiGet<BunkerReplenishment[]>('/bunker-replenishments')
export const getBunkerReplenishment = (id: number) =>
  apiGet<BunkerReplenishment>(`/bunker-replenishments/${id}`)
export const createBunkerReplenishment = (payload: BunkerReplenishmentCreate) =>
  apiPost<BunkerReplenishment>('/bunker-replenishments', payload)
