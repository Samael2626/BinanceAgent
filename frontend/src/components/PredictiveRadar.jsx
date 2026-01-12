import React, { useRef, useEffect } from 'react';

const PredictiveRadar = ({ score, breakoutProb }) => {
    const canvasRef = useRef(null);
    const animationRef = useRef(null);

    // Color Helpers
    const getScoreColor = (s) => {
        if (s >= 70) return '#0ECB81';
        if (s <= 30) return '#F6465D';
        return '#FCD535'; 
    };
    
    // Animation Logic
    useEffect(() => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        let angle = 0;
        
        const render = () => {
            const width = canvas.width;
            const height = canvas.height;
            const centerX = width / 2;
            const centerY = height - 10; // Bottom centered
            const radius = 60;

            const mainColor = getScoreColor(score);

            ctx.clearRect(0, 0, width, height);
            
            // 1. Draw Background Arc (Grey)
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, Math.PI, 0); 
            ctx.lineWidth = 6;
            ctx.strokeStyle = '#2B3139'; // Dark grey
            ctx.lineCap = 'round';
            ctx.stroke();

            // 2. Draw Active Score Arc
            const scoreAngle = Math.PI + (score / 100) * Math.PI;
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, Math.PI, scoreAngle);
            ctx.strokeStyle = mainColor;
            ctx.lineWidth = 6;
            ctx.shadowBlur = 10;
            ctx.shadowColor = mainColor;
            ctx.stroke();
            ctx.shadowBlur = 0;

            // 3. Draw Radar Scan Line
            angle += 0.05; // Speed
            // Constrain scan to semi-circle (PI to 2PI? No, just rotate full or clip?)
            // Let's clip to the semi-circle area
            ctx.save();
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius - 5, Math.PI, 0);
            ctx.closePath();
            ctx.clip(); // Only draw inside the gauge area

            // Draw scanning gradient
            // We rotate the context to 'angle'
            ctx.translate(centerX, centerY);
            
            // Oscillate the scan line between PI (180) and 0 (360/0)
            // But let's just make it rotate continuously and only show when in range? 
            // Better: An oscillating scan from Left to Right.
            const scanAngle = Math.PI + Math.abs(Math.sin(angle) * Math.PI); 
            
            ctx.rotate(scanAngle); 
            
            // Beam
            const gradient = ctx.createLinearGradient(0, 0, radius, 0);
            gradient.addColorStop(0, 'rgba(255, 255, 255, 0)');
            gradient.addColorStop(1, 'rgba(255, 255, 255, 0.3)');
            
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.arc(0, 0, radius, -0.2, 0.2); // Wedge
            ctx.fill();

            // Random "Tech" particles/blips
            if (Math.random() > 0.95) {
                const r = Math.random() * radius;
                ctx.fillStyle = '#fff';
                ctx.fillRect(r, 0, 2, 2);
            }

            ctx.restore();

            // 4. Draw Center Text
            // We do this via HTML overlay mostly, but can do canvas text too.
            // Let's stick to HTML overlay for crisp text, canvas for fx.

            animationRef.current = requestAnimationFrame(render);
        };

        render();

        return () => cancelAnimationFrame(animationRef.current);
    }, [score]);

    return (
        <div className="radar-container" style={{ position: 'relative', width: '150px', height: '90px', display: 'flex', justifyContent: 'center' }}>
            <canvas 
                ref={canvasRef} 
                width={150} 
                height={90} 
                style={{ position: 'absolute', top: 0, left: 0 }}
            />
            
            {/* Overlay Text */}
            <div style={{ position: 'absolute', bottom: '10px', textAlign: 'center', zIndex: 10 }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--text-main)', textShadow: '0 2px 10px rgba(0,0,0,0.5)' }}>
                    {score}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-sec)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                    MARKET SCORE
                </div>
            </div>
        </div>
    );
};

export default PredictiveRadar;
