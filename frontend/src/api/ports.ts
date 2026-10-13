import { apiDelete, apiGet, apiPost } from './client'
import type { Port } from './types'

export const listPorts = () => apiGet<Port[]>('/ports')
export const createPort = (name: string) => apiPost<Port>('/ports', { name })
export const deletePort = (id: number) => apiDelete<void>(`/ports/${id}`)
