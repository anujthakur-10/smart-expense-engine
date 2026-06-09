import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getInvoices, deleteInvoice } from '../services/api'
import { Search, Trash2, Eye, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Invoices() {
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const navigate = useNavigate()

  useEffect(() => { loadInvoices() }, [statusFilter])

  const loadInvoices = async () => {
    setLoading(true)
    try {
      const params = {}
      if (statusFilter) params.status = statusFilter
      if (search) params.search = search
      setInvoices(await getInvoices(params))
    } catch { toast.error('Failed to load invoices') }
    setLoading(false)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this invoice?')) return
    try { await deleteInvoice(id); toast.success('Deleted'); loadInvoices() }
    catch { toast.error('Delete failed') }
  }

  return (
    <div className="main-content">
      <div className="page-header"><h1>Invoices</h1><p>Search, filter, and manage all uploaded invoices</p></div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <form onSubmit={(e) => { e.preventDefault(); loadInvoices() }} style={{ flex: 1, display: 'flex', gap: 8 }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <Search size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input id="invoice-search" className="input-field" placeholder="Search vendor or invoice number..." value={search} onChange={e => setSearch(e.target.value)} style={{ paddingLeft: 32 }} />
            </div>
            <button type="submit" className="btn btn-primary" style={{ fontSize: 13 }}>Search</button>
          </form>
          <select id="status-filter" className="input-field" value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={{ width: 'auto', minWidth: 130 }}>
            <option value="">All Status</option><option value="pending">Pending</option><option value="reviewed">Reviewed</option><option value="approved">Approved</option>
          </select>
        </div>
      </div>

      <div className="card" style={{ overflow: 'auto' }}>
        {loading ? <div style={{ padding: 48, textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>
        : invoices.length === 0 ? <div style={{ padding: 48, textAlign: 'center', color: 'var(--text-muted)' }}><p>No invoices found</p><p style={{ fontSize: 13, marginTop: 4 }}>Upload your first invoice to get started</p></div>
        : (
          <table className="data-table">
            <thead><tr>
              <th>ID</th><th>Invoice #</th><th>Vendor</th><th>Date</th><th>Amount</th><th>GST</th><th>Status</th><th>Flags</th><th>Actions</th>
            </tr></thead>
            <tbody>
              {invoices.map(inv => (
                <tr key={inv.id}>
                  <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>#{inv.id}</td>
                  <td style={{ fontWeight: 500 }}>{inv.invoice_number || '—'}</td>
                  <td>{inv.vendor_name || '—'}</td>
                  <td style={{ fontSize: 13 }}>{inv.invoice_date || '—'}</td>
                  <td style={{ fontWeight: 600 }}>₹{(inv.total_amount || 0).toLocaleString('en-IN')}</td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>₹{((inv.cgst||0)+(inv.sgst||0)+(inv.igst||0)).toLocaleString('en-IN')}</td>
                  <td><span className={`badge badge-${inv.status}`}>{inv.status}</span></td>
                  <td>{inv.is_duplicate && <span className="badge badge-duplicate"><AlertTriangle size={11} style={{ marginRight: 3 }} />DUP</span>}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button onClick={() => navigate(`/invoices/${inv.id}`)} title="View" style={{ background: 'none', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '3px 6px', cursor: 'pointer', color: 'var(--text-secondary)' }}><Eye size={13} /></button>
                      <button onClick={() => handleDelete(inv.id)} title="Delete" style={{ background: 'none', border: '1px solid #fecaca', borderRadius: 'var(--radius-sm)', padding: '3px 6px', cursor: 'pointer', color: 'var(--status-error)' }}><Trash2 size={13} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
