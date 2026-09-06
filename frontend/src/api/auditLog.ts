import { apiGet } from './client'
import type { AuditLogEntry } from './types'

export const listAuditLog = (tableName?: string) =>
  apiGet<AuditLogEntry[]>(tableName ? `/audit-log?table_name=${encodeURIComponent(tableName)}` : '/audit-log')
