import React, { useState } from 'react';

const ChartHelp = () => {
    const [isVisible, setIsVisible] = useState(false);

    return (
        <div style={{ position: 'absolute', top: '10px', right: '10px', zIndex: 50 }}>
            <button 
                onClick={() => setIsVisible(!isVisible)}
                style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '20px',
                    padding: '5px 12px',
                    color: '#848E9C',
                    fontSize: '12px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    transition: 'all 0.2s'
                }}
                className="minimal-btn"
            >
                <span>❔ Ayuda Gráfico</span>
            </button>

            {isVisible && (
                <div style={{
                    position: 'absolute',
                    top: '40px',
                    right: '0',
                    width: '300px',
                    background: '#1E2329',
                    border: '1px solid #2B3139',
                    borderRadius: '8px',
                    padding: '15px',
                    boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
                    color: '#EAECEF',
                    fontSize: '13px',
                    lineHeight: '1.5'
                }}>
                    <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom: '10px'}}>
                        <h4 style={{margin:0, color:'#F3BA2F'}}>📖 Guía Rápida</h4>
                        <span onClick={() => setIsVisible(false)} style={{cursor:'pointer', opacity:0.6}}>✕</span>
                    </div>
                    
                    <ul style={{paddingLeft:'20px', margin:0}}>
                        <li style={{marginBottom:'8px'}}>
                            <b>Velas:</b> Muestran el movimiento del precio. <span style={{color:'#0ECB81'}}>Verde (Sube)</span>, <span style={{color:'#F6465D'}}>Rojo (Baja)</span>.
                        </li>
                        <li style={{marginBottom:'8px'}}>
                            <b>Líneas Onduladas:</b> Medias móviles (Tendencia). Si el precio está encima, es alcista.
                        </li>
                        <li style={{marginBottom:'8px'}}>
                            <b>Líneas Punteadas:</b> Proyecciones y zonas de soporte (Piso) y resistencia (Techo).
                        </li>
                        <li>
                            <b>RSI:</b> Indicador de fuerza. Si está muy alto (&gt;70) puede caer. Si está muy bajo (&lt;30) puede subir.
                        </li>
                    </ul>
                </div>
            )}
        </div>
    );
};

export default ChartHelp;
