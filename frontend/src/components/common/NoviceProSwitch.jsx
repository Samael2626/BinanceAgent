import React from 'react';

const NoviceProSwitch = ({ isPro, onToggle }) => {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '15px', gap: '10px' }}>
      <span style={{ 
        fontSize: '12px', 
        fontWeight: 'bold', 
        color: !isPro ? '#0ECB81' : '#848E9C',
        transition: 'color 0.3s'
      }}>
        MODO NOVATO
      </span>
      
      <div 
        onClick={onToggle}
        style={{
          width: '50px',
          height: '24px',
          background: '#161A25',
          borderRadius: '12px',
          position: 'relative',
          cursor: 'pointer',
          border: `1px solid ${isPro ? '#00B4C9' : '#0ECB81'}`,
          transition: 'all 0.3s ease'
        }}
      >
        <div style={{
          width: '18px',
          height: '18px',
          background: isPro ? '#00B4C9' : '#0ECB81',
          borderRadius: '50%',
          position: 'absolute',
          top: '2px',
          left: isPro ? '28px' : '2px',
          transition: 'left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: '0 1px 3px rgba(0,0,0,0.5)'
        }}></div>
      </div>
      
      <span style={{ 
        fontSize: '12px', 
        fontWeight: 'bold', 
        color: isPro ? '#00B4C9' : '#848E9C',
        transition: 'color 0.3s'
      }}>
        MODO PRO
      </span>
    </div>
  );
};

export default NoviceProSwitch;
