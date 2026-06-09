import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, Loader } from 'lucide-react'

export default function FileUpload({ onUpload, isLoading }) {
  const [preview, setPreview] = useState(null)

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0]
    if (!file) return
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = () => setPreview(reader.result)
      reader.readAsDataURL(file)
    } else { setPreview(null) }
    if (onUpload) onUpload(file)
  }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/jpeg': ['.jpg','.jpeg'], 'image/png': ['.png'], 'image/webp': ['.webp'], 'application/pdf': ['.pdf'] },
    maxFiles: 1, maxSize: 10 * 1024 * 1024, disabled: isLoading,
  })

  return (
    <div>
      <div {...getRootProps()} style={{
        border: `2px dashed ${isDragActive ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 'var(--radius-md)', padding: '48px 24px', textAlign: 'center',
        cursor: isLoading ? 'not-allowed' : 'pointer',
        background: isDragActive ? 'var(--accent-light)' : '#fafafa',
        transition: 'all 0.15s', opacity: isLoading ? 0.6 : 1,
      }}>
        <input {...getInputProps()} id="invoice-upload-input" />
        {isLoading ? (
          <div>
            <Loader size={36} style={{ color: 'var(--accent)', animation: 'spin 1s linear infinite', margin: '0 auto' }} />
            <p style={{ fontWeight: 600, marginTop: 12, fontSize: 15 }}>Processing Invoice...</p>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>OCR + GST + Fraud check running</p>
          </div>
        ) : (
          <div>
            <div style={{
              width: 48, height: 48, borderRadius: 'var(--radius-md)',
              background: 'var(--accent)', display: 'flex',
              alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px',
            }}>
              <Upload size={22} color="white" />
            </div>
            <p style={{ fontWeight: 600, fontSize: 15 }}>
              {isDragActive ? 'Drop here!' : 'Drag & drop invoice'}
            </p>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
              JPEG, PNG, WebP, PDF (multi-page) • Max 10MB
            </p>
            <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 4 }}>Hindi + English supported</p>
          </div>
        )}
      </div>
      {preview && !isLoading && (
        <div style={{ marginTop: 12, position: 'relative', display: 'inline-block' }}>
          <img src={preview} alt="Preview" style={{
            maxWidth: '100%', maxHeight: 240, borderRadius: 'var(--radius-md)', border: '1px solid var(--border)',
          }} />
          <button onClick={(e) => { e.stopPropagation(); setPreview(null) }}
            style={{ position: 'absolute', top: 6, right: 6, background: 'rgba(0,0,0,0.6)', border: 'none',
              borderRadius: 'var(--radius-full)', padding: 3, cursor: 'pointer', color: 'white' }}>
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  )
}
