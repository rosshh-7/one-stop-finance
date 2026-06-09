import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { LandingPage } from '@/pages/LandingPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ThemesPage } from '@/pages/ThemesPage'
import { OptionsPage } from '@/pages/OptionsPage'
import { InsidersPage } from '@/pages/InsidersPage'
import { SentimentPage } from '@/pages/SentimentPage'
import { TrendPage } from '@/pages/TrendPage'
import { SearchPage } from '@/pages/SearchPage'
import { OnchainPage } from '@/pages/OnchainPage'

export default function App() {
  return (
    <Routes>
      {/* Public landing page — no sidebar */}
      <Route path="/" element={<LandingPage />} />

      {/* App shell with sidebar */}
      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/themes"    element={<ThemesPage />} />
        <Route path="/options"   element={<OptionsPage />} />
        <Route path="/insiders"  element={<InsidersPage />} />
        <Route path="/sentiment" element={<SentimentPage />} />
        <Route path="/trend"     element={<TrendPage />} />
        <Route path="/search"    element={<SearchPage />} />
        <Route path="/onchain"   element={<OnchainPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
