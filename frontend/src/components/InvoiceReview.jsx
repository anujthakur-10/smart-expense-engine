import { useState } from 'react'
import { updateInvoice } from '../services/api'
import { Check, Edit3, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function InvoiceReview({ invoice, ocrResult, fraudCheck, onSaved }) {
  const [formData, setFormData] = useState({
    invoice_number: invoice?.invoice_number || '',
    vendor_name: invoice?.vendor_name || '',
    invoice_date: invoice?.invoice_date || '',
    subtotal: invoice?.subtotal || 0,
    cgst: invoice?.cgst || 0, sgst: invoice?.sgst || 0, igst: invoice?.igst || 0,
    total_amount: invoice?.total_amount || 0,
    gst_rate: invoice?.gst_rate || 18,
    vendor_gstin: invoice?.vendor_gstin || '',
    category: invoice?.category || '',
    notes: invoice?.notes || '',
  })
  const [saving, setSaving] = useState(false)

  const handleChange = (f, v) => setFormData(p => ({ ...p, [f]: v }))

  const handleSave = async (status = 'reviewed') => {
    setSaving(true)
    try {
      await updateInvoice(invoice.id, { ...formData, status })
      toast.success(`Invoice ${status === 'approved' ? 'approved' : 'saved'}!`)
      if (onSaved) onSaved()
    } catch (err) { toast.error('Save failed') }
    setSaving(false)
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
      {/* Left: Image + OCR */}
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>Original Invoice</h3>
        {invoice?.file_url && (
          <img src={invoice.file_url} alt="Invoice" style={{ width: '100%', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }} />
        )}
        <details style={{ marginTop: 8 }}>
          <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: 13 }}>
            Raw OCR Text (confidence: {(ocrResult?.confidence * 100 || 0).toFixed(1)}%)
          </summary>
          <pre style={{ marginTop: 6, padding: 10, background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)',
            fontSize: 11, whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', maxHeight: 160, overflow: 'auto' }}>
            {ocrResult?.raw_text || invoice?.raw_ocr_text || 'No OCR text'}
          </pre>
        </details>
      </div>

      {/* Right: Form */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600 }}><Edit3 size={15} style={{ marginRight: 6, verticalAlign: 'middle' }} />Review & Edit</h3>
          <div style={{ display: 'flex', gap: 6 }}>
            <button className="btn btn-secondary" onClick={() => handleSave('reviewed')} disabled={saving} style={{ fontSize: 12, padding: '5px 10px' }}>Save Draft</button>
            <button className="btn btn-primary" onClick={() => handleSave('approved')} disabled={saving} style={{ fontSize: 12, padding: '5px 10px' }}><Check size={13} /> Approve</button>
          </div>
        </div>

        {fraudCheck?.is_duplicate && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius-sm)', padding: '8px 12px', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <AlertTriangle size={15} color="var(--status-error)" />
            <span style={{ fontSize: 13, color: '#991b1b' }}>{fraudCheck.message}</span>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div><label>Invoice Number</label><input className="input-field" value={formData.invoice_number} onChange={e => handleChange('invoice_number', e.target.value)} /></div>
          <div><label>Vendor Name</label><input className="input-field" value={formData.vendor_name} onChange={e => handleChange('vendor_name', e.target.value)} /></div>
          <div><label>Invoice Date</label><input className="input-field" type="date" value={formData.invoice_date} onChange={e => handleChange('invoice_date', e.target.value)} /></div>
          <div><label>Category</label>
            <select className="input-field" value={formData.category} onChange={e => handleChange('category', e.target.value)}>
              <option value="">Select</option>
              <option value="Groceries">Groceries</option><option value="Office Supplies">Office Supplies</option>
              <option value="Electronics">Electronics</option><option value="Transport">Transport</option>
              <option value="IT Services">IT Services</option><option value="Food">Food</option><option value="Other">Other</option>
            </select>
          </div>
          <div><label>Subtotal (₹)</label><input className="input-field" type="number" step="0.01" value={formData.subtotal} onChange={e => handleChange('subtotal', parseFloat(e.target.value) || 0)} /></div>
          <div><label>GST Rate (%)</label>
            <select className="input-field" value={formData.gst_rate} onChange={e => handleChange('gst_rate', parseFloat(e.target.value))}>
              <option value={0}>0%</option><option value={5}>5%</option><option value={12}>12%</option><option value={18}>18%</option><option value={28}>28%</option>
            </select>
          </div>
          <div><label>CGST (₹)</label><input className="input-field" type="number" step="0.01" value={formData.cgst} onChange={e => handleChange('cgst', parseFloat(e.target.value) || 0)} /></div>
          <div><label>SGST (₹)</label><input className="input-field" type="number" step="0.01" value={formData.sgst} onChange={e => handleChange('sgst', parseFloat(e.target.value) || 0)} /></div>
          <div><label>IGST (₹)</label><input className="input-field" type="number" step="0.01" value={formData.igst} onChange={e => handleChange('igst', parseFloat(e.target.value) || 0)} /></div>
          <div><label>Total (₹)</label><input className="input-field" type="number" step="0.01" value={formData.total_amount} onChange={e => handleChange('total_amount', parseFloat(e.target.value) || 0)} style={{ fontWeight: 600 }} /></div>
          <div style={{ gridColumn: '1/-1' }}><label>Vendor GSTIN</label><input className="input-field" value={formData.vendor_gstin} onChange={e => handleChange('vendor_gstin', e.target.value)} placeholder="e.g. 09AAACH7409R1ZZ" /></div>
          <div style={{ gridColumn: '1/-1' }}><label>Notes</label><textarea className="input-field" rows={2} value={formData.notes} onChange={e => handleChange('notes', e.target.value)} placeholder="Corrections or notes..." /></div>
        </div>
      </div>
    </div>
  )
}
