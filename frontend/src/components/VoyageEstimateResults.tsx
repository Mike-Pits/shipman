import { useTranslation } from 'react-i18next'
import StatCard from './ui/StatCard'
import type { EstimateResults, VoyageEstimateCreate } from '../api/types'

const money = (v: number, currency: string) =>
  `${v < 0 ? '-' : ''}${Math.abs(v).toLocaleString(undefined, { maximumFractionDigits: 0 })} ${currency}`
const num = (v: number, digits = 3) =>
  v.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: digits })

function warningText(t: (k: string, o?: Record<string, string>) => string, code: string) {
  const [key, arg] = code.split(':')
  return t(`voyageEstimates.warning_${key}`, { grade: arg ?? '' })
}

export default function VoyageEstimateResults({
  results,
  form,
  vesselName,
}: {
  results: EstimateResults
  form: VoyageEstimateCreate
  vesselName: string
}) {
  const { t } = useTranslation()
  const cur = form.currency
  const items = form.cost_items.filter((i) => i.amount > 0)

  return (
    <section className="estimate-results" aria-label={t('voyageEstimates.resultsHeading')}>
      <h2>{t('voyageEstimates.resultsHeading')}</h2>
      {results.warnings.map((w) => (
        <p key={w} role="alert" className="alert-danger">
          {warningText(t, w)}
        </p>
      ))}

      <div className="results-grid">
        <StatCard label={t('voyageEstimates.resultVessel')} value={vesselName || '—'} />
        <StatCard label={t('voyageEstimates.resultDistance')} value={`${num(results.total_distance_nm, 1)} NM`} />
        <StatCard label={t('voyageEstimates.resultTotalDays')} value={num(results.total_voyage_days)} />
        <StatCard
          label={t('voyageEstimates.resultTce')}
          value={money(results.tce_per_day, cur)}
          sub={t('voyageEstimates.perDay')}
          tone={results.tce_per_day < 0 ? 'danger' : results.tce_per_day > 0 ? 'success' : undefined}
        />
      </div>

      <h3>{t('voyageEstimates.timeBreakdown')}</h3>
      <div className="results-grid">
        <StatCard label={t('voyageEstimates.timeSea')} value={num(results.sea_days)} />
        <StatCard label={t('voyageEstimates.timeLoad')} value={num(results.load_days)} />
        <StatCard label={t('voyageEstimates.timeDischarge')} value={num(results.discharge_days)} />
      </div>

      {Object.keys(results.fuel).length > 0 && (
        <>
          <h3>{t('voyageEstimates.fuelConsumption')}</h3>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t('voyageEstimates.fuelGrade')}</th>
                  <th>{t('voyageEstimates.fuelQty')}</th>
                  <th>{t('voyageEstimates.fuelCost')}</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(results.fuel).map(([grade, f]) => (
                  <tr key={grade}>
                    <td>{grade}</td>
                    <td>{num(f.quantity_mt)}</td>
                    <td>{money(f.cost, cur)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <h3>{t('voyageEstimates.costSummary')}</h3>
      <div className="result-line">
        <span>{t('voyageEstimates.costFuel')}</span>
        <span>{money(results.total_fuel_cost, cur)}</span>
      </div>
      {(
        [
          ['canalFees', form.canal_fees],
          ['portCharges', form.port_charges],
          ['agentFees', form.agent_fees],
          ['bunkerSurcharge', form.bunker_surcharge],
          ['extraCosts', form.extra_costs],
        ] as const
      )
        .filter(([, v]) => v > 0)
        .map(([key, v]) => (
          <div className="result-line" key={key}>
            <span>{t(`voyageEstimates.${key}`)}</span>
            <span>{money(v, cur)}</span>
          </div>
        ))}
      {items.map((i, idx) => (
        <div className="result-line" key={idx}>
          <span>{i.description || t('voyageEstimates.customCost')}</span>
          <span>{money(i.amount, cur)}</span>
        </div>
      ))}
      {results.demurrage > 0 && (
        <div className="result-line">
          <span>{t('voyageEstimates.demurrage')}</span>
          <span>{money(results.demurrage, cur)}</span>
        </div>
      )}
      <div className="result-line total">
        <span>{t('voyageEstimates.totalCosts')}</span>
        <span>{money(results.total_costs, cur)}</span>
      </div>

      <h3>{t('voyageEstimates.revenue')}</h3>
      <div className="result-line">
        <span>{t('voyageEstimates.freight')}</span>
        <span>{money(results.freight_revenue, cur)}</span>
      </div>
      <div className="result-line total">
        <span>{t('voyageEstimates.netResult')}</span>
        <span>{money(results.net_result, cur)}</span>
      </div>

      <div className={`demurrage-note${results.excess_days > 0 ? ' has-demurrage' : ''}`}>
        {results.excess_days > 0
          ? `${t('voyageEstimates.demurrage')}: ${num(results.excess_days)} ${t('voyageEstimates.excessDays')} → ${money(results.demurrage, cur)}`
          : t('voyageEstimates.noDemurrage')}
      </div>
    </section>
  )
}
