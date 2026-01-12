import React, { useState } from 'react';

const HelpTooltip = ({ text }) => {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div 
      className="help-tooltip-container"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      style={{ display: 'inline-flex', marginLeft: '6px', position: 'relative', cursor: 'help' }}
    >
      <div style={{ 
        width: '16px', 
        height: '16px', 
        borderRadius: '50%', 
        border: '1px solid #848E9C', 
        color: '#848E9C', 
        fontSize: '10px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        fontWeight: 'bold'
      }}>
        ?
      </div>
      
      {isVisible && (
        <div style={{
          position: 'absolute',
          bottom: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          marginBottom: '8px',
          width: '200px',
          padding: '8px 12px',
          background: '#0B0E11',
          border: '1px solid #2B3139',
          borderRadius: '4px',
          color: '#EAECEF',
          fontSize: '11px',
          lineHeight: '1.4',
          zIndex: 100,
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
          pointerEvents: 'none', // Prevent tooltip from blocking interaction
          textAlign: 'center'
        }}>
          {text}
          <div style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            borderWidth: '5px',
            borderStyle: 'solid',
            borderColor: '#2B3139 transparent transparent transparent'
          }}></div>
        </div>
      )}
    </div>
  );
};

export default HelpTooltip;
