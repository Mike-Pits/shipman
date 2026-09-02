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
