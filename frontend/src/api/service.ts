import { apiDelete, apiGet, apiPost, apiPut, apiUpload } from './client'
import type {
  BackupEntry,
  CompactResult,
  HealthReport,
  RestoreResult,
  ServiceSettings,
  ServiceStatus,
} from './types'

export const getServiceStatus = () => apiGet<ServiceStatus>('/service/status')
export const updateServiceSettings = (settings: ServiceSettings) =>
  apiPut<ServiceStatus>('/service/settings', settings)
export const listBackups = () => apiGet<BackupEntry[]>('/service/backups')
export const createBackup = () => apiPost<BackupEntry>('/service/backups', {})
export const importBackup = (file: File) => apiUpload<BackupEntry>('/service/backups/import', file)
export const deleteBackup = (name: string) => apiDelete<void>(`/service/backups/${encodeURIComponent(name)}`)
export const restoreBackup = (name: string, confirm: string) =>
  apiPost<RestoreResult>(`/service/backups/${encodeURIComponent(name)}/restore`, { confirm })
export const compactDatabase = () => apiPost<CompactResult>('/service/compact', {})
export const getHealthReport = () => apiGet<HealthReport>('/service/health')

export const backupDownloadUrl = (name: string) => `/api/service/backups/${encodeURIComponent(name)}/download`
export const EXPORT_URL = '/api/service/export'
