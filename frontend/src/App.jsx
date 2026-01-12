import { useState, useEffect, useRef } from 'react'
import MarketChart from './MarketChart'
import Login from './components/Login'
import TradeModal from './components/TradeModal'
import StatusCard from './components/StatusCard'
import StatisticsCard from './components/StatisticsCard'
import TradeHistory from './components/TradeHistory'
import Header from './components/Header'
import ActionCards from './components/ActionCards'
import SettingsPanel, { MarketSettings, RiskSettings, StrategySettings, ExtraSettings } from './components/SettingsPanel'
import RSIMonitorPanel from './components/RSIMonitorPanel'
import PredictiveDashboard from './components/PredictiveDashboard'
import NoviceProSwitch from './components/common/NoviceProSwitch'
import ChartHelp from './components/common/ChartHelp'
import LiveMarket from './components/LiveMarket'



const THEME_KEY = 'binance_bot_theme';

function App() {
  // Global Accordion State (Multiple can be open)
  const [openPanels, setOpenPanels] = useState({
    live: true,
    status: true,
    stats: true,
    predictive: true,
    market: false,
    risk: false,
    strategy: false,
    telegram: false,
    converter: false
  }); 

  const togglePanel = (panelName) => {
    setOpenPanels(prev => ({
      ...prev,
      [panelName]: !prev[panelName]
    }));
  };

  const [botStatus, setBotStatus] = useState({ 
    is_running: false, 
    symbol: '', 
    mode: 'DISCONNECTED',
    price: 0,
    balance: 0,
    crypto_balance: 0,
    pnl: 0,
    daily_pnl: 0,
    rsi: 0,
    history: [],
    trades: [],
    settings: {
      min_balance: 0,
      trade_qty: 0.001,
      buy_rsi: 30,
      sell_rsi: 70,
      ema_length: 200,
      macd_fast: 12,
      macd_slow: 26,
      macd_signal: 9,
      stop_loss_pct: 0,
      take_profit_pct: 0,
      tg_token: '',
      tg_chat_id: '',
      trade_qty_type: 'base',
      testnet_commission_pct: 0.1,
      dca_step_pct: 1.0
    },
    prediction: {
      market_score: 50,
      expected_move: { min: 0, max: 0 },
      projection: [],
      traps: [],
      zones: { target: 0, support: 0 }
    }
  })
  const [isStopLossOpen, setIsStopLossOpen] = useState(true)
  
  // Use refs to store previous values (updates synchronously)
  const prevPriceRef = useRef(0)
  const prevBalanceRef = useRef(0)
  const lastTradeRef = useRef(null)
  const lastSymbolRef = useRef('')
  
  const [priceChange, setPriceChange] = useState(0)
  const [balanceChange, setBalanceChange] = useState(0)
  const [loading, setLoading] = useState(true)
  const [isUpdating, setIsUpdating] = useState(false)
  const [isProMode, setProMode] = useState(() => localStorage.getItem('pro_mode') === 'true') 
  
  const handleProToggle = () => {
    setProMode(prev => {
      const newVal = !prev;
      localStorage.setItem('pro_mode', newVal);
      return newVal;
    });
  };
  const [error, setError] = useState(null)
  
  // Modal States
  const [showTradeModal, setShowTradeModal] = useState(false)
  const [showSniperModal, setShowSniperModal] = useState(false)
  const [showTrailingModal, setShowTrailingModal] = useState(false)
  const [tradeModalType, setTradeModalType] = useState('buy')
  const [tradeAmount, setTradeAmount] = useState(0)
  const [tradeAmountUSDT, setTradeAmountUSDT] = useState(0)
  const [notifications, setNotifications] = useState([])
  const [historyFilter, setHistoryFilter] = useState('all')
  const [showTrades, setShowTrades] = useState(false) // Keep this separate as it's a bottom panel

  /* Theme State */
  const [theme, setTheme] = useState(() => localStorage.getItem(THEME_KEY) || 'dark');

  const toggleTheme = () => {
    setTheme(prev => {
      const newTheme = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem(THEME_KEY, newTheme);
      return newTheme;
    });
  };

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  /* Currency State */
  const [currency, setCurrency] = useState('USDT');
  const [exchangeRate, setExchangeRate] = useState(1);
  const [currencyOptions] = useState(['USDT', 'COP']);
  const [tickers, setTickers] = useState({});
  const [convertAmount, setConvertAmount] = useState(10);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  // Helper to get auth headers
  const getAuthHeaders = () => {
    const token = localStorage.getItem('authToken');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    };
  };

  // Check authentication on mount
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('user');
    if (token && user) {
      setIsAuthenticated(true);
      setCurrentUser(JSON.parse(user));
    }
  }, []);

  useEffect(() => {
    // Fetch COP rate on mount
    fetch('https://api.exchangerate-api.com/v4/latest/USD')
      .then(res => res.json())
      .then(data => {
        if (data && data.rates && data.rates.COP) {
            localStorage.setItem('cop_rate', data.rates.COP);
        }
      })
      .catch(err => console.error("Failed to fetch rates", err));
  }, []);

  // Helper to format money based on selected currency
  const formatMoney = (amountUSD, fractionDigits = 2) => {
    if (amountUSD === undefined || amountUSD === null) return '---';
    
    let value = amountUSD;
    let symbol = '$';
    let code = 'USDT';

    if (currency === 'COP') {
      const rate = parseFloat(localStorage.getItem('cop_rate')) || 4200;
      value = amountUSD * rate;
      symbol = '$';
      code = 'COP';
      fractionDigits = 0;
    }

    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: code === 'COP' ? 'COP' : 'USD', 
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits
    }).format(value);
  }

  // Effect to fetch tickers (prices for other coins)
  useEffect(() => {
    if (!isAuthenticated) return;
    const fetchTickers = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/tickers', {
          headers: getAuthHeaders()
        });
        const data = await response.json();
        setTickers(data);
      } catch (err) {
        console.error("Failed to fetch tickers", err);
      }
    };
    fetchTickers();
    const interval = setInterval(fetchTickers, 30000); // Polling every 30s
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  // Effect to re-fetch status
  useEffect(() => {
    if (!isAuthenticated) return;
    fetchStatus()
    const interval = setInterval(fetchStatus, 3000) 
    return () => clearInterval(interval)
  }, [isAuthenticated])

  const isConnected = isAuthenticated && botStatus.mode !== 'DISCONNECTED'

  const fetchStatus = () => {
    fetch('/api/status', {
      headers: getAuthHeaders()
    })
      .then(res => {
        if (res.status === 401) {
          // Session expired, clear auth
          localStorage.removeItem('authToken');
          localStorage.removeItem('user');
          setIsAuthenticated(false);
          throw new Error('Session expired');
        }
        if (!res.ok) throw new Error('Network response was not ok');
        return res.json();
      })
      .then(data => {
        if (!data || typeof data !== 'object') return;

        // If symbol changed, reset price comparison refs immediately to prevent fake % drops
        if (data.symbol && lastSymbolRef.current && data.symbol !== lastSymbolRef.current) {
          prevPriceRef.current = 0; // Force reset
          prevBalanceRef.current = 0;
          setPriceChange(0);
          setBalanceChange(0);
        }
        if (data.symbol) lastSymbolRef.current = data.symbol;
        
        // Only calculate changes if we have a valid previous price and the same symbol
        if (data.price > 0 && prevPriceRef.current > 0 && data.symbol === lastSymbolRef.current) {
          const change = ((data.price - prevPriceRef.current) / prevPriceRef.current) * 100
          setPriceChange(change)
        }
        
        // Track current price for next comparison
        if (data.price > 0) prevPriceRef.current = data.price
        
        // Same for balance
        if (data.balance > 0 && prevBalanceRef.current > 0 && data.symbol === lastSymbolRef.current) {
          const balChange = ((data.balance - prevBalanceRef.current) / prevBalanceRef.current) * 100
          setBalanceChange(balChange)
        }
        if (data.balance > 0) prevBalanceRef.current = data.balance
        
        const safeData = {
          ...data,
          history: Array.isArray(data.history) ? data.history : [],
          trades: Array.isArray(data.trades) ? data.trades : []
        };

        // Detect new automatic trades for notifications
        if (safeData.trades.length > 0) {
          const latestTrade = safeData.trades[0];
          if (lastTradeRef.current && lastTradeRef.current.time !== latestTrade.time) {
            // Only notify if it's NOT a manual trade (those have their own notification in confirmTrade)
            if (!latestTrade.type.includes('MANUAL')) {
              const isBuy = latestTrade.type.includes('BUY');
              const tradeType = isBuy ? 'Compra' : 'Venta';
              const emoji = isBuy ? '🚀' : '💰';
              const symbol = latestTrade.symbol?.replace('USDT', '') || 'Cripto';
              addNotification('success', `${emoji} ${tradeType} Automática: ${latestTrade.qty} ${symbol}`);
            }
          }
          lastTradeRef.current = latestTrade;
        }

        setBotStatus(prev => ({ ...prev, ...safeData }));
        setLoading(false);
        setError(null);
      })
      .catch(err => {
        console.error('Fetch error:', err);
        if (err.message === 'Session expired') {
          setError('Sesión expirada. Por favor inicia sesión nuevamente.');
        } else {
          setError('Failed to connect to backend bot. Ensure the Python server is running.');
        }
        setLoading(false);
      })
  }

  const handleStart = () => {
    fetch('/api/start', { method: 'POST', headers: getAuthHeaders() })
      .then(res => res.json())
      .then(() => fetchStatus())
  }

  const handleStop = () => {
    fetch('/api/stop', { method: 'POST', headers: getAuthHeaders() })
      .then(res => res.json())
      .then(() => fetchStatus())
  }

  const updateSettings = async (newSettings) => {
    setIsUpdating(true);
    try {
      const resp = await fetch('/api/settings', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(newSettings)
      });
      const data = await resp.json();
      if (resp.ok) {
        addNotification('success', 'Configuración actualizada');
        fetchStatus();
      } else {
        addNotification('error', data.detail || 'Error al actualizar');
      }
    } catch (err) {
      addNotification('error', 'Error de conexión');
    } finally {
      setIsUpdating(false);
    }
  }

  const handleLogout = () => {
    fetch('/api/auth/logout', { method: 'POST', headers: getAuthHeaders() })
      .then(res => res.json())
      .then(() => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
        setIsAuthenticated(false);
        setCurrentUser(null);
        setBotStatus(prev => ({ ...prev, mode: 'DISCONNECTED' }))
      })
      .catch(() => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
        setIsAuthenticated(false);
        setCurrentUser(null);
      })
  }

  // Notification functions
  const addNotification = (type, message) => {
    const id = Date.now()
    setNotifications(prev => [...prev, { id, type, message }])
    setTimeout(() => {
      removeNotification(id)
    }, 4000)
  }

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(notif => notif.id !== id))
  }

  const handleManualBuy = () => {
    setTradeModalType('buy')
    setTradeAmount('')
    setTradeAmountUSDT('')
    setShowTradeModal(true)
  }

  const handleManualSell = () => {
    setTradeModalType('sell')
    setTradeAmount('')
    setTradeAmountUSDT('')
    setShowTradeModal(true)
  }

  const confirmTrade = () => {
    const qty = parseFloat(tradeAmount)
    if (!qty || qty <= 0) {
      addNotification('error', 'Por favor ingresa una cantidad válida')
      return
    }

    const tradeType = tradeModalType === 'buy' ? 'Compra' : 'Venta'
    const endpoint = tradeModalType === 'buy' ? '/api/buy' : '/api/sell'
    
    setIsSubmitting(true)
    fetch(endpoint, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ quantity: qty })
    })
      .then(res => res.json())
      .then((data) => {
        setIsSubmitting(false)
        if (data.status === 'success') {
          const symbol = botStatus.symbol?.replace('USDT', '') || 'Cripto'
          addNotification('success', `${tradeType} exitosa: ${qty} ${symbol}`)
        } else {
          addNotification('error', data.message || `Error en ${tradeType.toLowerCase()}`)
        }
        fetchStatus()
        setShowTradeModal(false)
      })
      .catch(err => {
        setIsSubmitting(false)
        addNotification('error', `Error al ejecutar ${tradeType.toLowerCase()}: ${err.message}`)
      })
  }

  const handleResetPosition = async () => {
    if (!window.confirm('¿Estás seguro de reiniciar la posición? Esto pondrá a 0 el precio de entrada y la cantidad acumulada sin vender nada.')) return;
    try {
      const resp = await fetch('/api/reset', { method: 'POST', headers: getAuthHeaders() });
      if (resp.ok) {
        addNotification('success', 'Posición reiniciada');
        fetchStatus();
      }
    } catch (err) {
      addNotification('error', 'Error al reiniciar posición');
    }
  }

  const handleResetPnL = async () => {
    if (!window.confirm('¿Estás seguro de reiniciar el PnL? Esto borrará el historial de trades y reseteará el balance inicial.')) return;
    try {
      const resp = await fetch('/api/reset_pnl', { method: 'POST', headers: getAuthHeaders() });
      if (resp.ok) {
        addNotification('success', 'PnL e Historial reiniciados');
        fetchStatus();
      }
    } catch (err) {
      addNotification('error', 'Error al reiniciar PnL');
    }
  }

  const updateTradeAmount = (newAmount) => {
    setTradeAmount(newAmount)
    if (newAmount && !isNaN(newAmount)) {
      setTradeAmountUSDT((parseFloat(newAmount) * botStatus.price).toFixed(2))
    } else {
      setTradeAmountUSDT('')
    }
  }

  const updateTradeAmountUSDT = (newAmountUSDT) => {
    setTradeAmountUSDT(newAmountUSDT)
    if (newAmountUSDT && !isNaN(newAmountUSDT) && botStatus.price > 0) {
      setTradeAmount((parseFloat(newAmountUSDT) / botStatus.price).toFixed(8))
    } else {
      setTradeAmount('')
    }
  }

  const handleLoginSuccess = () => {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('user');
    if (token && user) {
      setIsAuthenticated(true);
      setCurrentUser(JSON.parse(user));
    }
  };

  if (!isConnected) {
    return <Login onLoginSuccess={handleLoginSuccess} />
  }

  return (
    <div className="container">
      <TradeModal 
        showTradeModal={showTradeModal}
        setShowTradeModal={setShowTradeModal}
        tradeModalType={tradeModalType}
        botStatus={botStatus}
        tradeAmount={tradeAmount}
        updateTradeAmount={updateTradeAmount}
        tradeAmountUSDT={tradeAmountUSDT}
        updateTradeAmountUSDT={updateTradeAmountUSDT}
        confirmTrade={confirmTrade}
        isSubmitting={isSubmitting}
        error={error}
        formatMoney={formatMoney}
      />

      {/* Sniper Mode Risk Warning Modal */}
      {showSniperModal && (
        <div className="modal-overlay" onClick={() => setShowSniperModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ border: '2px solid #ff9800' }}>
            <div className="modal-header">
              <h3 style={{ color: '#ff9800' }}>⚠️ ADVERTENCIA DE RIESGO</h3>
              <button className="close-btn" onClick={() => setShowSniperModal(false)}>×</button>
            </div>
            
            <div className="modal-body" style={{ textAlign: 'center' }}>
              <p style={{ fontSize: '1.1rem', marginBottom: '15px' }}>
                Estás a punto de activar el <b>Sniper Mode</b>.
              </p>
              <ul style={{ textAlign: 'left', background: 'rgba(255, 152, 0, 0.1)', padding: '15px 25px', borderRadius: '8px', border: '1px solid rgba(255, 152, 0, 0.3)' }}>
                <li>🚀 <b>All-In:</b> Cada compra usará el <b>98%</b> de tu saldo disponible.</li>
                <li>🛡️ <b>Sin DCA:</b> Si el precio baja, el bot <b>NO</b> comprará más para promediar.</li>
                <li>🎯 <b>Alto Riesgo:</b> Operarás con una sola "bala".</li>
              </ul>
            </div>

            <div className="modal-footer">
              <button className="cancel-btn" onClick={() => setShowSniperModal(false)}>Cancelar</button>
              <button 
                className="confirm-btn" 
                style={{ background: '#ff9800', color: 'black', fontWeight: 'bold' }}
                onClick={() => {
                  updateSettings({ sniper_mode: true });
                  setShowSniperModal(false);
                  addNotification('success', 'Sniper Mode ACTIVADO 🎯');
                }}
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Trailing Stop Info Modal */}
      {showTrailingModal && (
        <div className="modal-overlay" onClick={() => setShowTrailingModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ border: '2px solid #2ea043' }}>
            <div className="modal-header">
              <h3 style={{ color: '#2ea043' }}>🚀 ACTIVAR TRAILING STOP</h3>
              <button className="close-btn" onClick={() => setShowTrailingModal(false)}>×</button>
            </div>
            
            <div className="modal-body" style={{ textAlign: 'center' }}>
              <ul style={{ textAlign: 'left', background: 'rgba(46, 160, 67, 0.1)', padding: '15px 25px', borderRadius: '8px', border: '1px solid rgba(46, 160, 67, 0.3)' }}>
                <li>📈 <b>Persigue el Precio:</b> El Stop Loss sube con el precio.</li>
                <li>💰 <b>Maximiza Ganancias:</b> Salida dinámica.</li>
              </ul>
            </div>

            <div className="modal-footer">
              <button className="cancel-btn" onClick={() => setShowTrailingModal(false)}>Cancelar</button>
              <button 
                className="confirm-btn" 
                style={{ background: '#2ea043', color: 'white', fontWeight: 'bold' }}
                onClick={() => {
                  updateSettings({ trailing_enabled: true });
                  setShowTrailingModal(false);
                  addNotification('success', 'Trailing Stop ACTIVADO 🚀');
                }}
              >
                Activar
              </button>
            </div>
          </div>
        </div>
      )}
      
      <Header 
        currency={currency} 
        setCurrency={setCurrency} 
        botStatus={botStatus} 
        handleLogout={handleLogout}
        theme={theme}
        toggleTheme={toggleTheme} 
        isProMode={isProMode}
        handleProToggle={handleProToggle}
      />

      {/* New Top Status Bar */}
      <StatusCard botStatus={botStatus} formatMoney={formatMoney} />

      {botStatus.mode === 'REAL' && (
        <div className="live-warning-banner">
          ⚠️ EJECUTANDO EN CUENTA REAL - FONDOS REALES EN RIESGO ⚠️
        </div>
      )}

      <ActionCards 
        botStatus={botStatus}
        handleStart={handleStart}
        handleStop={handleStop}
        handleManualBuy={handleManualBuy}
        handleManualSell={handleManualSell}
        handleResetPosition={handleResetPosition}
        handleResetPnL={handleResetPnL}
        updateSettings={updateSettings}
      />

      <RSIMonitorPanel />
      
      <div className="dashboard-grid">
        {/* Left Column: Chart & Visuals */}
        <div className="chart-column">
             {/* 2. Predictive Dashboard */}
             <div style={{marginBottom: '10px'}}>
                <PredictiveDashboard 
                    prediction={{ ...botStatus.prediction, rsi: botStatus.rsi }} 
                    isOpen={openPanels['predictive']}
                    onToggle={() => togglePanel('predictive')}
                />
             </div>

             {/* 3. Main Chart */}
             <div style={{position: 'relative'}}>
                <MarketChart data={botStatus.history} symbol={botStatus.symbol} prediction={botStatus.prediction} />
                <ChartHelp />
             </div>
             
             <TradeHistory 
                trades={botStatus.trades} 
                symbol={botStatus.symbol} 
                formatMoney={formatMoney} 
                showTrades={showTrades} 
                setShowTrades={setShowTrades} 
                historyFilter={historyFilter} 
                setHistoryFilter={setHistoryFilter} 
             />
        </div>
        
        {/* Right Column: The "Command Center" Accordion Stack */}
        <div className="settings-column" style={{ display: 'flex', flexDirection: 'column', gap: '0px' }}> {/* Gap handled by accordion margin */}
          


          <LiveMarket 
            botStatus={botStatus} 
            formatMoney={formatMoney} 
            priceChange={priceChange} 
            balanceChange={balanceChange} 
            isOpen={openPanels['live']}
            onToggle={() => togglePanel('live')}
          />


          <StatisticsCard 
            stats={botStatus.stats} 
            formatMoney={formatMoney} 
            isOpen={openPanels['stats']}
            onToggle={() => togglePanel('stats')}
          />

          <MarketSettings 
            botStatus={botStatus}
            updateSettings={updateSettings}
            showMarket={openPanels['market']} 
            setShowMarket={() => togglePanel('market')}
            isUpdating={isUpdating}
            isProMode={isProMode}
          />
          <RiskSettings 
            botStatus={botStatus}
            updateSettings={updateSettings}
            currencyAsset={botStatus.symbol?.replace('USDT', '') || 'BTC'}
            showRisk={openPanels['risk']} 
            setShowRisk={() => togglePanel('risk')}
            setShowTrailingModal={setShowTrailingModal}
            setShowSniperModal={setShowSniperModal}
            isUpdating={isUpdating}
            isProMode={isProMode}
          />
           <StrategySettings 
              botStatus={botStatus}
              updateSettings={updateSettings}
              showStrategy={openPanels['strategy']} 
              setShowStrategy={() => togglePanel('strategy')}
              isUpdating={isUpdating}
              isProMode={isProMode}
            />
          <ExtraSettings 
            botStatus={botStatus}
            updateSettings={updateSettings}
            showTelegram={openPanels['telegram']} 
            setShowTelegram={() => togglePanel('telegram')}
            showConverter={openPanels['converter']} 
            setShowConverter={() => togglePanel('converter')}
            convertAmount={convertAmount} setConvertAmount={setConvertAmount}
            tickers={tickers}
            currencyAsset={botStatus.symbol?.replace('USDT', '') || 'BTC'}
            isUpdating={isUpdating}
          />
        </div>
      </div>

      <div className="toast-container">
        {notifications.map(notif => (
          <div 
            key={notif.id} 
            className={`toast ${notif.type}`}
            onClick={() => removeNotification(notif.id)}
          >
            <span>{notif.type === 'success' ? '✅' : '❌'}</span>
            <span>{notif.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
