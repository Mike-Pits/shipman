import { apiGet } from './client'
import type { ClaimsStatusRow, DaReconciliationRow, FleetPnl, FleetVettingStatusRow, VoyagePnl, VoyageTce } from './types'

export const getVoyagePnl = (voyageId: number) => apiGet<VoyagePnl>(`/reports/voyage-pnl/${voyageId}`)
export const getVoyageTce = (voyageId: number) => apiGet<VoyageTce>(`/reports/tce/${voyageId}`)
export const voyagePnlExportUrl = (voyageId: number) => `/api/reports/voyage-pnl/${voyageId}?format=xlsx`
export const voyageTceExportUrl = (voyageId: number) => `/api/reports/tce/${voyageId}?format=xlsx`

export const getFleetPnl = (startDate: string, endDate: string) =>
  apiGet<FleetPnl>(`/reports/fleet-pnl?start_date=${startDate}&end_date=${endDate}`)
export const fleetPnlExportUrl = (startDate: string, endDate: string) =>
  `/api/reports/fleet-pnl?start_date=${startDate}&end_date=${endDate}&format=xlsx`

export const getDaReconciliation = () => apiGet<DaReconciliationRow[]>('/reports/da-reconciliation')
export const daReconciliationExportUrl = () => '/api/reports/da-reconciliation?format=xlsx'

export const getFleetVettingStatus = () => apiGet<FleetVettingStatusRow[]>('/reports/vetting-status')
export const fleetVettingStatusExportUrl = () => '/api/reports/vetting-status?format=xlsx'

export const getClaimsStatus = () => apiGet<ClaimsStatusRow[]>('/reports/claims-status')
export const claimsStatusExportUrl = () => '/api/reports/claims-status?format=xlsx'
