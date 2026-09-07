export type Currency = 'RUB' | 'USD'

export type FuelConsumptionMode = 'laden' | 'ballast' | 'idle_anchor' | 'discharging'

export interface FuelConsumptionProfile {
  mode: FuelConsumptionMode
  ifo_mt_per_day: number
  mgo_mt_per_day: number
}

export interface FuelConsumptionProfileRead extends FuelConsumptionProfile {
  id: number
}

export interface VesselCreate {
  name: string
  imo_number: string
  flag: string
  year_built: number
  vessel_type: string
  dwt: number
  loa: number
  beam: number
  draft: number
  cargo_tank_capacity_cbm: number
  ice_class: string
  engine_power_kw: number
  fuel_consumption_profiles: FuelConsumptionProfile[]
}

export interface Vessel extends VesselCreate {
  id: number
  fuel_consumption_profiles: FuelConsumptionProfileRead[]
}

export type FixtureType = 'voyage_charter' | 'time_charter_out' | 'coa'
export type FreightRateBasis = 'per_tonne' | 'lump_sum'
export type HireRateBasis = 'daily' | 'monthly'
export type HirePaymentBasis = 'advance' | 'arrears' | 'days_after_invoice'

export interface FixtureBroker {
  broker_name: string
  commission_percentage: number
}

export interface FixtureBrokerRead extends FixtureBroker {
  id: number
}

export interface FixtureCreate {
  fixture_type: FixtureType
  charterer: string
  contract_currency: Currency

  date_concluded?: string
  charter_party_ref?: string
  charter_party_type?: string

  // Voyage Charter
  freight_rate?: number
  freight_rate_basis?: FreightRateBasis
  laycan_start?: string
  laycan_end?: string
  load_port?: string
  discharge_port?: string
  cargo_grade?: string
  demurrage_rate?: number
  despatch_rate?: number
  laytime_terms?: string

  // Time Charter Out
  hire_rate?: number
  hire_rate_basis?: HireRateBasis
  charter_period_from?: string
  charter_period_to?: string
  delivery_port?: string
  delivery_rob_ifo_mt?: number
  delivery_rob_mgo_mt?: number
  redelivery_port?: string
  redelivery_rob_ifo_mt?: number
  redelivery_rob_mgo_mt?: number
  redelivery_conditions?: string
  hire_payment_basis?: HirePaymentBasis
  hire_payment_frequency_days?: number
  hire_payment_days_after_invoice?: number

  // COA
  contract_period_from?: string
  contract_period_to?: string
  total_contracted_quantity?: number
  number_of_lifts?: number
  rate_per_tonne?: number
  min_cargo_quantity_per_lift?: number
  max_cargo_quantity_per_lift?: number

  brokers: FixtureBroker[]
}

export interface Fixture extends FixtureCreate {
  id: number
  brokers: FixtureBrokerRead[]
}

export interface GenerateHireInstallmentsRequest {
  vessel_id: number
  invoice_date_override?: string
}

export interface VoyageCreate {
  fixture_id: number
  vessel_id: number
  voyage_number: string
  load_port: string
  discharge_port: string
  start_date: string
  end_date?: string | null
  cargo_grade: string
  cargo_quantity_mt: number
  laden: boolean
  ice_notes?: string | null
}

export interface Voyage extends VoyageCreate {
  id: number
  warnings: string[]
}

export interface DailyReportCreate {
  vessel_id: number
  voyage_id?: number | null
  raw_text: string
}

export interface DailyReportUpdate {
  raw_text: string
  override?: boolean
}

export interface DailyReport {
  id: number
  vessel_id: number
  voyage_id: number | null
  report_datetime: string
  raw_text: string
  fields: Record<string, string>
  approved: boolean
  warnings: string[]
  source_message_id: string | null
}

export interface ImapSettings {
  folder: string
}

export interface ImapPollResult {
  ingested: DailyReport[]
  skipped_duplicates: string[]
  errors: { message_id: string; detail: string }[]
}

export interface ImapFolderMapping {
  folder: string
  vessel_id: number
}

export interface ExchangeRate {
  id: number
  rate_date: string
  usd_rub_rate: number
  manual_override: boolean
  stale: boolean
}

export interface BunkerReplenishmentLineCreate {
  fuel_grade: string
  quantity_mt: number
  price_per_mt: number
}

export interface BunkerReplenishmentLineRead extends BunkerReplenishmentLineCreate {
  id: number
  total_cost: number
}

export interface BunkerReplenishmentCreate {
  vessel_id: number
  replenishment_datetime: string
  port: string
  supplier: string
  invoice_number?: string | null
  currency: Currency
  lines: BunkerReplenishmentLineCreate[]
}

export interface BunkerReplenishment extends Omit<BunkerReplenishmentCreate, 'lines'> {
  id: number
  lines: BunkerReplenishmentLineRead[]
  total_cost: number
}

export type DisbursementAccountStatus = 'pda_only' | 'fda_pending' | 'reconciled' | 'disputed'

