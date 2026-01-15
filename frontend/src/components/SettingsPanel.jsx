import React, { useState } from 'react';
import AccordionItem from './common/AccordionItem';
import HelpTooltip from './common/HelpTooltip';
import NoviceProSwitch from './common/NoviceProSwitch';

export const MarketSettings = ({ botStatus, updateSettings, showMarket, setShowMarket, isUpdating, isProMode }) => (
    <AccordionItem 
      title="Mercado y Tiempo" 
      isOpen={showMarket} 
      onToggle={() => setShowMarket(!showMarket)}
      icon="⚙️"
      helpText="Este módulo controla qué activo operar, la velocidad de análisis y cómo gestionar las salidas."
    >
      <div style={{ padding: '0 5px' }}>
          <div style={{ marginBottom: '10px' }}>
             <p style={{fontSize: '12px', color: '#848E9C', marginBottom: '8px'}}>Configura qué moneda operar y la velocidad del bot.</p>
          </div>

          <div className="settings-grid-3" style={{ marginBottom: '15px' }}>
            <div className="form-group">
              <label>
                Moneda <HelpTooltip text="El par de criptomonedas que el bot analizará y operará (Ej: Bitcoin contra USDT)." /> 
                <span title="Recomendación Senior" style={{ color: '#ff9800', cursor: 'help', fontSize: '10px', marginLeft: '4px' }}>[💡 SOL/BTC]</span>
              </label>
              <select 
                className="login-input" 
                value={botStatus.settings?.symbol || 'BTCUSDT'} 
                onChange={(e) => updateSettings({ symbol: e.target.value })}
                disabled={isUpdating}
                style={{ opacity: isUpdating ? 0.6 : 1, cursor: isUpdating ? 'not-allowed' : 'pointer' }}
              >
                <option value="BTCUSDT">Bitcoin (BTC)</option>
                <option value="ETHUSDT">Ethereum (ETH)</option>
                <option value="BNBUSDT">Binance Coin (BNB)</option>
                <option value="SOLUSDT">Solana (SOL)</option>
                <option value="ADAUSDT">Cardano (ADA)</option>
                <option value="XRPUSDT">XRP (XRP)</option>
                <option value="DOGEUSDT">Dogecoin (DOGE)</option>
                <option value="DOTUSDT">Polkadot (DOT)</option>
                <option value="MATICUSDT">Polygon (MATIC)</option>
                <option value="AVAXUSDT">Avalanche (AVAX)</option>
              </select>
            </div>
            
            {(isProMode || botStatus.settings?.timeframe !== '1m') && (
                 <div className="form-group">
                    <label>
                        Intervalo <HelpTooltip text="Cada cuánto tiempo cierra una vela. 1m es muy rápido, 5m es más estable." />
                        <span title="Recomendación Senior" style={{ color: '#ff9800', cursor: 'help', fontSize: '10px', marginLeft: '4px' }}>[⚠️ 15m]</span>
                    </label>
                    <select 
                        className="login-input" 
                        value={botStatus.settings?.timeframe || '1m'}
                        onChange={(e) => updateSettings({ timeframe: e.target.value })}
                        disabled={isUpdating}
                    >
                        <option value="off">🚫 OFF</option>
                        <option value="1m">1 Minuto</option>
                        <option value="5m">5 Minutos</option>
                        <option value="15m">15 Minutos</option>
                        <option value="1h">1 Hora</option>
                    </select>
                </div>
            )}

            <div className="form-group">
              <label>Venta <HelpTooltip text="Completa: Vende todo al llegar al objetivo. Gradual: Vende por partes para asegurar ganancias." /></label>
              <select 
                className="login-input" 
                value={botStatus.settings?.sell_mode || 'full'} 
                onChange={(e) => updateSettings({ sell_mode: e.target.value })}
                disabled={isUpdating}
              >
                <option value="full">Todo (100%)</option>
                <option value="gradual">Escalonada</option>
              </select>
            </div>
          </div>

        {isProMode && (
         <div style={{ marginTop: '5px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '15px', background: 'rgba(255,255,255,0.03)', padding: '5px', borderRadius: '6px' }}>
            <label style={{ fontSize: '0.8rem', color: botStatus.mode === 'TESTNET' ? 'var(--text-dim)' : '#666', cursor: botStatus.mode === 'TESTNET' ? 'pointer' : 'not-allowed' }}>
                Usar Datos Reales (Mainnet):
            </label>
            <input 
                type="checkbox" 
                disabled={botStatus.mode !== 'TESTNET' || isUpdating}
                checked={botStatus.settings?.use_real_data || false} 
                onChange={(e) => updateSettings({ use_real_data: e.target.checked })}
                style={{ width: '16px', height: '16px', cursor: (botStatus.mode === 'TESTNET' && !isUpdating) ? 'pointer' : 'not-allowed' }}
            />
         </div>
        )}
      </div>
    </AccordionItem>
);

export const RiskSettings = ({ botStatus, updateSettings, showRisk, setShowRisk, currencyAsset, setShowTrailingModal, setShowSniperModal, isUpdating, isProMode }) => {
    // Helper checks
    const stopLoss = parseFloat(botStatus.settings?.stop_loss_pct || 0);
    const takeProfit = parseFloat(botStatus.settings?.take_profit_pct || 0);

    return (
    <AccordionItem 
      title="Riesgo y Capital" 
      isOpen={showRisk} 
      onToggle={() => setShowRisk(!showRisk)}
      icon="🛡️"
      helpText="Define cuánto invertir por operación y tus límites de seguridad (Stop Loss / Take Profit)."
    >
      <div style={{ padding: '0 5px' }}>
           <div style={{ marginBottom: '10px' }}>
             <p style={{fontSize: '12px', color: '#848E9C', marginBottom: '8px'}}>Controla cuánto dinero inviertes y tus límites de seguridad.</p>
          </div>

        <div className="settings-grid-2">
           <div className="form-group">
                <label>Saldo Mínimo (USDT) <HelpTooltip text="El bot no operará si tu saldo baja de este monto. Protege tu capital base." /></label>
                <input type="number" step="any" className="login-input" value={botStatus.settings?.min_balance} onChange={(e) => updateSettings({ min_balance: e.target.value })} disabled={isUpdating} />
            </div>
          
            <div className="form-group">
                <label>Unidad de Compra</label>
                 <select 
                  className="login-input" 
                  value={botStatus.settings?.trade_qty_type || 'base'} 
                  onChange={(e) => updateSettings({ trade_qty_type: e.target.value })}
                  disabled={isUpdating}
                >
                  <option value="base">Cripto ({currencyAsset})</option>
                  <option value="quote">USDT (Monto Fijo)</option>
                </select>
            </div>
        </div>

        <div className="settings-grid-2">
            <div className="form-group">
                <label>
                    {botStatus.settings?.trade_qty_type === 'quote' ? 'Monto a Invertir (USDT)' : `Cantidad (${currencyAsset})`} 
                    <HelpTooltip text="Cuánto dinero usará el bot en cada compra inicial." />
                    <span title="Recomendación Senior" style={{ color: '#ff9800', cursor: 'help', fontSize: '10px', marginLeft: '4px' }}>[⚠️ 35]</span>
                </label>
                <input type="number" step="0.0001" className="login-input input-required" value={botStatus.settings?.trade_qty} onChange={(e) => updateSettings({ trade_qty: e.target.value })} />
            </div>
        </div>
        
        {/* DCA Section */}
         <div style={{ marginTop: '10px', padding: '10px', background: 'rgba(31, 111, 235, 0.05)', borderRadius: '6px', border: '1px solid rgba(31, 111, 235, 0.1)' }}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom: '8px'}}>
                 <label style={{fontWeight:'bold', color: '#58a6ff', fontSize: '12px'}}>Estrategia DCA (Promedio) <HelpTooltip text="Si el precio baja, el bot compra más para bajar el precio promedio de entrada." /></label>
                 <button 
                    className={`login-btn ${botStatus.settings?.dca_enabled !== false ? 'active' : ''}`}
                    style={{ height: '24px', padding: '0 8px', fontSize: '0.7rem', width: 'auto' }}
                    onClick={() => updateSettings({ dca_enabled: botStatus.settings?.dca_enabled === false })}
                >
                    {botStatus.settings?.dca_enabled !== false ? 'ON' : 'OFF'}
                </button>
            </div>
             {botStatus.settings?.dca_enabled !== false && (
                <div className="settings-grid-2">
                    <div className="form-group" style={{ marginBottom: 0 }}>
                        <label>Máx Recompras <HelpTooltip text="Cuántas veces comprará extra si el precio cae." /></label>
                         <input type="number" className="login-input" value={botStatus.settings?.max_dca_orders} onChange={(e) => updateSettings({ max_dca_orders: e.target.value })} />
                    </div>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                        <label>Caída para Recompra % <HelpTooltip text="Qué tanto debe bajar el precio para activar una recompra." /></label>
                         <input type="number" step="0.01" className="login-input" value={botStatus.settings?.dca_step_pct} onChange={(e) => updateSettings({ dca_step_pct: e.target.value })} />
                    </div>
                </div>
             )}
         </div>

          {/* Senior Protection Engine - Refactored for Premium Look & Logic */}
          <div style={{ 
            marginTop: '15px', 
            padding: '16px', 
            background: 'linear-gradient(145deg, rgba(46,160,67,0.1), rgba(1,4,9,0.4))', 
            borderRadius: '12px', 
            border: '1px solid rgba(46,160,67,0.2)',
            boxShadow: '0 4px 15px rgba(0,0,0,0.2)',
            position: 'relative',
            overflow: 'hidden'
          }}>
             {/* Decorative background element */}
             <div style={{ position: 'absolute', top: '-20px', right: '-20px', width: '60px', height: '60px', background: 'rgba(46,160,67,0.1)', borderRadius: '50%', filter: 'blur(15px)' }}></div>

             <label style={{ fontSize: '14px', color: '#3fb950', fontWeight: '800', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '18px' }}>🌊</span> MOTOR DE PROTECCIÓN (Manos Libres)
             </label>

             <div className="form-group" style={{ marginBottom: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                   <label style={{ fontSize: '12px', color: '#e6edf3', fontWeight: '500', margin: 0 }}>
                      Sensibilidad del Trailing
                   </label>
                   <div style={{ background: '#ff9800', padding: '2px 8px', borderRadius: '4px', fontSize: '10px', color: '#000', fontWeight: 'bold' }}>
                      🔥 RECOMENDADO
                   </div>
                </div>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ flex: 1, position: 'relative' }}>
                       <input 
                         type="number" 
                         step="0.05"
                         min="0.1"
                         max="5.0"
                         className="login-input" 
                         style={{ 
                            height: '40px', 
                            fontSize: '16px', 
                            fontWeight: 'bold', 
                            background: 'rgba(255,255,255,0.05)',
                            paddingRight: '35px'
                         }} 
                         value={botStatus.settings?.rsi_trailing_pct || 0.8} 
                         onChange={(e) => updateSettings({ rsi_trailing_pct: e.target.value })} 
                       />
                       <span style={{ position: 'absolute', right: '12px', top: '10px', color: '#848E9C', fontSize: '14px' }}>%</span>
                    </div>
                    <div style={{ 
                      textAlign: 'center', 
                      minWidth: '70px',
                      padding: '5px',
                      background: 'rgba(255,255,255,0.02)',
                      borderRadius: '6px',
                      border: '1px solid rgba(255,255,255,0.05)'
                    }}>
                       <div style={{ fontSize: '9px', color: '#848E9C' }}>Sugerido:</div>
                       <div style={{ fontSize: '12px', color: '#ff9800', fontWeight: 'bold' }}>
                          {botStatus.symbol?.includes('BTC') ? '0.3%' : '0.5%'}
                       </div>
                    </div>
                </div>
                <p style={{ fontSize: '11px', color: '#848E9C', marginTop: '12px', lineHeight: '1.4' }}>
                   *Esta barra es tu "escudo". Controla qué tan cerca sigue el bot al precio máximo para asegurar ganancias.*
                </p>
             </div>
          </div>
         
          {/* Límite Fijo (Panic/Exit) */}
          <div style={{ 
            background: 'rgba(1,4,9,0.3)', 
            padding: '16px', 
            borderRadius: '12px', 
            marginTop: '15px', 
            border: '1px solid rgba(255,255,255,0.05)' 
          }}>
            <label style={{ fontSize: '13px', color: '#58a6ff', fontWeight: 'bold', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '16px' }}>🛑</span> LÍMITES DE SEGURIDAD (Salida Forzada)
            </label>
            
            <div className="settings-grid-2" style={{ gap: '15px' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label style={{color: '#f85149', fontSize: '11px', fontWeight: '600', marginBottom: '6px', display: 'block'}}>
                   Stop Loss (Límite Rojo)
                </label>
                <div style={{ position: 'relative' }}>
                    <input 
                        type="number" 
                        step="0.1"
                        className={`login-input ${botStatus.settings?.stop_loss_pct > 5 ? 'input-danger' : ''}`} 
                        style={{ height: '38px', background: 'rgba(248,81,73,0.05)' }} 
                        value={botStatus.settings?.stop_loss_pct} 
                        onChange={(e) => updateSettings({ stop_loss_pct: e.target.value })} 
                    />
                    <span style={{ position: 'absolute', right: '10px', top: '9px', color: '#f85149' }}>%</span>
                </div>
                <div style={{ color: '#ff9800', fontSize: '10px', marginTop: '6px', fontWeight: '500' }}>💡 Recomendado: 3.2%</div>
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label style={{color: '#2ea043', fontSize: '11px', fontWeight: '600', marginBottom: '6px', display: 'block'}}>
                   Take Profit (Salida Inmediata)
                </label>
                <div style={{ position: 'relative' }}>
                    <input 
                        type="number" 
                        step="0.1"
                        className="login-input" 
                        style={{ height: '38px', background: 'rgba(46,160,67,0.05)' }} 
                        value={botStatus.settings?.take_profit_pct} 
                        onChange={(e) => updateSettings({ take_profit_pct: e.target.value })} 
                    />
                    <span style={{ position: 'absolute', right: '10px', top: '9px', color: '#2ea043' }}>%</span>
                </div>
                <div style={{ color: '#ff9800', fontSize: '10px', marginTop: '6px', fontWeight: '500' }}>💡 Recomendado: 1.3%</div>
              </div>
            </div>
            
            <div style={{ 
              marginTop: '15px', 
              padding: '8px', 
              background: 'rgba(255,152,0,0.05)', 
              borderRadius: '6px', 
              border: '1px dashed rgba(255,152,0,0.2)',
              fontSize: '10px',
              color: '#848E9C',
              textAlign: 'center'
            }}>
               El bot usará el **Trailing** para ganar MAS del 1.3%, y el **Take Profit** como salida de emergencia ante subidas repentinas.
            </div>
          </div>

      </div>
    </AccordionItem>
    );
};

export const StrategySettings = ({ botStatus, updateSettings, showStrategy, setShowStrategy, isUpdating, isProMode }) => {
  const [showGuide, setShowGuide] = useState(false);

  return (
     <AccordionItem 
      title="Estrategia de Trading" 
      isOpen={showStrategy} 
      onToggle={() => setShowStrategy(!showStrategy)}
      icon="📊"
      helpText="Selecciona la lógica de inteligencia que usará el bot para decidir cuándo comprar o vender."
    >
       <div style={{ padding: '5px' }}>
         {/* Unified Senior Guide Toggle */}
         <div 
            onClick={() => setShowGuide(!showGuide)}
            style={{ 
              marginBottom: '15px', 
              padding: '12px', 
              background: showGuide ? 'rgba(255,152,0,0.1)' : 'rgba(255,255,255,0.03)', 
              borderRadius: '10px', 
              border: showGuide ? '1px solid #ff9800' : '1px solid rgba(255,255,255,0.05)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              transition: 'all 0.3s ease'
            }}
         >
            <span style={{ fontSize: '18px' }}>🧠</span>
            <span style={{ fontSize: '12px', fontWeight: '800', color: showGuide ? '#ff9800' : '#e6edf3' }}>
               {showGuide ? 'CERRAR GUÍA SENIOR' : 'VER GUÍA DE ESTRATEGIA'}
            </span>
         </div>

         {/* Unified Premium Guide (Aviso) */}
         {showGuide && (
            <div style={{ 
               background: 'linear-gradient(135deg, rgba(1,4,9,0.95), rgba(46,160,67,0.05))', 
               padding: '18px', 
               borderRadius: '12px', 
               border: '1px solid #ff9800', 
               marginBottom: '20px', 
               boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
               animation: 'fadeIn 0.4s ease'
            }}>
               <h4 style={{ margin: '0 0 12px 0', color: '#ff9800', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  📡 PROTOCOLO DE INTELIGENCIA SENIOR
               </h4>
               <p style={{ fontSize: '11px', color: '#848E9C', lineHeight: '1.5', marginBottom: '15px' }}>
                  Capitán, este panel configura el "ojo" del bot. El sistema usa un RSI de 14 periodos combinado con una EMA Dinámica para validar cada paso.
               </p>
               <div style={{ display: 'grid', gap: '10px' }}>
                  {[
                     { t: '⚡ Rápida', d: 'Solo compra si el precio ya está subiendo (rebotando) sobre la EMA corta.' },
                     { t: '📈 Tendencia', d: 'Regla de oro: No compra si el mercado es bajista (precio < EMA Dinámica).' },
                     { t: '📊 Volumen', d: 'Ignora "falsas alarmas" si no hay volumen real operando la moneda.' },
                     { t: '🚫 Exclusión', d: 'Gestión de riesgo: No abre BTC y SOL al mismo tiempo para no doblar riesgo.' }
                  ].map(item => (
                     <div key={item.t} style={{ padding: '8px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', borderLeft: '3px solid #ff9800' }}>
                        <span style={{ fontSize: '11px', fontWeight: 'bold', color: '#e6edf3', display: 'block' }}>{item.t}</span>
                        <span style={{ fontSize: '10px', color: '#848E9C' }}>{item.d}</span>
                     </div>
                  ))}
               </div>
            </div>
         )}


         {/* 1. Main Strategy Selection */}
         <div style={{ 
            background: 'rgba(255,255,255,0.02)', 
            padding: '16px', 
            borderRadius: '12px', 
            border: '1px solid rgba(255,255,255,0.05)', 
            marginBottom: '15px' 
         }}>
            <label style={{ fontSize: '13px', color: '#848E9C', fontWeight: 'bold', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
               🧠 MODELO DE INTELIGENCIA
            </label>
            <select 
               className="login-input" 
               style={{ height: '42px', fontSize: '14px', fontWeight: '600', border: '1px solid rgba(88,166,255,0.2)' }}
               value={botStatus.settings?.active_strategy || 'rsi'} 
               onChange={(e) => updateSettings({ active_strategy: e.target.value })}
               disabled={isUpdating}
            >
               <option value="rsi">RSI Estándar (Equilibrado)</option>
               <option value="ema_rsi">Tendencia + RSI (Seguro)</option>
               <option value="multi">Multi-Indicador (Precisión)</option>
               <option value="rebound">Rebote (Contra-Tendencia)</option>
               <option value="scalper_pro">Scalper-PRO (Agresivo)</option>
            </select>
         </div>

         {/* 2. RSI Levels - Compact & Visual */}
         <div className="settings-grid-2" style={{ gap: '15px', marginBottom: '15px' }}>
            <div style={{ background: 'rgba(46,160,67,0.03)', padding: '12px', borderRadius: '10px', border: '1px solid rgba(46,160,67,0.1)' }}>
               <label style={{ color: '#3fb950', fontSize: '11px', fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>
                  📈 NIVEL COMPRA (Barato)
               </label>
               <div style={{ position: 'relative' }}>
                  <input type="number" step="0.1" className="login-input" style={{ height: '35px', background: 'rgba(46,160,67,0.05)' }} value={botStatus.settings?.buy_rsi} onChange={(e) => updateSettings({ buy_rsi: e.target.value })} disabled={isUpdating} />
                  <div style={{ position: 'absolute', right: '10px', top: '8px', color: '#ff9800', fontSize: '11px' }}>💡 21</div>
               </div>
            </div>
            <div style={{ background: 'rgba(248,81,73,0.03)', padding: '12px', borderRadius: '10px', border: '1px solid rgba(248,81,73,0.1)' }}>
               <label style={{ color: '#f85149', fontSize: '11px', fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>
                  📉 NIVEL VENTA (Caro)
               </label>
               <div style={{ position: 'relative' }}>
                  <input type="number" step="0.1" className="login-input" style={{ height: '35px', background: 'rgba(248,81,73,0.05)' }} value={botStatus.settings?.sell_rsi} onChange={(e) => updateSettings({ sell_rsi: e.target.value })} disabled={isUpdating} />
                  <div style={{ position: 'absolute', right: '10px', top: '8px', color: '#ff9800', fontSize: '11px' }}>💡 75</div>
               </div>
            </div>
         </div>

         {/* 3. Unified Trend Selector */}
         <div style={{ 
            background: 'linear-gradient(145deg, rgba(88,166,255,0.05), rgba(1,4,9,0.3))', 
            padding: '16px', 
            borderRadius: '12px', 
            border: '1px solid rgba(88,166,255,0.15)',
            marginBottom: '15px'
         }}>
            <label style={{ fontSize: '13px', color: '#58a6ff', fontWeight: 'bold', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
               📏 BASELINE DE TENDENCIA (EMA)
            </label>
            <div style={{ display: 'flex', gap: '10px' }}>
               <select 
                  className="login-input" 
                  style={{ flex: 1, height: '40px', fontSize: '14px' }}
                  value={[100, 200].includes(parseInt(botStatus.settings?.ema_length)) ? botStatus.settings?.ema_length : 'custom'}
                  onChange={(e) => {
                     if (e.target.value !== 'custom') {
                        updateSettings({ ema_length: e.target.value });
                     }
                  }}
                  disabled={isUpdating}
               >
                  <option value="200">EMA 200 (Alta Estabilidad)</option>
                  <option value="100">EMA 100 (Tendencia Media)</option>
                  <option value="custom">Valor Personalizado...</option>
               </select>
               
               {(![100, 200].includes(parseInt(botStatus.settings?.ema_length)) || botStatus.settings?.ema_length === 'custom') && (
                  <input 
                     type="number" 
                     className="login-input" 
                     style={{ width: '90px', height: '40px', fontWeight: 'bold', textAlign: 'center' }}
                     value={botStatus.settings?.ema_length}
                     onChange={(e) => updateSettings({ ema_length: e.target.value })}
                     disabled={isUpdating}
                  />
               )}
            </div>
         </div>

         {/* 4. Professional Filter Module */}
         <div style={{ 
            background: 'rgba(255,255,255,0.01)', 
            padding: '16px', 
            borderRadius: '12px', 
            border: '1px solid rgba(255,255,255,0.03)' 
         }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <label style={{ fontSize: '12px', color: '#ff9800', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px', textTransform: 'uppercase', margin: 0 }}>
                    ⚔️ Filtros de Verificación Senior
                </label>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
               {[
                  { id: 'enable_fast_ema', label: 'Rápida', icon: '⚡' },
                  { id: 'enable_trend_filter', label: 'Tendencia', icon: '📈' },
                  { id: 'enable_vol_filter', label: 'Volumen', icon: '📊' },
                  { id: 'enable_pair_exclusion', label: 'Exclusión', icon: '🚫' }
               ].map(filter => (
                  <div key={filter.id} style={{ position: 'relative' }}>
                    <div 
                        onClick={() => updateSettings({ [filter.id]: !botStatus.settings?.[filter.id] })}
                        style={{ 
                            padding: '10px', 
                            background: botStatus.settings?.[filter.id] ? 'rgba(46,160,67,0.1)' : 'rgba(255,255,255,0.03)',
                            borderRadius: '8px',
                            border: `1px solid ${botStatus.settings?.[filter.id] ? 'rgba(46,160,67,0.3)' : 'rgba(255,255,255,0.05)'}`,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease'
                        }}>
                        <span style={{ fontSize: '14px' }}>{filter.icon}</span>
                        <span style={{ fontSize: '11px', color: botStatus.settings?.[filter.id] ? '#3fb950' : '#848E9C', fontWeight: '600' }}>
                            {filter.label}
                        </span>
                        <div style={{ marginLeft: 'auto', width: '8px', height: '8px', borderRadius: '50%', background: botStatus.settings?.[filter.id] ? '#3fb950' : '#484f58' }}></div>
                    </div>
                  </div>
               ))}
            </div>

            {isProMode && (
               <div style={{ marginTop: '15px', paddingTop: '15px', borderTop: '1px dashed rgba(255,255,255,0.05)' }}>
                  <label style={{ fontSize: '10px', color: '#848E9C', marginBottom: '10px', display: 'block' }}>Ajustes Milimétricos (MACD / Fast EMA)</label>
                  <div className="settings-grid-2">
                     <div className="form-group" style={{ marginBottom: 0 }}>
                        <input type="number" className="login-input" style={{ height: '30px', fontSize: '12px' }} value={botStatus.settings?.macd_fast} onChange={(e) => updateSettings({ macd_fast: e.target.value })} placeholder="MACD Fast" />
                     </div>
                     <div className="form-group" style={{ marginBottom: 0 }}>
                        <input type="number" className="login-input" style={{ height: '30px', fontSize: '12px' }} value={botStatus.settings?.fast_ema_len} onChange={(e) => updateSettings({ fast_ema_len: e.target.value })} placeholder="EMA Rápida" />
                     </div>
                  </div>
               </div>
            )}
         </div>
      </div>
    </AccordionItem>
  );
};

export const ExtraSettings = ({ 
  botStatus, updateSettings, 
  showTelegram, setShowTelegram, 
  showConverter, setShowConverter,
  convertAmount, setConvertAmount,
  tickers, currencyAsset, isUpdating 
}) => {
  const [convertAsset, setConvertAsset] = React.useState(currencyAsset);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0px' }}> {/* Gap handled by Accordion Margin */}
      
      {/* Telegram */}
      <AccordionItem 
        title="Notificaciones Telegram" 
        isOpen={showTelegram} 
        onToggle={() => setShowTelegram(!showTelegram)}
        icon="📱"
        helpText="Conecta el bot con tu celular para recibir alertas de compra y venta en tiempo real."
      >
          <div className="settings-grid-2" style={{ alignItems: 'flex-end', gap: '15px' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Tu Chat ID <HelpTooltip text="Obtén esto del @userinfobot en Telegram." /></label>
                <div style={{ display: 'flex', gap: '5px' }}>
                  <input 
                    type="text" 
                    className="login-input" 
                    placeholder="Ej: 123456789" 
                    value={botStatus.settings?.tg_chat_id || ''}
                    onChange={(e) => updateSettings({ tg_chat_id: e.target.value })}
                    disabled={isUpdating}
                  />
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', height: '35px', background: 'rgba(255,255,255,0.03)', padding: '0 10px', borderRadius: '6px', border: '1px solid var(--border)' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-dim)', cursor: 'pointer' }} htmlFor="tg-switch">Activar</label>
                <input 
                  id="tg-switch"
                  type="checkbox" 
                  checked={botStatus.settings?.telegram_enabled} 
                  onChange={(e) => updateSettings({ telegram_enabled: e.target.checked })}
                  disabled={isUpdating}
                  style={{ width: '16px', height: '16px', cursor: isUpdating ? 'not-allowed' : 'pointer' }}
                />
              </div>
            </div>

            <div style={{ marginTop: '15px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '10px' }}>
                 <p style={{fontSize: '11px', color: '#848E9C', textTransform: 'uppercase', marginBottom: '10px'}}>Umbrales de RSI para Alertas</p>
                 <div className="settings-grid-2">
                    <div className="form-group">
                        <label style={{color: '#ff9800'}}>Comprar (Normal) <HelpTooltip text="Aviso de acercamiento a zona de compra." /></label>
                        <input type="number" className="login-input" value={botStatus.settings?.rsi_alert_buy_normal} onChange={(e) => updateSettings({ rsi_alert_buy_normal: e.target.value })} />
                    </div>
                    <div className="form-group">
                        <label style={{color: 'var(--success)'}}>Comprar (URGENTE) <HelpTooltip text="Señal de entrada definitiva." /></label>
                        <input type="number" className="login-input" value={botStatus.settings?.rsi_alert_buy_urgent} onChange={(e) => updateSettings({ rsi_alert_buy_urgent: e.target.value })} />
                    </div>
                 </div>
                 <div className="settings-grid-2" style={{ marginTop: '10px' }}>
                    <div className="form-group">
                        <label style={{color: '#3B82F6'}}>Vender (Normal) <HelpTooltip text="Aviso de acercamiento a zona de venta." /></label>
                        <input type="number" className="login-input" value={botStatus.settings?.rsi_alert_sell_normal} onChange={(e) => updateSettings({ rsi_alert_sell_normal: e.target.value })} />
                    </div>
                    <div className="form-group">
                        <label style={{color: 'var(--danger)'}}>Vender (URGENTE) <HelpTooltip text="Señal de salida definitiva." /></label>
                        <input type="number" className="login-input" value={botStatus.settings?.rsi_alert_sell_urgent} onChange={(e) => updateSettings({ rsi_alert_sell_urgent: e.target.value })} />
                    </div>
                 </div>
            </div>
      </AccordionItem>

      {/* Conversor */}
      <AccordionItem 
        title="Conversor Rápido (USDT)" 
        isOpen={showConverter} 
        onToggle={() => setShowConverter(!showConverter)}
        icon="🔄"
        helpText="Herramienta rápida para calcular cuánto recibirás al cambiar tus USDT por otras monedas."
      >
            <div className="settings-grid-3">
              <div className="form-group">
                <label>Tengo (USDT)</label>
                <input 
                  type="number" 
                  className="login-input" 
                  value={convertAmount}
                  onChange={(e) => setConvertAmount(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Quiero</label>
                <select 
                  className="login-input"
                  value={convertAsset + "USDT"}
                  onChange={(e) => setConvertAsset(e.target.value.replace('USDT', ''))}
                >
                  {Object.keys(tickers).length > 0 ? (
                    Object.keys(tickers).map(symbol => (
                      <option key={symbol} value={symbol}>{symbol.replace('USDT', '')}</option>
                    ))
                  ) : (
                    <option value={botStatus.symbol}>{currencyAsset}</option>
                  )}
                </select>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', paddingBottom: '10px' }}>
                <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#ff9800', textAlign: 'center' }}>
                  {(convertAmount / (tickers[convertAsset + "USDT"] || botStatus.price || 1)).toFixed(6)}
                </div>
              </div>
            </div>
      </AccordionItem>
    </div>
  );
};

const SettingsPanel = (props) => {
  const currencyAsset = props.botStatus.symbol?.replace('USDT', '') || 'BTC';
  const { isProMode, setProMode } = props; // Received from App
  
  return (
    <div className="settings-container">
       <div style={{marginBottom: '10px'}}>
        <NoviceProSwitch isPro={isProMode} onToggle={() => setProMode(!isProMode)} />
      </div>

      <MarketSettings {...props} />
      <RiskSettings {...props} currencyAsset={currencyAsset} />
      <StrategySettings {...props} />
      <ExtraSettings {...props} currencyAsset={currencyAsset} />
    </div>
  );
};

export default SettingsPanel;
