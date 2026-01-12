import React, { useEffect, useState } from 'react';

// You will need to import the actual images. For now, assuming they are in public or imported.
// Note: Since we generated them into the artifacts folder, we assume the user will move them or we reference them correctly.
// For this environment, we'll assume they are available at specific paths or just use placeholders if not yet moved.
// However, since I generated them, I know their paths in the artifacts folder. 
// I CANNOT strictly import from an absolute path outside src in Vite easily without configuration.
// ideally I should have written them to public/ or src/assets/. 
// I will assume for the code that they are imported from assets.
// I will need to "move" (conceptually) the generated images to the frontend/src/assets folder in a subsequent step or just use the artifact path if allowed (usually not in browser).
// I will write the component to use dynamic imports or props, but for now standard imports.

const Mascot = ({ rsi }) => {
  const [mode, setMode] = useState('neutral'); // neutral, alert
  const [mousePos, setPosition] = useState({ x: 0, y: 0 }); // Define state BEFORE usage

  // Mouse Tracking Logic
  useEffect(() => {
    const handleMouseMove = (e) => {
        // Calculate relative position of mouse (clamped for subtle movement)
        const x = (e.clientX / window.innerWidth - 0.5) * 20; // -10 to 10px
        const y = (e.clientY / window.innerHeight - 0.5) * 10; // -5 to 5px
        
        // Smoothly update position
        setPosition({ x, y });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div 
        className="mascot-container"
        style={{
            position: 'absolute',
            bottom: '0',
            right: '-10px',
            width: '130px', 
            height: '110px', 
            pointerEvents: 'none',
            zIndex: 10,
            overflow: 'visible',
            // Interactive movement
            transform: `translate(${mousePos.x}px, ${mousePos.y}px)`,
            transition: 'transform 0.1s ease-out' 
        }}
    >
        <img 
            src={mode === 'alert' ? alertImg : neutralImg} 
            alt="" 
            style={{
                width: '100%',
                height: 'auto',
                // Blend mode to hide black background
                mixBlendMode: 'screen', // Drops black on dark bg
                filter: 'brightness(1.1) contrast(1.1)', // Slightly pop
                transform: mode === 'alert' ? 'scale(1.1)' : 'scale(1)',
                transition: 'transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)'
            }}
            onError={(e) => { e.target.style.display = 'none'; }} 
        />
        
        {/* Speech Bubble for extreme RSI */}
        {mode === 'alert' && (
             <div className="mascot-bubble" style={{
                 position: 'absolute',
                 top: '-20px',
                 left: '-60px',
                 background: 'var(--panel-bg)',
                 border: '1px solid var(--accent-primary)',
                 padding: '4px 8px',
                 borderRadius: '8px',
                 fontSize: '0.75rem',
                 color: 'var(--text-main)',
                 boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
                 animation: 'fadeIn 0.3s ease'
             }}>
                 {rsi >= 70 ? '¡Sobrecompra!' : '¡Sobreventa!'}
             </div>
        )}
    </div>
  );
};

export default Mascot;
