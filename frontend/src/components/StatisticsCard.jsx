import React from 'react';
import AccordionItem from './common/AccordionItem';

const StatisticsCard = ({ stats, formatMoney }) => {
    if (!stats) return (
        <div className="card status-card">
            <h2>📊 Rendimiento</h2>
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-dim)' }}>Cargando datos...</div>
        </div>
    );

    return (
        <div className="card status-card">
            <h2>📊 Rendimiento</h2>
            <div style={{ marginTop: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div style={{ textAlign: 'center' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Win Rate</span>
                        <div className={stats.win_rate >= 50 ? 'profit-text' : 'loss-text'} style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                            {stats.win_rate}%
                        </div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Total PnL</span>
                        <div className={stats.net_pnl >= 0 ? 'profit-text' : 'loss-text'} style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                            {formatMoney(stats.net_pnl)}
                        </div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Daily PnL</span>
                        <div className={stats.daily_pnl >= 0 ? 'profit-text' : 'loss-text'} style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                            {formatMoney(stats.daily_pnl)}
                        </div>
                    </div>
                </div>
                
                {/* Visual Win/Loss Bar */}
                <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden', background: '#333', marginBottom: '10px' }}>
                    <div style={{ width: `${stats.win_rate}%`, background: '#3fb950' }}></div>
                    <div style={{ flex: 1, background: '#f85149' }}></div>
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem' }}>
                    <span style={{ color: '#3fb950' }}>✅ {stats.wins} Ganadas</span>
                    <span style={{ color: '#f85149' }}>❌ {stats.losses} Perdidas</span>
                </div>
            </div>
        </div>
    );
};

export default StatisticsCard;
