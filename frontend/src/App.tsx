import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'

import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import JobList from './pages/JobList'
import JobDetail from './pages/JobDetail'
import VariantList from './pages/VariantList'
import VariantDetail from './pages/VariantDetail'
import Login from './pages/Login'
import { AuthProvider } from './contexts/AuthContext'

const queryClient = new QueryClient()

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AuthProvider>
          <Router>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/login" element={<Login />} />
                <Route path="/jobs" element={<JobList />} />
                <Route path="/jobs/:jobId" element={<JobDetail />} />
                <Route path="/jobs/:jobId/variants" element={<VariantList />} />
                <Route path="/variants/:variantId" element={<VariantDetail />} />
              </Routes>
            </Layout>
          </Router>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App