import { apiDelete, apiGet, apiPost, apiPut } from './client'
import type { Invoice, InvoiceCreate } from './types'

export const listInvoices = () => apiGet<Invoice[]>('/invoices')
export const getInvoice = (id: number) => apiGet<Invoice>(`/invoices/${id}`)
export const createInvoice = (payload: InvoiceCreate) => apiPost<Invoice>('/invoices', payload)
export const updateInvoice = (id: number, payload: InvoiceCreate) => apiPut<Invoice>(`/invoices/${id}`, payload)
export const deleteInvoice = (id: number) => apiDelete<void>(`/invoices/${id}`)
export const issueInvoice = (id: number) => apiPost<Invoice>(`/invoices/${id}/issue`, {})
export const voidInvoice = (id: number) => apiPost<Invoice>(`/invoices/${id}/void`, {})
