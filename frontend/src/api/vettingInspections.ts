import { apiGet, apiPost } from './client'
import type { VettingInspection, VettingInspectionCreate, VettingStatusRead } from './types'

export const listVettingInspections = (vesselId: number) =>
  apiGet<VettingInspection[]>(`/vessels/${vesselId}/vetting-inspections`)
export const createVettingInspection = (vesselId: number, payload: VettingInspectionCreate) =>
  apiPost<VettingInspection>(`/vessels/${vesselId}/vetting-inspections`, payload)
export const getVettingStatus = (vesselId: number) =>
  apiGet<VettingStatusRead>(`/vessels/${vesselId}/vetting-status`)
