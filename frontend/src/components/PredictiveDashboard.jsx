import React from 'react';
import AccordionItem from './common/AccordionItem';

const PredictiveDashboard = ({ prediction, isOpen, onToggle }) => {
    if (!prediction) return null;

    const { 
        rvol, 
        breakout_prob, 
        speed, 
        session, 
        market_score, 
        summary,
        liquidity_zones,
        traps,
        divergences,
        fear_greed,
        smart_money,
        volatility,
        trend_strength
    } = prediction;
    
    // Sentiment Logic
    const getSentiment = (score) => {
        if (score >= 70) return { label: 'EXTREMA CODICIA', emoji: '🤑', color: '#0ECB81' };
        if (score >= 55) return { label: 'CODICIA', emoji: '📈', color: '#70E000' };
        if (score <= 30) return { label: 'EXTREMO MIEDO', emoji: '😨', color: '#F6465D' };
        if (score <= 45) return { label: 'MIEDO', emoji: '📉', color: '#FF7D00' };
        return { label: 'NEUTRAL', emoji: '⚖️', color: '#FCD535' };
    };

    const sentiment = getSentiment(fear_greed?.score || market_score);

    // Range Logic
    const hasLiquidity = liquidity_zones && liquidity_zones.support && liquidity_zones.target;
    let rangePercent = 0;
    if (hasLiquidity) {
        const { support, target } = liquidity_zones;
        const current = prediction.current_price || (support + target) / 2;
        rangePercent = Math.min(100, Math.max(0, ((current - support) / (target - support)) * 100));
    }

    return (
        <div style={{ position: 'relative' }}>
            <AccordionItem 
                title="Cerebro Predictivo PRO" 
                isOpen={isOpen} 
                onToggle={onToggle} 
                icon="🧠"
                helpText="Analítica institucional y técnica avanzada."
            >
                <div style={containerStyle}>
                    
                    {/* Top Section: Sentiment & Institutional Flow */}
                    <div style={topInfoGrid}>
                        <div style={headerRowStyle}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <div style={{ ...scoreCircleStyle, borderColor: sentiment.color, boxShadow: `0 0 10px ${sentiment.color}44` }}>
                                    {fear_greed?.score || market_score}
                                </div>
                                <div>
                                    <div style={{ ...sentimentLabelStyle, color: sentiment.color }}>
                                        {sentiment.label} {sentiment.emoji}
                                    </div>
                                    <div style={tinyLabelStyle}>SENTIMIENTO (FEAR & GREED)</div>
                                </div>
                            </div>
                        </div>

                        <div style={{ ...headerRowStyle, borderLeft: `4px solid ${smart_money?.includes('Compra') ? '#0ECB81' : (smart_money?.includes('Venta') ? '#F6465D' : '#848E9C')}` }}>
                            <div style={tinyLabelStyle}>FLUJO INSTITUCIONAL</div>
                            <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#EAECEF' }}>{smart_money || 'NEUTRAL'}</div>
                        </div>
                    </div>

                    {/* Technical Matrix */}
                    <div style={metricsBarGrid}>
                        <MetricPill label="TENDENCIA" value={trend_strength?.label} subValue={`${trend_strength?.score}%`} color={trend_strength?.score > 60 ? '#0ECB81' : '#848E9C'} />
                        <MetricPill label="VOLATILIDAD" value={volatility?.status} subValue={`ATR: ${volatility?.value?.toFixed(2)}`} color={volatility?.status?.includes('Alta') ? '#F6465D' : '#848E9C'} />
                        <MetricPill label="RUPTURA" value={`${breakout_prob}%`} subValue={breakout_prob > 60 ? 'ALTA' : 'BAJA'} color={breakout_prob > 60 ? '#00B4C9' : '#848E9C'} />
                    </div>

                    {/* Liquidity Range (Crucial Visual) */}
                    {hasLiquidity && (
                        <div style={liquidityBoxStyle}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                <div style={liquidityLabelStyle}>
                                    <span style={{opacity: 0.6}}>SUP:</span> ${liquidity_zones.support?.toLocaleString()}
                                </div>
                                <div style={liquidityLabelStyle}>
                                    <span style={{opacity: 0.6}}>OBJ:</span> ${liquidity_zones.target?.toLocaleString()}
                                </div>
                            </div>
                            <div style={liquidityBarStyle}>
                                <div style={{ ...liquidityFillStyle, width: `${rangePercent}%`, background: sentiment.color }} />
                                <div style={{ ...priceMarkerStyle, left: `${rangePercent}%` }} />
                            </div>
                            <div style={{...tinyLabelStyle, textAlign: 'center', marginTop: '6px', fontSize: '8px'}}>POSICIÓN EN RANGO DINÁMICO</div>
                        </div>
                    )}

                    {/* Detection Badges */}
                    {(traps?.length > 0 || divergences?.length > 0 || rvol > 1.2) && (
                        <div style={signalsRowStyle}>
                            {rvol > 1.2 && <div style={{ ...signalPillStyle, background: '#FCD53522', color: '#FCD535', borderColor: '#FCD53544' }}>⚡ VOLUMEN ANORMAL ({rvol}x)</div>}
                            {divergences?.map((d, i) => (
                                <div key={`div-${i}`} style={signalPillStyle}>⚠️ {d.label}</div>
                            ))}
                            {traps?.map((t, i) => (
                                <div key={`trap-${i}`} style={{ ...signalPillStyle, background: '#F6465D22', color: '#F6465D', borderColor: '#F6465D44' }}>🚨 {t}</div>
                            ))}
                        </div>
                    )}

                    {/* Tactical summary */}
                    {summary && (
                        <div style={summaryBoxStyle}>
                            <div style={summaryLabelStyle}>NOTAS TÁCTICAS DEL ANALISTA</div>
                            <div style={summaryTextStyle}>{summary}</div>
                        </div>
                    )}

                </div>
            </AccordionItem>
        </div>
    );
};

