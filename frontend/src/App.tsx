import { NavLink, Route, Routes } from 'react-router-dom'
import VesselsPage from './pages/VesselsPage'
import './App.css'

function App() {
  return (
    <div className="app">
      <nav>
        <NavLink to="/vessels">Vessels</NavLink>
      </nav>
      <main>
        <Routes>
          <Route path="/vessels" element={<VesselsPage />} />
          <Route path="*" element={<VesselsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
