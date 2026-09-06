import { apiDelete, apiGet, apiPost, apiPut } from './client'
import type { Vessel, VesselCreate } from './types'

export const listVessels = () => apiGet<Vessel[]>('/vessels')
export const getVessel = (id: number) => apiGet<Vessel>(`/vessels/${id}`)
export const createVessel = (payload: VesselCreate) => apiPost<Vessel>('/vessels', payload)
export const updateVessel = (id: number, payload: VesselCreate) =>
  apiPut<Vessel>(`/vessels/${id}`, payload)
export const deleteVessel = (id: number) => apiDelete<void>(`/vessels/${id}`)