const MetricPill = ({ label, value, subValue, color }) => (
    <div style={metricPillStyle}>
        <span style={tinyLabelStyle}>{label}</span>
        <span style={{ fontSize: '16px', fontWeight: '900', color: color || '#EAECEF', fontFamily: 'Roboto Mono, monospace', margin: '4px 0' }}>{value || '-'}</span>
        <span style={{ fontSize: '12px', opacity: 0.7, color }}>{subValue}</span>
    </div>
);

// Styles
const containerStyle = {
    padding: '12px 10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    background: 'rgba(20, 21, 26, 0.4)',
    backdropFilter: 'blur(10px)'
};

const topInfoGrid = {
    display: 'grid',
    gridTemplateColumns: '1.4fr 1fr',
    gap: '16px'
};

const headerRowStyle = {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    background: 'linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
    padding: '12px 16px',
    borderRadius: '12px',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    boxShadow: '0 4px 15px rgba(0,0,0,0.4)'
};

const scoreCircleStyle = {
    width: '56px',
    height: '56px',
    borderRadius: '50%',
    border: '3px solid',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '24px',
    fontWeight: '950',
    background: 'rgba(0,0,0,0.5)',
    fontFamily: 'Roboto Mono, monospace',
    marginRight: '12px'
};

const sentimentLabelStyle = {
    fontSize: '17px',
    fontWeight: '900',
    letterSpacing: '0.5px',
    lineHeight: '1.2'
};

const tinyLabelStyle = {
    fontSize: '11px',
    color: '#848E9C',
    fontWeight: '900',
    textTransform: 'uppercase',
    letterSpacing: '1.5px',
    marginBottom: '4px'
};

const metricsBarGrid = {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '16px'
};

const metricPillStyle = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    background: 'rgba(255,255,255,0.03)',
    padding: '12px 8px',
    borderRadius: '12px',
    border: '1px solid rgba(255,255,255,0.08)',
    transition: 'all 0.3s ease',
    cursor: 'default'
};

const liquidityBoxStyle = {
    background: 'linear-gradient(90deg, rgba(0,0,0,0.4) 0%, rgba(255,255,255,0.02) 50%, rgba(0,0,0,0.4) 100%)',
    padding: '24px 20px',
    borderRadius: '16px',
    border: '1px solid rgba(255,255,255,0.1)',
    position: 'relative',
    overflow: 'hidden'
};

const liquidityLabelStyle = {
    fontSize: '15px',
    fontWeight: '900',
    color: '#EAECEF',
    fontFamily: 'Roboto Mono, monospace'
};

const liquidityBarStyle = {
    width: '100%',
    height: '12px',
    background: 'rgba(255,255,255,0.05)',
    borderRadius: '6px',
    position: 'relative',
    margin: '16px 0',
    boxShadow: 'inset 0 0 10px rgba(0,0,0,0.5)'
};

const liquidityFillStyle = {
    height: '100%',
    borderRadius: '6px',
    opacity: 0.3,
    transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
    boxShadow: '0 0 20px inherit'
};

const priceMarkerStyle = {
    position: 'absolute',
    top: '-10px',
    width: '4px',
    height: '32px',
    background: '#fff',
    borderRadius: '2px',
    boxShadow: '0 0 15px rgba(255,255,255,0.8), 0 0 30px rgba(255,255,255,0.4)',
    transition: 'left 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
    zIndex: 2
};

const signalsRowStyle = {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px',
    justifyContent: 'center'
};

const signalPillStyle = {
    fontSize: '13px',
    padding: '6px 16px',
    background: 'rgba(0, 180, 201, 0.15)',
    color: '#00B4C9',
    borderRadius: '8px',
    fontWeight: '900',
    border: '1px solid rgba(0, 180, 201, 0.4)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
};

const summaryBoxStyle = {
    padding: '20px 24px',
    background: 'linear-gradient(135deg, rgba(252, 213, 53, 0.12) 0%, rgba(0,0,0,0.3) 100%)',
    borderRadius: '16px',
    borderLeft: '6px solid #FCD535',
    boxShadow: '0 10px 30px rgba(0,0,0,0.3)'
};

const summaryLabelStyle = {
    fontSize: '12px',
    color: '#FCD535',
    marginBottom: '10px',
    fontWeight: '950',
    letterSpacing: '2px',
    textShadow: '0 0 10px rgba(252, 213, 53, 0.3)'
};

const summaryTextStyle = {
    fontSize: '14px',
    color: '#EAECEF',
    lineHeight: '1.7',
    whiteSpace: 'pre-line',
    fontWeight: '500',
    fontStyle: 'normal'
};

export default PredictiveDashboard;
