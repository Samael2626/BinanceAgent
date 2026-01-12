import React from 'react';
import TradeSlider from './TradeSlider';

const TradeModal = ({ 
  showTradeModal, 
  setShowTradeModal, 
  tradeModalType, 
  botStatus, 
  tradeAmount, 
  updateTradeAmount, 
  tradeAmountUSDT, 
  updateTradeAmountUSDT, 
  confirmTrade, 
  isSubmitting, 
  error,
  formatMoney 
}) => {
  if (!showTradeModal) return null;

  const isBuy = tradeModalType === 'buy';
  const symbol = botStatus.symbol || 'BTCUSDT';
  // If the symbol is BTCUSDT, asset is BTC
  const asset = symbol.replace('USDT', '');
  
  // Standardize title/label based on the actual asset being traded
  const title = isBuy ? `Compra Manual (${asset})` : `Venta Manual (${asset})`;
  
  const balance = isBuy ? botStatus.balance : botStatus.crypto_balance;

  return (
    <div className="modal-overlay" onClick={() => setShowTradeModal(false)}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="section-header" style={{ justifyContent: 'space-between', borderBottom: 'none' }}>
          <h3>{title}</h3>
          <button 
            className="minimal-btn" 
            onClick={() => setShowTradeModal(false)}
            style={{ padding: '4px 8px', fontSize: '1.2rem', lineHeight: '1' }}
          >
            ×
          </button>
        </div>
        
        <div className="modal-body" style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', padding: '10px', background: 'var(--input-bg)', borderRadius: 'var(--radius-sm)' }}>
            <div className="metric">
                <span>Precio Actual</span>
                <b>{formatMoney(botStatus.price)}</b>
            </div>
            <div className="metric">
                <span>Disponible</span>
                <b>{isBuy ? formatMoney(balance) : `${balance} ${asset}`}</b>
            </div>
          </div>

          <div className="form-group">
            <label>Cantidad ({asset})</label>
            <input 
              type="number" 
              value={tradeAmount} 
              onChange={(e) => updateTradeAmount(e.target.value)}
              placeholder={`0.0000 ${asset}`}
            />
          </div>
          
          <div className="form-group">
            <label>Valor Aproximado (USDT)</label>
            <input 
              type="number" 
              value={tradeAmountUSDT} 
              onChange={(e) => updateTradeAmountUSDT(e.target.value)}
              placeholder="0.00 USDT"
            />
          </div>

          {/* Slider Component */}
          <div style={{ marginBottom: '1.5rem' }}>
             <TradeSlider 
                type={tradeModalType} 
                balance={balance} 
                symbol={symbol} 
                price={botStatus.price} 
                stepSize={botStatus.step_size || 0.00001}
                onAmountChange={(val) => {
                updateTradeAmount(val);
                }} 
            />
          </div>

          {isSubmitting && <div className="status-indicator running" style={{ justifyContent: 'center', marginBottom: '1rem' }}>Procesando...</div>}
          {error && <div className="error-message">{error}</div>}
        </div>

        <div style={{ display: 'flex', gap: '10px', marginTop: '1rem' }}>
          <button className="minimal-btn" style={{ flex: 1 }} onClick={() => setShowTradeModal(false)}>Cancelar</button>
          <button 
            className="confirm-btn" 
            style={{ flex: 2, background: isBuy ? 'var(--success)' : 'var(--danger)' }}
            onClick={confirmTrade}
            disabled={isSubmitting}
          >
            {isBuy ? 'COMPRAR' : 'VENDER'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TradeModal;
