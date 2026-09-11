import { useTranslation } from 'react-i18next'
import { NavLink, Route, Routes } from 'react-router-dom'
import {
  Anchor,
  BarChart3,
  Calculator,
  ClipboardList,
  CreditCard,
  FileSpreadsheet,
  FileText,
  Fuel,
  Gavel,
  History,
  Landmark,
  LayoutDashboard,
  PauseCircle,
  Receipt,
  Route as RouteIcon,
  Ship,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react'
import LanguageToggle from './components/LanguageToggle'
import VesselsPage from './pages/VesselsPage'
import FixturesPage from './pages/FixturesPage'
import VoyagesPage from './pages/VoyagesPage'
import DailyReportsPage from './pages/DailyReportsPage'
import ExchangeRatesPage from './pages/ExchangeRatesPage'
import BunkerReplenishmentsPage from './pages/BunkerReplenishmentsPage'
import DisbursementAccountsPage from './pages/DisbursementAccountsPage'
import PaymentsPage from './pages/PaymentsPage'
import InvoicingPage from './pages/InvoicingPage'
import VoyageReportsPage from './pages/VoyageReportsPage'
import VoyageEstimatesPage from './pages/VoyageEstimatesPage'
import VettingInspectionsPage from './pages/VettingInspectionsPage'
import OffHirePage from './pages/OffHirePage'
import ClaimsPage from './pages/ClaimsPage'
import ReportsPage from './pages/ReportsPage'
import AuditLogPage from './pages/AuditLogPage'
import DashboardPage from './pages/DashboardPage'
import './App.css'

function App() {
  const { t } = useTranslation()

  return (
    <div className="app">
      <nav>
        <NavLink to="/" end className="nav-link nav-link-top">
          <LayoutDashboard size={16} />
          {t('nav.dashboard')}
        </NavLink>

        <div className="nav-group">
          <div className="nav-group-header">{t('nav.groupFleet')}</div>
          <NavLink to="/vessels" className="nav-link">
            <Ship size={16} />
            {t('nav.vessels')}
          </NavLink>
          <NavLink to="/fixtures" className="nav-link">
            <FileText size={16} />
            {t('nav.fixtures')}
          </NavLink>
          <NavLink to="/voyages" className="nav-link">
            <RouteIcon size={16} />
            {t('nav.voyages')}
          </NavLink>
          <NavLink to="/daily-reports" className="nav-link">
            <ClipboardList size={16} />
            {t('nav.dailyReports')}
          </NavLink>
          <NavLink to="/exchange-rates" className="nav-link">
            <Landmark size={16} />
            {t('nav.exchangeRates')}
          </NavLink>
        </div>

        <div className="nav-group">
          <div className="nav-group-header">{t('nav.groupFinancial')}</div>
          <NavLink to="/bunkers" className="nav-link">
            <Fuel size={16} />
            {t('nav.bunkers')}
          </NavLink>
          <NavLink to="/disbursement-accounts" className="nav-link">
            <Receipt size={16} />
            {t('nav.disbursementAccounts')}
          </NavLink>
          <NavLink to="/payments" className="nav-link">
            <CreditCard size={16} />
            {t('nav.payments')}
          </NavLink>
          <NavLink to="/invoicing" className="nav-link">
            <FileSpreadsheet size={16} />
            {t('nav.invoicing')}
          </NavLink>
          <NavLink to="/voyage-reports" className="nav-link">
            <TrendingUp size={16} />
            {t('nav.voyageReports')}
          </NavLink>
        </div>

        <div className="nav-group">
          <div className="nav-group-header">{t('nav.groupCommercial')}</div>
          <NavLink to="/voyage-estimates" className="nav-link">
            <Calculator size={16} />
            {t('nav.voyageEstimates')}
          </NavLink>
          <NavLink to="/vetting" className="nav-link">
            <ShieldCheck size={16} />
            {t('nav.vetting')}
          </NavLink>
          <NavLink to="/off-hire" className="nav-link">
            <PauseCircle size={16} />
            {t('nav.offHire')}
          </NavLink>
          <NavLink to="/claims" className="nav-link">
            <Gavel size={16} />
            {t('nav.claims')}
          </NavLink>
        </div>

        <div className="nav-group">
          <div className="nav-group-header">{t('nav.groupReporting')}</div>
          <NavLink to="/reports" className="nav-link">
            <BarChart3 size={16} />
            {t('nav.reports')}
          </NavLink>
          <NavLink to="/audit-log" className="nav-link">
            <History size={16} />
            {t('nav.auditLog')}
          </NavLink>
        </div>

        <div className="nav-footer">
          <Anchor size={16} className="nav-brand-icon" />
          <LanguageToggle />
        </div>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/vessels" element={<VesselsPage />} />
          <Route path="/fixtures" element={<FixturesPage />} />
          <Route path="/voyages" element={<VoyagesPage />} />
          <Route path="/daily-reports" element={<DailyReportsPage />} />
          <Route path="/exchange-rates" element={<ExchangeRatesPage />} />
          <Route path="/bunkers" element={<BunkerReplenishmentsPage />} />
          <Route path="/disbursement-accounts" element={<DisbursementAccountsPage />} />
          <Route path="/payments" element={<PaymentsPage />} />
          <Route path="/invoicing" element={<InvoicingPage />} />
          <Route path="/voyage-reports" element={<VoyageReportsPage />} />
          <Route path="/voyage-estimates" element={<VoyageEstimatesPage />} />
          <Route path="/vetting" element={<VettingInspectionsPage />} />
          <Route path="/off-hire" element={<OffHirePage />} />
          <Route path="/claims" element={<ClaimsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/audit-log" element={<AuditLogPage />} />
          <Route path="*" element={<VesselsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
