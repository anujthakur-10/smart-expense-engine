import { useState, useEffect } from 'react'
import { getDashboardSummary, getMonthlyTrend, getGSTSummary, getVendorExpenses, exportInvoicesCSV, triggerSummaryEmail } from '../services/api'
import StatsCard from '../components/StatsCard'
import { IndianRupee, FileText, Users, TrendingUp, Download, Mail } from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import toast from 'react-hot-toast'

const COLORS = ['#10b981', '#3b82f6', '#ef4444', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [monthlyTrend, setMonthlyTrend] = useState([])
  const [gstSummary, setGstSummary] = useState([])
  const [vendorExpenses, setVendorExpenses] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      const [s, t, g, v] = await Promise.all([
        getDashboardSummary(), getMonthlyTrend(), getGSTSummary(), getVendorExpenses(8),
      ])
      setSummary(s); setMonthlyTrend(t); setGstSummary(g); setVendorExpenses(v)
    } catch (err) { toast.error('Failed to load dashboard') }
    setLoading(false)
  }

  const tooltipStyle = {
    background: '#fff', border: '1px solid #e5e7eb',
    borderRadius: 6, fontSize: 13, boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  }

  if (loading) return (
    <div className="main-content">
      <div className="page-header"><h1>Dashboard</h1></div>
      <div className="stats-grid">{[1,2,3,4].map(i => <div key={i} className="card" style={{ height: 100 }} />)}</div>
    </div>
  )

  return (
    <div className="main-content">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1>Dashboard</h1>
          <p>Expense analytics & GST tracking</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button onClick={async () => {
            try {
              await triggerSummaryEmail()
              toast.success('Summary email sent to your inbox!')
            } catch (e) {
              toast.error('Failed to send email')
            }
          }} className="btn btn-secondary">
            <Mail size={16} /> Send Summary
          </button>
          
          <button onClick={async () => {
            try {
              await exportInvoicesCSV()
              toast.success('Export downloaded successfully!')
            } catch (e) {
              toast.error('Failed to export CSV')
            }
          }} className="btn btn-primary">
            <Download size={16} /> Export CSV
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <StatsCard title="Total Expenses" value={`₹${(summary?.total_expenses || 0).toLocaleString('en-IN')}`}
          subtitle="All time" icon={<IndianRupee size={18} />} color="var(--chart-1)" />
        <StatsCard title="GST Paid" value={`₹${(summary?.total_gst_paid || 0).toLocaleString('en-IN')}`}
          subtitle="CGST + SGST + IGST" icon={<TrendingUp size={18} />} color="var(--chart-2)" />
        <StatsCard title="Invoices" value={summary?.total_invoices || 0}
          subtitle={`${summary?.pending_reviews || 0} pending`} icon={<FileText size={18} />} color="var(--chart-4)" />
        <StatsCard title="Vendors" value={summary?.total_vendors || 0}
          subtitle={`${summary?.duplicates_flagged || 0} duplicates`} icon={<Users size={18} />} color="var(--chart-5)" />
      </div>

      <div className="charts-grid">
        {/* Monthly Expense Trend */}
        <div className="card">
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>Monthly Expense Trend</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={monthlyTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} />
              <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`₹${v.toLocaleString('en-IN')}`, 'Amount']} />
              <Line type="monotone" dataKey="total_amount" stroke="#ef4444" strokeWidth={2} dot={{ r: 3, fill: '#ef4444' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* GST Breakdown */}
        <div className="card">
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>GST Breakdown</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={gstSummary}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} />
              <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => `₹${v.toLocaleString('en-IN')}`} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="cgst" fill="#3b82f6" name="CGST" radius={[3,3,0,0]} />
              <Bar dataKey="sgst" fill="#10b981" name="SGST" radius={[3,3,0,0]} />
              <Bar dataKey="igst" fill="#f59e0b" name="IGST" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Vendor Pie */}
      <div className="charts-grid">
        <div className="card">
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>Top Vendors by Expense</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={vendorExpenses} cx="50%" cy="50%" innerRadius={65} outerRadius={100} paddingAngle={2}
                dataKey="total_amount" nameKey="vendor_name"
                label={({ vendor_name, percent }) => `${vendor_name?.substring(0, 12)} (${(percent * 100).toFixed(0)}%)`}
                labelLine={{ stroke: '#d1d5db' }}>
                {vendorExpenses.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => `₹${v.toLocaleString('en-IN')}`} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
