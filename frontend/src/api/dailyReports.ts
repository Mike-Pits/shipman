import { ApiError, apiGet, apiPost, apiPut } from './client'
import type {
  DailyReport,
  DailyReportCreate,
  DailyReportUpdate,
  ImapFolderMapping,
  ImapPollResult,
  ImapSettings,
} from './types'

export const listDailyReports = (vesselId?: number) =>
  apiGet<DailyReport[]>(vesselId ? `/daily-reports?vessel_id=${vesselId}` : '/daily-reports')
export const getDailyReport = (id: number) => apiGet<DailyReport>(`/daily-reports/${id}`)
export const createDailyReport = (payload: DailyReportCreate) =>
  apiPost<DailyReport>('/daily-reports', payload)
export const updateDailyReport = (id: number, payload: DailyReportUpdate) =>
  apiPut<DailyReport>(`/daily-reports/${id}`, payload)
export const approveDailyReport = (id: number) =>
  apiPost<DailyReport>(`/daily-reports/${id}/approve`, undefined)

export const getImapSettings = () => apiGet<ImapSettings>('/daily-reports/imap-settings')
export const updateImapSettings = (folder: string) =>
  apiPut<ImapSettings>('/daily-reports/imap-settings', { folder })
export const pollImap = (vesselId: number, confirmVesselChange = false) =>
  apiPost<ImapPollResult>('/daily-reports/poll-imap', {
    vessel_id: vesselId,
    confirm_vessel_change: confirmVesselChange,
  })

export const getImapFolderMapping = async (folder: string): Promise<ImapFolderMapping | null> => {
  try {
    return await apiGet<ImapFolderMapping>(`/daily-reports/imap-folder-mapping/${encodeURIComponent(folder)}`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}