export interface DisbursementAccountLineCreate {
  line_type: string
  description: string
  amount: number
  currency: Currency
}

export interface DisbursementAccountLineRead extends DisbursementAccountLineCreate {
  id: number
}

export interface DisbursementAccountCreate {
  voyage_id: number
  port: string
  pda_amount: number
  pda_currency: Currency
  pda_date: string
}

export interface DisbursementAccount extends DisbursementAccountCreate {
  id: number
  status: DisbursementAccountStatus
  lines: DisbursementAccountLineRead[]
  fda_total: number
  variance: number
}

export type CostCategory = 'income' | 'expense'
export type PaymentStatus = 'draft' | 'pending' | 'invoiced' | 'partial' | 'paid' | 'overdue'

export interface PaymentCreate {
  vessel_id: number
  voyage_id?: number | null
  fixture_id?: number | null
  disbursement_account_id?: number | null
  vendor_name?: string | null
  cost_category: CostCategory
  cost_type_name: string

  original_currency: Currency
  original_amount: number

  invoice_date: string
  due_date?: string | null
  payment_date?: string | null
  status?: PaymentStatus

  document_number?: string | null
  notes?: string | null
}

export interface Payment extends PaymentCreate {
  id: number
  status: PaymentStatus
  rub_equivalent: number
  exchange_rate_used: number | null
  exchange_rate_date: string | null
}

export interface PaymentWithDisplay extends Payment {
  display_currency: Currency
  display_amount: number
}

export interface VoyagePnl {
  voyage_id: number
  revenue: number
  costs: number
  net_result: number
  currency: string
  estimated_net_result?: number
  variance_vs_estimate?: number
}

export interface VoyageTce extends VoyagePnl {
  duration_days: number
  off_hire_days: number
  earning_days: number
  tce_per_day: number
}

export type EstimateStatus = 'draft' | 'under_negotiation' | 'fixed' | 'declined'
export type RateBasis = 'per_tonne' | 'lump_sum'

export interface VoyageEstimateCreate {
  vessel_id?: number | null
  load_port: string
  discharge_port: string
  laycan_start: string
  laycan_end: string
  cargo_grade: string
  estimated_cargo_quantity_mt: number
  estimated_rate: number
  estimated_rate_basis: RateBasis
  currency: Currency
  estimated_bunker_consumption_mt: number
  estimated_bunker_cost: number
  estimated_port_costs: number
  estimated_duration_days: number
}

export interface VoyageEstimate extends VoyageEstimateCreate {
  id: number
  status: EstimateStatus
  fixture_id: number | null
  warnings: string[]
  estimated_revenue: number
  estimated_costs: number
  estimated_net_result: number
  estimated_tce_per_day: number
}

export type VettingStatus = 'approved' | 'pending' | 'expired' | 'failed'

export interface VettingInspectionCreate {
  inspection_date: string
  inspecting_body: string
  inspection_type: string
  expiry_date: string
  status: VettingStatus
  observations?: string | null
}

export interface VettingInspection extends VettingInspectionCreate {
  id: number
  vessel_id: number
}

export interface VettingStatusRead {
  status: VettingStatus | null
  inspecting_body?: string | null
  expiry_date?: string | null
}

export interface OffHirePeriodCreate {
  start_datetime: string
  end_datetime: string
  reason: string
  override_deduction?: number | null
}

export interface OffHirePeriod extends OffHirePeriodCreate {
  id: number
  voyage_id: number
  calculated_deduction: number
  duration_days: number
  effective_deduction: number
}

export type ClaimType = 'cargo_quantity' | 'cargo_quality' | 'demurrage_dispute' | 'off_hire_dispute' | 'other'
export type ClaimStatus = 'open' | 'negotiating' | 'settled' | 'rejected'

export interface ClaimCreate {
  voyage_id?: number | null
  fixture_id?: number | null
  disbursement_account_id?: number | null
  claim_type: ClaimType
  counterparty: string
  amount_claimed: number
  currency: Currency
  date_raised: string
  notes?: string | null
}

export interface Claim extends ClaimCreate {
  id: number
  amount_settled: number | null
  status: ClaimStatus
  date_resolved: string | null
  settled_payment_id: number | null
}

export interface FleetPnl {
  start_date: string
  end_date: string
  revenue: number
  costs: number
  net_result: number
  voyage_count: number
  currency: string
}

export interface DaReconciliationRow {
  id: number
  voyage_id: number
  port: string
  status: DisbursementAccountStatus
  pda_amount: number
  fda_total: number
  variance: number
}

export interface FleetVettingStatusRow {
  vessel_id: number
  vessel_name: string
  status: VettingStatus | null
  expiry_date: string | null
}

export interface ClaimsStatusRow {
  id: number
  voyage_id: number | null
  claim_type: ClaimType
  counterparty: string
  amount_claimed: number
  currency: string
  status: ClaimStatus
  age_days: number
}

export interface AuditLogEntry {
  id: number
  table_name: string
  record_id: number | null
  action: string
  old_values: string | null
  new_values: string | null
  user: string
  timestamp: string
}
