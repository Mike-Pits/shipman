import { apiGet } from './client'
import type { VoyagePnl, VoyageTce } from './types'

export const getVoyagePnl = (voyageId: number) => apiGet<VoyagePnl>(`/reports/voyage-pnl/${voyageId}`)
export const getVoyageTce = (voyageId: number) => apiGet<VoyageTce>(`/reports/tce/${voyageId}`)
export const voyagePnlExportUrl = (voyageId: number) => `/api/reports/voyage-pnl/${voyageId}?format=xlsx`
export const voyageTceExportUrl = (voyageId: number) => `/api/reports/tce/${voyageId}?format=xlsx`
