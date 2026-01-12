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

        {/* Advanced Modes - Now always visible per user request */}
         <div className="settings-grid-2" style={{ margin: '15px 0' }}>
           <button 
             className={`login-btn ${botStatus.settings?.sniper_mode ? 'active' : ''}`}
             style={{ height: '35px', padding: '0 10px', fontSize: '0.8rem', background: botStatus.settings?.sniper_mode ? '#ff9800' : 'rgba(255,152,0,0.1)', color: botStatus.settings?.sniper_mode ? 'black' : '#ff9800', border: '1px solid #ff9800' }}
             onClick={() => botStatus.settings?.sniper_mode ? updateSettings({ sniper_mode: false }) : setShowSniperModal(true)}
           >
             {botStatus.settings?.sniper_mode ? '🎯 SNIPER ON' : '🎯 Sniper Mode'}
           </button>
           <button 
             className={`login-btn ${botStatus.settings?.trailing_enabled ? 'active' : ''}`}
             style={{ height: '35px', padding: '0 10px', fontSize: '0.8rem', background: botStatus.settings?.trailing_enabled ? '#2ea043' : 'rgba(46,160,67,0.1)', color: botStatus.settings?.trailing_enabled ? 'white' : '#3fb950', border: '1px solid #2ea043' }}
             onClick={() => botStatus.settings?.trailing_enabled ? updateSettings({ trailing_enabled: false }) : setShowTrailingModal(true)}
           >
             {botStatus.settings?.trailing_enabled ? '🚀 TRAILING ON' : '🚀 Trailing Stop'}
           </button>
         </div>
        
        {/* SL/TP */}
        <div className="settings-grid-2" style={{ background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: '8px', marginTop: '10px' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{color: '#f85149', fontSize: '0.75rem'}}>Máx Pérdida % (SL) <HelpTooltip text="Vende automáticamente si pierdes este porcentaje para protegerte." /> <span style={{ color: '#ff9800', fontSize: '10px' }}>[💡 3.2]</span></label>
            <input 
                type="number" 
                step="0.01"
                className={`login-input ${stopLoss > 10 ? 'input-danger' : ''}`} 
                style={{ height: '30px' }} 
                value={botStatus.settings?.stop_loss_pct} 
                onChange={(e) => updateSettings({ stop_loss_pct: e.target.value })} 
            />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{color: '#3fb950', fontSize: '0.75rem'}}>Ganancia Objetivo % (TP) <HelpTooltip text="Vende automáticamente cuando ganas este porcentaje." /> <span style={{ color: '#ff9800', fontSize: '10px' }}>[💡 1.3]</span></label>
            <input 
                type="number" 
                step="0.01"
                className="login-input" 
                style={{ height: '30px' }} 
                value={botStatus.settings?.take_profit_pct} 
                onChange={(e) => updateSettings({ take_profit_pct: e.target.value })} 
            />
          </div>
        </div>

      </div>
    </AccordionItem>
    );
};

