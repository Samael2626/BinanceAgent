import React from 'react';
import AccordionItem from './common/AccordionItem';

const LiveMarket = ({ botStatus, formatMoney, priceChange, balanceChange, isOpen, onToggle }) => {
    return (
        <AccordionItem 
            title="Mercado en Vivo" 
            isOpen={isOpen} 
            onToggle={onToggle} 
            icon="📈"
            helpText="Muestra el precio actual y tu balance en tiempo real."
        >
          <div className="metrics-large">
            <div className="metric-box">
              <label>Precio Actual</label>
              <div className="value" style={{ fontSize: '1.2rem' }}>
                {formatMoney(botStatus.price)}
                <div className={`change ${priceChange > 0 ? 'up' : priceChange < 0 ? 'down' : 'neutral'}`} style={{ fontSize: '0.8rem' }}>
                  {priceChange > 0 ? '↑' : priceChange < 0 ? '↓' : '―'} {Math.abs(priceChange).toFixed(2)}%
                </div>
              </div>
            </div>
            <div className="metric-box">
              <label>Saldo Total</label>
              <div className="value" style={{ fontSize: '1.2rem' }}>
                {formatMoney(botStatus.balance)}
                <div className={`change ${balanceChange > 0 ? 'up' : balanceChange < 0 ? 'down' : 'neutral'}`} style={{ fontSize: '0.8rem' }}>
                  {balanceChange > 0 ? '↑' : balanceChange < 0 ? '↓' : '―'} {Math.abs(balanceChange).toFixed(2)}%
                </div>
              </div>
            </div>
            <div className="metric-box">
              <label>Holdings</label>
              <div className="value" style={{ fontSize: '1.2rem' }}>
                {botStatus.crypto_balance || 0}
                <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                  {botStatus.symbol?.replace('USDT', '') || '???'}
                </div>
              </div>
            </div>
          </div>
          <div style={{ marginTop: '15px', borderTop: '1px solid var(--border)', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
            <div>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>PnL Total</span>
              <div className={botStatus.pnl >= 0 ? 'profit-text' : 'loss-text'} style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                {formatMoney(botStatus.pnl)}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>PnL Diario</span>
              <div className={botStatus.daily_pnl >= 0 ? 'profit-text' : 'loss-text'} style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                {formatMoney(botStatus.daily_pnl)}
              </div>
            </div>
          </div>
        </AccordionItem>
    );
};

export default LiveMarket;
