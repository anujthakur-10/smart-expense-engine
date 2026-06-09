import {
  LineChart, Line, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ComposedChart
} from 'recharts'

export default function ForecastChart({ data, title = 'Forecast', color = '#ef4444' }) {
  if (!data || (!data.historical?.length && !data.predictions?.length)) {
    return <div className="card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>Not enough data for forecast.</div>
  }

  const chartData = [
    ...(data.historical || []).map(d => ({ ...d, type: 'historical' })),
    ...(data.predictions || []).map(d => ({ ...d, type: 'prediction' })),
  ]

  const tooltipStyle = { background: '#fff', border: '1px solid #e5e7eb', borderRadius: 6, fontSize: 13, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600 }}>{title}</h3>
        {data.model_used && (
          <span className="badge" style={{ background: '#dbeafe', color: '#1e40af' }}>{data.model_used.toUpperCase()}</span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} />
          <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v, name) => [`₹${v?.toLocaleString('en-IN')}`, name]} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Area dataKey="upper_bound" stroke="none" fill={color} fillOpacity={0.06} name="Upper" />
          <Line dataKey="actual_value" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: '#3b82f6' }} name="Actual" connectNulls={false} />
          <Line dataKey="predicted_value" stroke={color} strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3, fill: color }} name="Predicted" />
        </ComposedChart>
      </ResponsiveContainer>

      {data.metrics && Object.keys(data.metrics).length > 0 && (
        <div style={{ display: 'flex', gap: 32, marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border-light)' }}>
          {data.metrics.mae !== undefined && <div><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>MAE</span><p style={{ fontWeight: 600, fontSize: 14 }}>₹{data.metrics.mae?.toLocaleString('en-IN')}</p></div>}
          {data.metrics.rmse !== undefined && <div><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>RMSE</span><p style={{ fontWeight: 600, fontSize: 14 }}>₹{data.metrics.rmse?.toLocaleString('en-IN')}</p></div>}
          {data.metrics.mape !== undefined && <div><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>MAPE</span><p style={{ fontWeight: 600, fontSize: 14 }}>{data.metrics.mape}%</p></div>}
        </div>
      )}
    </div>
  )
}
