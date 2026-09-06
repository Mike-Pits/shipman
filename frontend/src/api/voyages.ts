import { apiGet, apiPost, apiPut } from './client'
import type { Voyage, VoyageCreate } from './types'

export const listVoyages = () => apiGet<Voyage[]>('/voyages')
export const getVoyage = (id: number) => apiGet<Voyage>(`/voyages/${id}`)
export const createVoyage = (payload: VoyageCreate) => apiPost<Voyage>('/voyages', payload)
export const updateVoyage = (id: number, payload: VoyageCreate) =>
  apiPut<Voyage>(`/voyages/${id}`, payload)
