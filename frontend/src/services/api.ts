import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/api/auth/token', new URLSearchParams({ username, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  
  register: (data: { email: string; username: string; password: string }) =>
    api.post('/api/auth/register', data),
  
  getUser: () => api.get('/api/auth/user'),
  
  logout: () => api.post('/api/auth/logout'),
}

// Jobs API
export const jobsAPI = {
  create: (formData: FormData) =>
    api.post('/api/jobs/create', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  
  list: (params?: { page?: number; per_page?: number; status?: string }) =>
    api.get('/api/jobs/', { params }),
  
  get: (jobId: string) => api.get(`/api/jobs/${jobId}`),
  
  getById: (jobId: string) => api.get(`/api/jobs/${jobId}`).then(res => res.data),
  
  cancel: (jobId: string) => api.delete(`/api/jobs/${jobId}`),
}

// Variants API
export const variantsAPI = {
  list: (jobId: string, params?: any) =>
    api.get(`/api/variants/job/${jobId}`, { params }),
  
  get: (variantId: number) => api.get(`/api/variants/${variantId}`),
  
  getById: (variantId: string) => api.get(`/api/variants/${variantId}`).then(res => res.data),
  
  getIGVData: (variantId: number) => api.get(`/api/variants/${variantId}/igv`),
}

// Reports API
export const reportsAPI = {
  generate: (jobId: string, format: string) =>
    api.post(`/api/reports/${jobId}`, { format }),
  
  download: (jobId: string, filename: string) =>
    api.get(`/api/reports/download/${jobId}/${filename}`, {
      responseType: 'blob',
    }),
}

// WebSocket connection
export const createWebSocket = (jobId: string) => {
  const wsUrl = `${API_URL.replace('http', 'ws')}/ws/jobs/${jobId}`
  return new WebSocket(wsUrl)
}

export default api