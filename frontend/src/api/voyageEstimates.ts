import { apiGet, apiPost, apiPut } from './client'
import type { EstimateStatus, Fixture, FixtureCreate, VoyageEstimate, VoyageEstimateCreate } from './types'

export const listVoyageEstimates = () => apiGet<VoyageEstimate[]>('/voyage-estimates')
export const createVoyageEstimate = (payload: VoyageEstimateCreate) =>
  apiPost<VoyageEstimate>('/voyage-estimates', payload)
export const updateVoyageEstimate = (id: number, payload: VoyageEstimateCreate) =>
  apiPut<VoyageEstimate>(`/voyage-estimates/${id}`, payload)
export const updateVoyageEstimateStatus = (id: number, status: Extract<EstimateStatus, 'under_negotiation' | 'declined'>) =>
  apiPost<VoyageEstimate>(`/voyage-estimates/${id}/status`, { status })
export const promoteVoyageEstimate = (id: number, payload: FixtureCreate) =>
  apiPost<Fixture>(`/voyage-estimates/${id}/promote`, payload)
