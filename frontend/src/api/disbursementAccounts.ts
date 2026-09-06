import { apiGet, apiPost, apiPut } from './client'
import type { DisbursementAccount, DisbursementAccountCreate, DisbursementAccountLineCreate } from './types'

export const listDisbursementAccounts = () => apiGet<DisbursementAccount[]>('/disbursement-accounts')
export const getDisbursementAccount = (id: number) =>
  apiGet<DisbursementAccount>(`/disbursement-accounts/${id}`)
export const createDisbursementAccount = (payload: DisbursementAccountCreate) =>
  apiPost<DisbursementAccount>('/disbursement-accounts', payload)
export const updateDisbursementAccount = (id: number, payload: DisbursementAccountCreate) =>
  apiPut<DisbursementAccount>(`/disbursement-accounts/${id}`, payload)
export const addFdaLines = (id: number, lines: DisbursementAccountLineCreate[]) =>
  apiPost<DisbursementAccount>(`/disbursement-accounts/${id}/fda-lines`, { lines })
export const updateFdaLine = (id: number, lineId: number, payload: DisbursementAccountLineCreate) =>
  apiPut<DisbursementAccount>(`/disbursement-accounts/${id}/fda-lines/${lineId}`, payload)
export const reconcileDisbursementAccount = (id: number) =>
  apiPost<DisbursementAccount>(`/disbursement-accounts/${id}/reconcile`, undefined)
export const disputeDisbursementAccount = (id: number) =>
  apiPost<DisbursementAccount>(`/disbursement-accounts/${id}/dispute`, undefined)
