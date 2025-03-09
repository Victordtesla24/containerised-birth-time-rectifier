import React from 'react';
import { Html, useProgress } from '@react-three/drei';

function LoadingScreen() {
  const { active, progress, item } = useProgress();

  if (!active) return null;

  return (
    <Html center>
      <div style={{
        padding: '20px',
        background: 'rgba(0,0,0,0.8)',
        borderRadius: '10px',
        color: 'white',
        textAlign: 'center'
      }}>
        <h2>Loading celestial data...</h2>
        <div style={{ width: '250px', height: '20px', background: '#111', borderRadius: '10px', margin: '10px 0' }}>
          <div style={{ width: `${progress}%`, height: '100%', background: '#4060ff', borderRadius: '10px' }} />
        </div>
        <div>{Math.round(progress)}%</div>
        <div style={{ fontSize: '12px', opacity: 0.7 }}>{item}</div>
      </div>
    </Html>
  );
}

export default LoadingScreen;
