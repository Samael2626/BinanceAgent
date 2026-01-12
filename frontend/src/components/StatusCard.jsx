import React from 'react';

const StatusCard = ({ botStatus, formatMoney }) => {
    // Helper for trend color
    const getProfitClass = (val) => val > 0 ? 'text-gold' : val < 0 ? 'loss-text' : 'text-dim';

    return (
        <div className="status-bar-container" style={{ 
            background: 'var(--panel-bg)', 
            border: '1px solid var(--panel-border)',
            boxShadow: 'var(--shadow-soft)',
            backdropFilter: 'blur(10px)',
            marginBottom: '1.5rem'
        }}>
            {/* 1. Status with Pulse */}
            <div className="flex-center" style={{ gap: '12px', borderRight: '1px solid var(--panel-border)', paddingRight: '25px' }}>
                <div className={`status-indicator ${botStatus.is_running ? 'running' : 'idle'} ${botStatus.is_running ? 'pulse-active' : ''}`} 
                     style={{ width: '8px', height: '8px', borderRadius: '50%', background: botStatus.is_running ? 'var(--success)' : 'var(--text-sec)', boxShadow: botStatus.is_running ? '0 0 10px var(--success)' : 'none' }}>
                </div>
                <span style={{ fontWeight: 700, fontSize: '0.85rem', letterSpacing: '0.05em', color: botStatus.is_running ? 'var(--success)' : 'var(--text-sec)' }}>
                    {botStatus.is_running ? 'SYSTEM ONLINE' : 'STANDBY'}
                </span>
            </div>

            {/* 2. Ticker Metrics */}
            <div style={{ display: 'flex', flex: 1, justifyContent: 'space-between', alignItems: 'center', paddingLeft: '25px' }}>
                <div className="ticker-item" style={{ border: 'none' }}>
                    <span className="ticker-label">MARKET</span>
                    <span className="ticker-value" style={{ fontFamily: 'monospace' }}>{botStatus.symbol}</span>
                </div>
                
                <div className="ticker-item" style={{ border: 'none' }}>
                    <span className="ticker-label">CURRENT PRICE</span>
                    <span className="ticker-value text-gold" style={{ fontFamily: 'monospace' }}>{formatMoney(botStatus.price)}</span>
                </div>

                <div className="ticker-item" style={{ border: 'none' }}>
                    <span className="ticker-label">RSI (14)</span>
                    <span className={`ticker-value ${botStatus.rsi <= 30 || botStatus.rsi >= 70 ? 'text-gold' : ''}`} style={{ fontFamily: 'monospace' }}>
                        {botStatus.rsi ? parseFloat(botStatus.rsi).toFixed(1) : '--'}
                    </span>
                </div>

                <div className="ticker-item" style={{ border: 'none' }}>
                    <span className="ticker-label">24H PNL</span>
                    <span className={`ticker-value ${getProfitClass(botStatus.daily_pnl)}`}>
                        {botStatus.daily_pnl ? `${botStatus.daily_pnl}%` : '--'}
                    </span>
                </div>
                
                <div className="ticker-item" style={{ border: 'none' }}>
                    <span className="ticker-label">TOTAL EQUITY</span>
                    <span className="ticker-value">{formatMoney(botStatus.balance)}</span>
                </div>

                <div className="ticker-item" style={{ border: 'none', paddingRight: 0 }}>
                    <span className="ticker-label">EXECUTION</span>
                    <span className="ticker-value" style={{ 
                        fontSize: '0.75rem', 
                        padding: '2px 8px', 
                        borderRadius: '4px', 
                        background: botStatus.mode === 'REAL' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(148, 163, 184, 0.1)',
                        color: botStatus.mode === 'REAL' ? 'var(--danger)' : 'var(--text-sec)' 
                    }}>
                        {botStatus.mode}
                    </span>
                </div>
            </div>
        </div>
    );
};

export default StatusCard;
