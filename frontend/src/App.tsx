import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { Dashboard } from './pages/Dashboard'
import { UploadPage } from './pages/UploadPage'
import { AnalysisResult } from './pages/AnalysisResult'
import { ResultsList } from './pages/ResultsList'
import { ReviewQueue } from './pages/ReviewQueue'
import { SettingsPage } from './pages/SettingsPage'
import { Analytics } from './pages/Analytics'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="results" element={<ResultsList />} />
          <Route path="results/:id" element={<AnalysisResult />} />
          <Route path="reviews" element={<ReviewQueue />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="*" element={
            <div className="flex flex-col items-center justify-center py-32 text-center text-muted-foreground">
              <p className="text-6xl font-bold mb-4">404</p>
              <p className="text-xl">Page not found</p>
            </div>
          } />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
