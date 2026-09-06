import { useTranslation } from 'react-i18next'
import { NavLink, Route, Routes } from 'react-router-dom'
import LanguageToggle from './components/LanguageToggle'
import VesselsPage from './pages/VesselsPage'
import FixturesPage from './pages/FixturesPage'
import VoyagesPage from './pages/VoyagesPage'
import DailyReportsPage from './pages/DailyReportsPage'
import ExchangeRatesPage from './pages/ExchangeRatesPage'
import BunkerReplenishmentsPage from './pages/BunkerReplenishmentsPage'
import DisbursementAccountsPage from './pages/DisbursementAccountsPage'
import PaymentsPage from './pages/PaymentsPage'
import VoyageReportsPage from './pages/VoyageReportsPage'
import VoyageEstimatesPage from './pages/VoyageEstimatesPage'
import VettingInspectionsPage from './pages/VettingInspectionsPage'
import OffHirePage from './pages/OffHirePage'
import ClaimsPage from './pages/ClaimsPage'
import './App.css'

function App() {
  const { t } = useTranslation()

  return (
    <div className="app">
      <nav>
        <NavLink to="/vessels">{t('nav.vessels')}</NavLink>
        <NavLink to="/fixtures">{t('nav.fixtures')}</NavLink>
        <NavLink to="/voyages">{t('nav.voyages')}</NavLink>
        <NavLink to="/daily-reports">{t('nav.dailyReports')}</NavLink>
        <NavLink to="/exchange-rates">{t('nav.exchangeRates')}</NavLink>
        <NavLink to="/bunkers">{t('nav.bunkers')}</NavLink>
        <NavLink to="/disbursement-accounts">{t('nav.disbursementAccounts')}</NavLink>
        <NavLink to="/payments">{t('nav.payments')}</NavLink>
        <NavLink to="/voyage-reports">{t('nav.voyageReports')}</NavLink>
        <NavLink to="/voyage-estimates">{t('nav.voyageEstimates')}</NavLink>
        <NavLink to="/vetting">{t('nav.vetting')}</NavLink>
        <NavLink to="/off-hire">{t('nav.offHire')}</NavLink>
        <NavLink to="/claims">{t('nav.claims')}</NavLink>
        <LanguageToggle />
      </nav>
      <main>
        <Routes>
          <Route path="/vessels" element={<VesselsPage />} />
          <Route path="/fixtures" element={<FixturesPage />} />
          <Route path="/voyages" element={<VoyagesPage />} />
          <Route path="/daily-reports" element={<DailyReportsPage />} />
          <Route path="/exchange-rates" element={<ExchangeRatesPage />} />
          <Route path="/bunkers" element={<BunkerReplenishmentsPage />} />
          <Route path="/disbursement-accounts" element={<DisbursementAccountsPage />} />
          <Route path="/payments" element={<PaymentsPage />} />
          <Route path="/voyage-reports" element={<VoyageReportsPage />} />
          <Route path="/voyage-estimates" element={<VoyageEstimatesPage />} />
          <Route path="/vetting" element={<VettingInspectionsPage />} />
          <Route path="/off-hire" element={<OffHirePage />} />
          <Route path="/claims" element={<ClaimsPage />} />
          <Route path="*" element={<VesselsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
