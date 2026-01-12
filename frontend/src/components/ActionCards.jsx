import React from 'react';

const ActionCards = ({ botStatus, handleStart, handleStop, handleManualBuy, handleManualSell, handleResetPosition, handleResetPnL, updateSettings }) => {
  return (
    <div className="action-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--panel-bg)', padding: '10px 15px', borderRadius: '12px', marginBottom: '20px', border: '1px solid var(--panel-border)', boxShadow: 'var(--shadow-soft)' }}>
      {/* Left: Main Control */}
      <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
        {!botStatus.is_running ? (
          <button className="confirm-btn" onClick={handleStart} style={{ padding: '8px 20px', borderRadius: '8px', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
             <span>▶</span> START ENGINE
          </button>
        ) : (
          <button className="stop-btn" onClick={handleStop} style={{ background: 'var(--danger)', color: 'white', padding: '8px 20px', borderRadius: '8px', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
             <span>⏹</span> HALT SYSTEM
          </button>
        )}
        
        <div style={{ height: '24px', width: '1px', background: 'var(--panel-border)' }}></div>

        {/* Toggles */}
        <div style={{ display: 'flex', gap: '10px' }}>
             <button 
                onClick={() => updateSettings({ enable_buying: !botStatus.settings?.enable_buying })}
                style={{ 
                    background: botStatus.settings?.enable_buying ? 'rgba(63, 185, 80, 0.15)' : 'transparent', 
                    border: `1px solid ${botStatus.settings?.enable_buying ? '#3fb950' : 'var(--text-sec)'}`,
                    color: botStatus.settings?.enable_buying ? '#3fb950' : 'var(--text-sec)',
                    padding: '6px 12px', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 600
                }}
             >
                {botStatus.settings?.enable_buying ? 'BUYING: ON' : 'BUYING: PAUSED'}
             </button>

             <button 
                onClick={() => updateSettings({ enable_selling: !botStatus.settings?.enable_selling })}
                style={{ 
                    background: botStatus.settings?.enable_selling ? 'rgba(248, 81, 73, 0.15)' : 'transparent', 
                    border: `1px solid ${botStatus.settings?.enable_selling ? '#f85149' : 'var(--text-sec)'}`,
                    color: botStatus.settings?.enable_selling ? '#f85149' : 'var(--text-sec)',
                    padding: '6px 12px', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 600
                }}
             >
                {botStatus.settings?.enable_selling ? 'SELLING: ON' : 'SELLING: PAUSED'}
             </button>
        </div>
      </div>

      {/* Right: Manual Actions */}
      <div style={{ display: 'flex', gap: '8px' }}>
        <button className="minimal-btn" onClick={handleManualBuy} title="Execute Manual Buy">🛒 Buy</button>
        <button className="minimal-btn" onClick={handleManualSell} title="Execute Manual Sell">💰 Sell</button>
        <button className="minimal-btn" onClick={handleResetPosition} title="Reset Position Data">🔄 Reset Pos</button>
        <button className="minimal-btn" onClick={handleResetPnL} title="Clear PnL History">📊 Clear PnL</button>
      </div>
    </div>
  );
};

export default ActionCards;
