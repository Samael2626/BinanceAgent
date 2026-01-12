import React from 'react';
import NoviceProSwitch from './common/NoviceProSwitch';
// Checking App.jsx imports might be needed, but assuming standard component folder.
// Actually, in App.jsx it was likely imported. I'll check App.jsx imports if needed, but usually it's in components.

const Header = ({ currency, setCurrency, botStatus, handleLogout, theme, toggleTheme, isProMode, handleProToggle }) => {
  return (
    <div className="action-bar" style={{ marginBottom: '2rem', borderLeft: 'none', background: 'transparent', padding: '0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
         <h1 style={{ margin: 0, fontSize: '1.8rem', letterSpacing: '-0.03em' }}>
            Binance Agent <span className="text-gold">Pro</span>
         </h1>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        {/* Novice/Pro Switch */}
        <div style={{ marginRight: '15px' }}>
           <NoviceProSwitch isPro={isProMode} onToggle={handleProToggle} />
        </div>

        {/* Currency Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="text-dim" style={{ fontSize: '0.9rem' }}>Moneda:</span>
          <select 
            value={currency} 
            onChange={(e) => setCurrency(e.target.value)}
            style={{ 
              width: 'auto',
              padding: '6px 12px',
              fontWeight: '600',
              color: 'var(--premium-gold)',
              borderColor: 'rgba(199, 164, 74, 0.3)'
            }}
          >
            <option value="USDT">USDT (USD)</option>
            <option value="COP">COP (Pesos)</option>
          </select>
        </div>

        {/* Theme Switcher */}
        <button 
            onClick={toggleTheme}
            className="minimal-btn"
            style={{ fontSize: '1.2rem', padding: '6px 10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            title={`Cambiar a ${theme === 'dark' ? 'Modo Claro' : 'Modo Oscuro'}`}
        >
            {theme === 'dark' ? '🌙' : '☀️'}
        </button>

        {/* Logout */}
        <button className="minimal-btn" onClick={handleLogout}>
          Logout 🔑
        </button>
      </div>
    </div>
  );
};

export default Header;
