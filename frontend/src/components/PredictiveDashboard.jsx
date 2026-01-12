import React from 'react';
import AccordionItem from './common/AccordionItem';
import PredictiveRadar from './PredictiveRadar';
import Mascot from './Mascot';

const PredictiveDashboard = ({ prediction, isOpen, onToggle }) => {
    if (!prediction) return null;

    const { rvol, breakout_prob, speed, session, market_score, rsi } = prediction; // Ensure RSI is passed or get from parent? 
    // Wait, 'prediction' object might not have RSI if it comes from different part of state. 
    // In App.jsx, 'botStatus.rsi' is separate. 
    // We should probably pass RSI as a prop or ensure it's in prediction.
    // For now, I'll assume passing 'rsi' prop to this component from App.jsx is better.
    
    // Helper for colors
    const getScoreColor = (score) => {
        if (score >= 70) return '#0ECB81'; // Green
        if (score <= 30) return '#F6465D'; // Red
        return '#FCD535'; // Yellow
    };

    const scoreColor = getScoreColor(market_score);

    return (
        <div style={{ position: 'relative' }}> {/* Wrapper for Mascot positioning */}
            <AccordionItem 
                title="Módulo Predictivo" 
                isOpen={isOpen} 
                onToggle={onToggle} 
                icon="🔮"
                helpText="Análisis avanzado: Volumen inteligente, probabilidad de ruptura y sesión activa."
            >
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                    gap: '15px',
                    padding: '10px 5px',
                    alignItems: 'center'
                }}>
                    
                    {/* 1. Radar Visual - Replaces simple bar */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                         <PredictiveRadar score={market_score} breakoutProb={breakout_prob} />
                    </div>

                    {/* 2. Metrics Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                        {/* Breakout Prob Text */}
                        <div style={cardStyle}>
                            <div style={labelStyle}>Breakout Prob</div>
                            <div style={{ ...valueStyle, color: '#00B4C9' }}>
                                {breakout_prob ?? 0}%
                            </div>
                        </div>

                        {/* Speed */}
                        <div style={cardStyle}>
                            <div style={labelStyle}>Price Speed</div>
                            <div style={{ ...valueStyle, color: speed?.includes('+') ? '#0ECB81' : '#F6465D' }}>
                                {speed ?? '-'}
                            </div>
                        </div>

                        {/* RVOL */}
                        <div style={cardStyle}>
                            <div style={labelStyle}>RVOL</div>
                            <div style={{ ...valueStyle, color: rvol > 1.5 ? '#0ECB81' : '#EAECEF' }}>
                                {rvol?.toFixed(2) ?? '-'}
                            </div>
                        </div>

                         {/* Session */}
                         <div style={cardStyle}>
                            <div style={labelStyle}>Session</div>
                            <div style={{ ...valueStyle, fontSize: '14px', color: '#FCD535' }}>
                                {session ?? 'GLOBAL'}
                            </div>
                        </div>
                    </div>

                </div>
            </AccordionItem>
            
            {/* Mascot - Lives outside Accordion content but inside this relative wrapper? 
                Actually, user said "bottom right of predictive module". 
                If accordion is closed, mascot should probably hide or verify? 
                "Nunca tapa datos" -> If inside accordion, it hides when closed.
                If outside, it stays. 
                Let's put it inside the AccordionItem children so it collapses with it.
                But wait, Mascot has absolute position. 
                If I put it inside the AccordionItem children div, it will be clipped if overflow hidden.
                Yes, AccordionItem has overflow hidden.
                So Mascot must be inside.
                But I need to pass RSI.
            */}
            {/* Mascot removed per user request */}
            {/* {isOpen && <Mascot rsi={prediction.rsi || 50} />} */} 
        </div>
    );
};

// Styles
const cardStyle = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '5px',
    textAlign: 'center',
    background: 'rgba(255,255,255,0.02)',
    padding: '10px',
    borderRadius: '8px',
    border: '1px solid var(--panel-border)'
};

const labelStyle = {
    fontSize: '10px',
    color: '#848E9C',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
};

const valueStyle = {
    fontSize: '18px',
    fontWeight: 'bold',
    fontFamily: 'Roboto, sans-serif'
};

export default PredictiveDashboard;
