import { useState, useEffect } from 'react';

const TradeSlider = ({ type, balance, symbol, price, stepSize, onAmountChange }) => {
  const [percentage, setPercentage] = useState(0);

  const handleSliderChange = (e) => {
    const val = parseFloat(e.target.value);
    setPercentage(val);
    calculateAmount(val);
  };

  const handleButtonClick = (val) => {
    setPercentage(val);
    calculateAmount(val);
  };

  const floorToStep = (value, step) => {
    if (!step) return value;
    // Helper to round down to nearest step
    const inv = 1 / step;
    return Math.floor(value * inv) / inv;
  }

  const calculateAmount = (percent) => {
    if (!balance || !price) return;

    let amount = 0;
    if (type === 'buy') {
      // Buy: Percentage of USDT Balance -> divided by price -> Qty in Crypto
      const usdtAmount = balance * (percent / 100);
      amount = usdtAmount / price;
    } else {
      // Sell: Percentage of Crypto Balance -> Qty in Crypto
      amount = balance * (percent / 100);
    }
    
    // Apply step size flooring
    // Use stepSize passed from parent (defaulting to 0.00001)
    const step = stepSize || 0.00001;
    const flooredAmount = floorToStep(amount, step);
    
    // Formatting: Adjust decimals based on step size roughly
    // e.g. step 0.00001 -> 5 decimals
    const precision = Math.max(0, Math.log10(1 / step));
    
    onAmountChange(flooredAmount.toFixed(Math.ceil(precision)));
  };

  // Reset if type changes
  useEffect(() => {
    setPercentage(0);
  }, [type]);

  return (
    <div className="trade-slider-container" style={{ marginTop: '15px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
        <span>0%</span>
        <span>{percentage}%</span>
      </div>
      <input
        type="range"
        min="0"
        max="100"
        step="1"
        value={percentage}
        onChange={handleSliderChange}
        style={{ width: '100%', cursor: 'pointer', accentColor: 'var(--binance-yellow)' }}
      />
      <div style={{ display: 'flex', gap: '5px', marginTop: '10px', justifyContent: 'space-between' }}>
        {[25, 50, 75, 100].map((pct) => (
          <button
            key={pct}
            onClick={() => handleButtonClick(pct)}
            className="minimal-btn"
            style={{ 
              flex: 1, 
              fontSize: '0.75rem', 
              padding: '4px',
              background: percentage === pct ? 'rgba(243, 186, 47, 0.2)' : 'rgba(255,255,255,0.05)',
              color: percentage === pct ? 'var(--binance-yellow)' : 'var(--text-dim)',
              border: percentage === pct ? '1px solid var(--binance-yellow)' : '1px solid transparent'
            }}
          >
            {pct}%
          </button>
        ))}
      </div>
    </div>
  );
};

export default TradeSlider;
