// services/api.js — API Service Layer
// Backend FastAPI se communicate karta hai
// Auth token automatically attach hota hai har request mein

import axios from 'axios'
import { supabase } from '../lib/supabase'

// Base URL — development mein Vite proxy handle karega
// Production mein VITE_API_URL environment variable use hoga
const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Request Interceptor — Attach auth token ──────────────────────
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }
  return config
})

// ── Response Interceptor — Handle errors ─────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired — redirect to login
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ══════════════════════════════════════════════════════════════════
// API Functions
// ══════════════════════════════════════════════════════════════════

// ── Upload ───────────────────────────────────────────────────────
export const uploadInvoice = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/api/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ── Invoices CRUD ────────────────────────────────────────────────
export const getInvoices = async (params = {}) => {
  const { data } = await api.get('/api/invoices/', { params })
  return data
}

export const getInvoice = async (id) => {
  const { data } = await api.get(`/api/invoices/${id}`)
  return data
}

export const updateInvoice = async (id, updateData) => {
  const { data } = await api.put(`/api/invoices/${id}`, updateData)
  return data
}

export const deleteInvoice = async (id) => {
  const { data } = await api.delete(`/api/invoices/${id}`)
  return data
}

export const exportInvoicesCSV = async () => {
  const response = await api.get('/api/invoices/export', { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', 'expenses_export.csv')
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// ── Dashboard ────────────────────────────────────────────────────
export const getDashboardSummary = async () => {
  const { data } = await api.get('/api/dashboard/summary')
  return data
}

export const getGSTSummary = async () => {
  const { data } = await api.get('/api/dashboard/gst-summary')
  return data
}

export const getMonthlyTrend = async () => {
  const { data } = await api.get('/api/dashboard/monthly-trend')
  return data
}

export const getVendorExpenses = async (limit = 10) => {
  const { data } = await api.get('/api/dashboard/vendor-expenses', { params: { limit } })
  return data
}

export const triggerSummaryEmail = async () => {
  const { data } = await api.post('/api/dashboard/trigger-summary-email')
  return data
}

// ── Forecast ─────────────────────────────────────────────────────
export const getForecast = async (model = 'xgboost', months = 3, type = 'expenses') => {
  const { data } = await api.get(`/api/forecast/${type}`, {
    params: { model, months_ahead: months },
  })
  return data
}

export const compareModels = async (months = 3, type = 'expenses') => {
  const { data } = await api.get('/api/forecast/compare', {
    params: { months_ahead: months, forecast_type: type },
  })
  return data
}

export default api
