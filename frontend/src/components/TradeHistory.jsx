import React from 'react';

const TradeHistory = ({ trades, symbol, formatMoney, showTrades, setShowTrades, historyFilter, setHistoryFilter }) => {
    return (
        <div className="card log-card" style={{ marginTop: '1.5rem' }}>
            <div 
                className="collapsible-header" 
                onClick={() => setShowTrades(!showTrades)}
                style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                    <h2 style={{ margin: 0 }}>Trade History {showTrades ? '📖' : '📘'}</h2>
                    
                    <div className="filter-controls" onClick={(e) => e.stopPropagation()} style={{ display: 'flex', gap: '5px' }}>
                        <button 
                            className={`filter-btn ${historyFilter === 'all' ? 'active' : ''}`}
                            onClick={() => setHistoryFilter('all')}
                        >
                            Todos
                        </button>
                        <button 
                            className={`filter-btn ${historyFilter === 'manual' ? 'active' : ''}`}
                            onClick={() => setHistoryFilter('manual')}
                        >
                            Manuales
                        </button>
                        <button 
                            className={`filter-btn ${historyFilter === 'auto' ? 'active' : ''}`}
                            onClick={() => setHistoryFilter('auto')}
                        >
                            Auto
                        </button>
                    </div>
                </div>
                <span className="toggle-icon">{showTrades ? '▲' : '▼'}</span>
            </div>
            
            <div className={`collapsible-content ${showTrades ? 'expanded' : 'collapsed'}`}>
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Type</th>
                            <th>Coin</th>
                            <th>Price</th>
                            <th>Qty</th>
                            <th>Total</th>
                            <th>Comisión</th>
                            <th>RSI</th>
                            <th>PnL</th>
                        </tr>
                    </thead>
                    <tbody>
                        {trades && trades
                            .filter(t => {
                                if (historyFilter === 'all') return true
                                if (historyFilter === 'manual') return t.type.toLowerCase().includes('manual')
                                if (historyFilter === 'auto') return !t.type.toLowerCase().includes('manual')
                                return true
                            })
                            .map((t, i) => (
                            <tr key={i} className={t.type.toLowerCase()}>
                                <td>{t.time ? t.time.split(' ')[1] : ''}</td>
                                <td>
                                    {t.type.toLowerCase().includes('manual') && '👤 '}
                                    {t.type}
                                </td>
                                <td>{t.symbol ? t.symbol.replace('USDT', '') : (symbol ? symbol.replace('USDT', '') : 'BTC')}</td>
                                <td>{formatMoney(t.price, 2)}</td>
                                <td>{t.qty ? parseFloat(t.qty).toFixed(5) : '-'}</td>
                                <td>{t.total ? formatMoney(t.total, 2) : formatMoney(t.price * t.qty, 2)}</td>
                                <td style={{ color: '#f85149' }}>{t.commission ? formatMoney(t.commission, 2) : '-'}</td>
                                <td className={t.rsi <= 30 ? 'profit-text' : t.rsi >= 70 ? 'loss-text' : ''}>
                                    {t.rsi ? t.rsi.toFixed(2) : '-'}
                                </td>
                                <td className={t.pnl >= 0 ? 'profit-text' : 'loss-text'}>{formatMoney(t.pnl, 2)}</td>
                            </tr>
                        ))}
                        {(!trades || trades.length === 0) && (
                            <tr><td colSpan="9">No trades yet... waiting for market action.</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default TradeHistory;
