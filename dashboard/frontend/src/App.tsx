import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Layout } from './components/Layout'
import { FiltersProvider } from './context/Filters'
import { Compare } from './pages/Compare'
import { DappDetail, DappsList } from './pages/Dapps'
import { Ecosystem } from './pages/Ecosystem'
import { Overview } from './pages/Overview'
import { Schema } from './pages/Schema'
import { Tables } from './pages/Tables'
import { Variations } from './pages/Variations'

const qc = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <FiltersProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<ErrorBoundary><Overview /></ErrorBoundary>} />
              <Route path="compare" element={<ErrorBoundary><Compare /></ErrorBoundary>} />
              <Route path="dapps" element={<ErrorBoundary><DappsList /></ErrorBoundary>} />
              <Route path="dapps/:slug" element={<ErrorBoundary><DappDetail /></ErrorBoundary>} />
              <Route path="ecosystem" element={<ErrorBoundary><Ecosystem /></ErrorBoundary>} />
              <Route path="variations" element={<ErrorBoundary><Variations /></ErrorBoundary>} />
              <Route path="schema" element={<ErrorBoundary><Schema /></ErrorBoundary>} />
              <Route path="tables" element={<ErrorBoundary><Tables /></ErrorBoundary>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </FiltersProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