export const StrategySettings = ({ botStatus, updateSettings, showStrategy, setShowStrategy, isUpdating, isProMode }) => (
    <AccordionItem 
      title="Estrategia de Trading" 
      isOpen={showStrategy} 
      onToggle={() => setShowStrategy(!showStrategy)}
      icon="📊"
      helpText="Selecciona la lógica de inteligencia que usará el bot para decidir cuándo comprar o vender."
    >
       <div style={{ padding: '0 5px' }}>
        <div style={{ marginBottom: '10px' }}>
             <p style={{fontSize: '12px', color: '#848E9C', marginBottom: '8px'}}>Define las reglas inteligentes que usa el bot para entrar y salir.</p>
        </div>

        <div className="form-group">
          <label>Modelo de Inteligencia <HelpTooltip text="La lógica principal que decide cuándo comprar." /></label>
          <select 
            className="login-input" 
            value={botStatus.settings?.active_strategy || 'rsi'} 
            onChange={(e) => updateSettings({ active_strategy: e.target.value })}
            disabled={isUpdating}
          >
            <option value="rsi">RSI Estándar (Recomendado Novatos)</option>
            <option value="ema_rsi">Tendencia + RSI</option>
            <option value="multi">Multi-Indicador (Precisión)</option>
            <option value="rebound">Rebote (Contra-Tendencia)</option>
            <option value="scalper_pro">Scalper-PRO (Agresivo)</option>
          </select>
        </div>

        <div className="settings-grid-2">
          <div className="form-group">
            <label>Nivel Compra (RSI) <HelpTooltip text="Valor bajo (ej: 30) indica 'barato'. El bot intentará comprar aquí." /> <span style={{ color: '#ff9800', fontSize: '10px' }}>[💡 21]</span></label>
            <input type="number" step="0.1" className="login-input" value={botStatus.settings?.buy_rsi} onChange={(e) => updateSettings({ buy_rsi: e.target.value })} disabled={isUpdating} />
          </div>
          <div className="form-group">
            <label>Nivel Venta (RSI) <HelpTooltip text="Valor alto (ej: 70) indica 'caro'. El bot intentará vender aquí." /> <span style={{ color: '#ff9800', fontSize: '10px' }}>[💡 75]</span></label>
            <input type="number" step="0.1" className="login-input" value={botStatus.settings?.sell_rsi} onChange={(e) => updateSettings({ sell_rsi: e.target.value })} disabled={isUpdating} />
          </div>
        </div>

        {isProMode && (
          <>
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', margin: '10px 0', padding: '10px 0' }}>
                 <label style={{ fontSize: '11px', color: '#848E9C', textTransform: 'uppercase', marginBottom: '10px', display: 'block' }}>Configuración Avanzada de Indicadores</label>
                 <div className="settings-grid-3">
                    <div className="form-group">
                        <label>EMA Len</label>
                        <input type="number" className="login-input" value={botStatus.settings?.ema_length} onChange={(e) => updateSettings({ ema_length: e.target.value })} disabled={isUpdating} />
                    </div>
                     <div className="form-group">
                        <label>MACD Fast</label>
                        <input type="number" className="login-input" value={botStatus.settings?.macd_fast} onChange={(e) => updateSettings({ macd_fast: e.target.value })} disabled={isUpdating} />
                    </div>
                    <div className="form-group">
                        <label>MACD Slow</label>
                        <input type="number" className="login-input" value={botStatus.settings?.macd_slow} onChange={(e) => updateSettings({ macd_slow: e.target.value })} disabled={isUpdating} />
                    </div>
                 </div>
            </div>

            <div style={{ padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', marginTop: '10px' }}>
                 <label style={{ fontSize: '11px', color: '#848E9C', textTransform: 'uppercase', marginBottom: '10px', display: 'block' }}>Filtros Cuantitativos Senior</label>
                 <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                     <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                         <span style={{ fontSize: '12px' }}>Filtro Tendencial (EMA200) <HelpTooltip text="Solo compra si el precio está arriba de la tendencia principal." /></span>
                         <input type="checkbox" checked={botStatus.settings?.enable_trend_filter} onChange={(e) => updateSettings({ enable_trend_filter: e.target.checked })} />
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                         <span style={{ fontSize: '12px' }}>Filtro de Volumen (SMA20) <HelpTooltip text="Solo compra si hay volumen mayor al promedio." /></span>
                         <input type="checkbox" checked={botStatus.settings?.enable_vol_filter} onChange={(e) => updateSettings({ enable_vol_filter: e.target.checked })} />
                     </div>
                     <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                         <span style={{ fontSize: '12px' }}>Exclusión Mutua (BTC/SOL) <HelpTooltip text="Evita abrir BTC y SOL al mismo tiempo para no sobre-apalancar capital." /></span>
                         <input type="checkbox" checked={botStatus.settings?.enable_mutual_exclusion} onChange={(e) => updateSettings({ enable_mutual_exclusion: e.target.checked })} />
                     </div>
                 </div>
            </div>
          </>
        )}
      </div>
    </AccordionItem>
);

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
