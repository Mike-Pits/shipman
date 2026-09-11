import { apiDelete, apiGet, apiPost, apiPut } from './client'
import type { Currency, Payment, PaymentCreate, PaymentStatus, PaymentWithDisplay } from './types'

export const listPayments = () => apiGet<Payment[]>('/payments')
export const createPayment = (payload: PaymentCreate) => apiPost<Payment>('/payments', payload)
export const updatePayment = (id: number, payload: PaymentCreate) => apiPut<Payment>(`/payments/${id}`, payload)
export const deletePayment = (id: number) => apiDelete<void>(`/payments/${id}`)
export const updatePaymentStatus = (id: number, status: PaymentStatus) =>
  apiPost<Payment>(`/payments/${id}/status`, { status })
export const getPaymentWithDisplay = (id: number, displayCurrency: Currency) =>
  apiGet<PaymentWithDisplay>(`/payments/${id}?display_currency=${displayCurrency}`)
