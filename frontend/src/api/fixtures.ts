import { apiGet, apiPost, apiPut } from './client'
import type { Fixture, FixtureCreate, GenerateHireInstallmentsRequest, Payment } from './types'

export const listFixtures = () => apiGet<Fixture[]>('/fixtures')
export const getFixture = (id: number) => apiGet<Fixture>(`/fixtures/${id}`)
export const createFixture = (payload: FixtureCreate) => apiPost<Fixture>('/fixtures', payload)
export const updateFixture = (id: number, payload: FixtureCreate) =>
  apiPut<Fixture>(`/fixtures/${id}`, payload)
export const generateHireInstallments = (id: number, payload: GenerateHireInstallmentsRequest) =>
  apiPost<Payment[]>(`/fixtures/${id}/generate-hire-installments`, payload)
