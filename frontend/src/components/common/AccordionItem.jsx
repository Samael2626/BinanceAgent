import React, { useRef, useEffect, useState } from 'react';

const AccordionItem = ({ title, isOpen, onToggle, children, icon, helpText }) => {
  const contentRef = useRef(null);
  const [height, setHeight] = useState('0px');
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setHeight('0px');
      return;
    }

    // Use ResizeObserver for dynamic content height
    const observer = new ResizeObserver(() => {
      if (contentRef.current && isOpen) {
        setHeight(`${contentRef.current.scrollHeight}px`);
      }
    });

    if (contentRef.current) {
      observer.observe(contentRef.current);
    }

    return () => observer.disconnect();
  }, [isOpen]);

  return (
    <div className="accordion-item" style={{ 
      marginBottom: '10px', 
      background: 'rgba(22, 26, 37, 0.6)', 
      borderRadius: '8px', 
      border: '1px solid rgba(255, 255, 255, 0.05)',
      overflow: 'hidden',
      transition: 'border-color 0.3s ease',
      position: 'relative'
    }}>
      <div 
        className={`accordion-header ${isOpen ? 'active' : ''}`} 
        onClick={(e) => {
            // Prevent toggle if clicking help
            if (e.target.closest('.header-help-btn')) return;
            onToggle();
        }}
        style={{
          padding: '12px 15px',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: isOpen ? 'rgba(255, 255, 255, 0.03)' : 'transparent',
          transition: 'background 0.2s ease',
          userSelect: 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontWeight: 'bold', color: '#EAECEF' }}>
          {icon && <span>{icon}</span>}
          <span>{title}</span>
          {helpText && (
             <div 
                className="header-help-btn"
                onClick={() => setShowHelp(!showHelp)}
                style={{
                    width: '18px', height: '18px', borderRadius: '50%', border: '1px solid #848E9C',
                    color: '#848E9C', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '11px', cursor: 'help', marginLeft: '5px'
                }}
             >
                ?
             </div>
          )}
        </div>
        <div style={{ 
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)', 
          transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          color: '#848E9C',
          fontSize: '12px'
        }}>
          ▼
        </div>
      </div>
      
      {/* Header Help Popup */}
      {showHelp && (
          <div style={{
              padding: '10px 15px',
              background: 'rgba(31, 111, 235, 0.1)',
              borderBottom: '1px solid rgba(255,255,255,0.05)',
              borderTop: '1px solid rgba(255,255,255,0.05)',
              fontSize: '13px',
              color: '#bdc3c7',
              lineHeight: '1.4',
              display: 'flex',
              alignItems: 'start',
              gap: '8px'
          }}>
              <span>💡</span>
              <span>{helpText}</span>
              <span 
                onClick={() => setShowHelp(false)}
                style={{marginLeft: 'auto', cursor: 'pointer', opacity: 0.7}}
              >✕</span>
          </div>
      )}
      
      <div 
        ref={contentRef}
        className="accordion-content"
        style={{
          height: height,
          opacity: isOpen ? 1 : 0,
          transition: 'height 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease',
          overflow: 'hidden'
        }}
      >
        <div style={{ padding: '15px', borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
          {children}
        </div>
      </div>
    </div>
  );
};

export default AccordionItem;
