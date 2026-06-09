import { useState, useEffect } from 'react'
import { getForecast, compareModels } from '../services/api'
import ForecastChart from '../components/ForecastChart'
import StatsCard from '../components/StatsCard'
import { TrendingUp, Cpu, Zap, BarChart3 } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Predictions() {
  const [model, setModel] = useState('xgboost')
  const [months, setMonths] = useState(3)
  const [forecastType, setForecastType] = useState('expenses')
  const [forecastData, setForecastData] = useState(null)
  const [comparison, setComparison] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadForecast() }, [model, months, forecastType])

  const loadForecast = async () => {
    setLoading(true)
    try { setForecastData(await getForecast(model, months, forecastType)) }
    catch (err) { toast.error('Forecast failed') }
    setLoading(false)
  }

  const loadComparison = async () => {
    try { setComparison(await compareModels(months, forecastType)); toast.success('Comparison loaded') }
    catch { toast.error('Comparison failed') }
  }

  const next = forecastData?.predictions?.[0]

  return (
    <div className="main-content">
      <div className="page-header"><h1>Predictions</h1><p>AI-powered expense forecasting — Prophet, XGBoost, LightGBM</p></div>

      {/* Controls */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div><label>Model</label>
            <select className="input-field" value={model} onChange={e => setModel(e.target.value)} style={{ minWidth: 150 }}>
              <option value="xgboost">XGBoost (Best)</option><option value="lightgbm">LightGBM</option><option value="prophet">Prophet</option>
            </select>
          </div>
          <div><label>Period</label>
            <select className="input-field" value={months} onChange={e => setMonths(parseInt(e.target.value))} style={{ minWidth: 120 }}>
              <option value={1}>1 Month</option><option value={3}>3 Months</option><option value={6}>6 Months</option><option value={12}>12 Months</option>
            </select>
          </div>
          <div><label>Type</label>
            <select className="input-field" value={forecastType} onChange={e => setForecastType(e.target.value)} style={{ minWidth: 120 }}>
              <option value="expenses">Expenses</option><option value="gst">GST Liability</option>
            </select>
          </div>
          <button className="btn btn-secondary" onClick={loadComparison}><BarChart3 size={14} /> Compare All</button>
        </div>
      </div>

      {/* Stats */}
      {next && (
        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          <StatsCard title="Next Month Forecast" value={`₹${next.predicted_value?.toLocaleString('en-IN')}`} subtitle={next.date} icon={<TrendingUp size={18} />} color="var(--chart-3)" />
          <StatsCard title="Model" value={forecastData?.model_used?.toUpperCase()} subtitle={forecastData?.message?.substring(0, 35)} icon={<Cpu size={18} />} color="var(--chart-2)" />
          {forecastData?.metrics?.mae !== undefined && (
            <StatsCard title="MAE" value={`₹${forecastData.metrics.mae?.toLocaleString('en-IN')}`} subtitle={`MAPE: ${forecastData.metrics.mape || 0}%`} icon={<Zap size={18} />} color="var(--chart-1)" />
          )}
        </div>
      )}

      {/* Chart */}
      {loading ? <div className="card" style={{ height: 360 }} />
        : <ForecastChart data={forecastData} title={`${forecastType === 'expenses' ? 'Expense' : 'GST'} Forecast — ${model.toUpperCase()}`}
            color={model === 'prophet' ? '#3b82f6' : model === 'lightgbm' ? '#10b981' : '#ef4444'} />}

      {/* Comparison */}
      {comparison && (
        <div style={{ marginTop: 24 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Model Comparison</h2>

          {comparison.comparison_metrics && Object.keys(comparison.comparison_metrics).length > 0 && (
            <div className="card" style={{ marginBottom: 16, overflow: 'auto' }}>
              <table className="data-table">
                <thead><tr><th>Model</th><th>MAE (₹)</th><th>RMSE (₹)</th><th>MAPE (%)</th><th></th></tr></thead>
                <tbody>
                  {Object.entries(comparison.comparison_metrics).map(([name, m]) => (
                    <tr key={name}>
                      <td style={{ fontWeight: 600 }}>{name.toUpperCase()}</td>
                      <td>₹{m.mae?.toLocaleString('en-IN')}</td>
                      <td>₹{m.rmse?.toLocaleString('en-IN')}</td>
                      <td>{m.mape}%</td>
                      <td>{name === comparison.best_model && <span className="badge badge-approved">BEST</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="charts-grid">
            {comparison.xgboost && <ForecastChart data={comparison.xgboost} title="XGBoost" color="#ef4444" />}
            {comparison.lightgbm && <ForecastChart data={comparison.lightgbm} title="LightGBM" color="#10b981" />}
            {comparison.prophet && <ForecastChart data={comparison.prophet} title="Prophet" color="#3b82f6" />}
          </div>
        </div>
      )}
    </div>
  )
}
