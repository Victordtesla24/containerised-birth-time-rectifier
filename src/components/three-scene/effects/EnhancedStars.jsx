import React, { useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { useQuality } from '../core/QualityContext';

/**
 * Enhanced stars with depth effect
 * Renders a starfield with parallax motion
 */
function EnhancedStars() {
  const { qualityLevel } = useQuality();
  const { camera } = useThree();
  const starsRef = useRef();

  // Configure stars count based on quality
  const starCount = useMemo(() => {
    switch (qualityLevel) {
      case 'low': return 1000;
      case 'medium': return 3000;
      case 'high': return 5000;
      case 'ultra': return 8000;
      default: return 3000;
    }
  }, [qualityLevel]);

  // Parallax effect for stars based on camera movement
  useFrame(() => {
    if (starsRef.current && camera) {
      // Subtle rotation for ambient movement
      starsRef.current.rotation.y += 0.0001;
      starsRef.current.rotation.x += 0.00005;
    }
  });

  return (
    <Stars
      ref={starsRef}
      radius={100}
      depth={50}
      count={starCount}
      factor={4}
      saturation={0.6}
      fade
      speed={1}
    />
  );
}

export default EnhancedStars;
