import { useState, useEffect } from 'react'

const RSIMonitorPanel = () => {
  const [rsiData, setRsiData] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [error, setError] = useState(null)

  // Helper to get auth headers
  const getAuthHeaders = () => {
    const token = localStorage.getItem('authToken');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    };
  };

  const fetchRSISnapshot = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/market/rsi-snapshot', {
        headers: getAuthHeaders()
      })
      
      if (!response.ok) {
        throw new Error('Failed to fetch RSI data')
      }
      
      const data = await response.json()
      setRsiData(data)
      setLastUpdate(new Date())
      setError(null)
    } catch (err) {
      console.error('RSI Snapshot error:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Auto-refresh every 5 seconds
  useEffect(() => {
    fetchRSISnapshot()
    const interval = setInterval(fetchRSISnapshot, 5000)
    return () => clearInterval(interval)
  }, [])

  const getRSIStatus = (rsi) => {
    if (rsi <= 30) return { text: 'Oversold', color: 'var(--success)' }
    if (rsi <= 40) return { text: 'Buy Zone', color: '#EAB308' } // Yellow
    if (rsi <= 59) return { text: 'Neutral', color: 'var(--text-sec)' }
    if (rsi <= 69) return { text: 'Sell Zone', color: '#3B82F6' } // Blue
    return { text: 'Overbought', color: 'var(--danger)' }
  }

  return (
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <h3 style={{ fontSize: '1rem', color: 'var(--accent-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            RSI Monitor
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {loading && <div className="spinner" style={{ width: '12px', height: '12px', border: '2px solid var(--text-sec)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {!error && (
        <div className="rsi-list-container">
          {rsiData.map((item) => {
            const status = getRSIStatus(item.rsi)
            return (
              <div key={item.symbol} className="rsi-row">
                 {/* Symbol */}
                 <div style={{ width: '45px', fontWeight: '900', fontSize: '13px', color: '#EAECEF' }}>
                    {item.symbol.replace('USDT', '')}
                 </div>
                 
                 {/* Progress Bar */}
                 <div className="progress-bg">
                    <div className="progress-fill" style={{ width: `${item.rsi}%`, background: status.color, color: status.color }} />
                 </div>

                 {/* Value & Status */}
                 <div style={{ textAlign: 'right', minWidth: '65px' }}>
                    <div style={{ fontWeight: '950', color: status.color, fontSize: '14px', textShadow: `0 0 10px ${status.color}44` }}>{item.rsi.toFixed(1)}</div>
                    <div style={{ fontSize: '10px', color: 'var(--text-sec)', textTransform: 'uppercase', fontWeight: '700' }}>{status.text}</div>
                 </div>
              </div>
            )
          })}
          {rsiData.length === 0 && !loading && (
             <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '10px' }}>No Data</div>
          )}
        </div>
      )}
    </div>
  )
}

export default RSIMonitorPanel
