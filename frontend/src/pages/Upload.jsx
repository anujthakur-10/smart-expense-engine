import { useState } from 'react'
import FileUpload from '../components/FileUpload'
import InvoiceReview from '../components/InvoiceReview'
import DuplicateAlert from '../components/DuplicateAlert'
import { uploadInvoice } from '../services/api'
import toast from 'react-hot-toast'

export default function Upload() {
  const [isProcessing, setIsProcessing] = useState(false)
  const [result, setResult] = useState(null)

  const handleUpload = async (file) => {
    setIsProcessing(true); setResult(null)
    try {
      const data = await uploadInvoice(file)
      setResult(data)
      toast.success(data.message || 'Invoice processed!')
    } catch (err) { toast.error('Upload failed: ' + (err.response?.data?.detail || err.message)) }
    setIsProcessing(false)
  }

  return (
    <div className="main-content">
      <div className="page-header">
        <h1>Upload Invoice</h1>
        <p>Upload a handwritten or printed invoice — AI will extract data automatically</p>
      </div>

      {!result && (
        <div className="card"><FileUpload onUpload={handleUpload} isLoading={isProcessing} /></div>
      )}

      {result && (
        <div>
          <DuplicateAlert fraudCheck={result.fraud_check} />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '12px 0' }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>
              ✓ Invoice #{result.invoice?.id} processed — Review below
            </span>
            <button className="btn btn-secondary" onClick={() => setResult(null)}>Upload Another</button>
          </div>

          {result.gst_details && (
            <div className="card" style={{ marginBottom: 12 }}>
              <h4 style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>GST Summary</h4>
              <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
                <div><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>CGST</span><p style={{ fontWeight: 600, color: 'var(--chart-2)' }}>₹{result.gst_details.cgst || 0}</p></div>
                <div><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>SGST</span><p style={{ fontWeight: 600, color: 'var(--chart-1)' }}>₹{result.gst_details.sgst || 0}</p></div>
                <div><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>IGST</span><p style={{ fontWeight: 600, color: 'var(--chart-4)' }}>₹{result.gst_details.igst || 0}</p></div>
                <div><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Rate</span><p style={{ fontWeight: 600 }}>{result.gst_details.gst_rate || 0}%</p></div>
                <div><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Type</span><p style={{ fontWeight: 600 }}>{result.gst_details.is_inter_state ? 'Inter-State' : 'Intra-State'}</p></div>
              </div>
            </div>
          )}

          <InvoiceReview invoice={result.invoice} ocrResult={result.ocr_result} fraudCheck={result.fraud_check} onSaved={() => setResult(null)} />
        </div>
      )}
    </div>
  )
}
