import { apiGet, apiPost, apiPut } from './client'
import type { Claim, ClaimCreate, ClaimStatus } from './types'

export const listClaims = (status?: ClaimStatus) =>
  apiGet<Claim[]>(status ? `/claims?status=${status}` : '/claims')
export const createClaim = (payload: ClaimCreate) => apiPost<Claim>('/claims', payload)
export const updateClaim = (id: number, payload: ClaimCreate) => apiPut<Claim>(`/claims/${id}`, payload)
export const updateClaimStatus = (id: number, status: Extract<ClaimStatus, 'negotiating' | 'rejected'>) =>
  apiPost<Claim>(`/claims/${id}/status`, { status })
export const settleClaim = (id: number, amountSettled: number, paymentId?: number | null) =>
  apiPost<Claim>(`/claims/${id}/settle`, { amount_settled: amountSettled, payment_id: paymentId ?? null })
