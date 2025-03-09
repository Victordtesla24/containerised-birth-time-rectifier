import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';
import { useQuality } from '../core/QualityContext';

/**
 * Improved lighting system with scientific accuracy and optimization
 * Provides physically correct lighting for the celestial scene
 */
const SceneLighting = () => {
  const lightRef = useRef();
  const { qualityLevel } = useQuality();

  // Optimize lighting setup
  useEffect(() => {
    if (lightRef.current) {
      // Configure shadow settings for better performance
      lightRef.current.shadow.bias = -0.001; // Reduce shadow acne
      lightRef.current.shadow.radius = 4; // Soften shadows

      // Adapt shadow settings based on quality level
      if (qualityLevel === 'low') {
        lightRef.current.shadow.mapSize.width = 1024;
        lightRef.current.shadow.mapSize.height = 1024;
        lightRef.current.shadow.camera.far = 40;
      } else if (qualityLevel === 'medium') {
        lightRef.current.shadow.mapSize.width = 2048;
        lightRef.current.shadow.mapSize.height = 2048;
        lightRef.current.shadow.camera.far = 50;
      } else {
        lightRef.current.shadow.mapSize.width = 4096;
        lightRef.current.shadow.mapSize.height = 4096;
        lightRef.current.shadow.camera.far = 60;
      }

      // Update shadow camera
      lightRef.current.shadow.camera.updateProjectionMatrix();
    }
  }, [qualityLevel]);

  return (
    <>
      {/* Ambient light with proper physical values */}
      <ambientLight intensity={0.02} color="#050508" />

      {/* Main directional light with scientific sun color temperature (5778K) */}
      <directionalLight
        ref={lightRef}
        position={[15, 8, 10]}
        intensity={0.3}
        color="#f8f2e8"
        castShadow={qualityLevel !== 'low'} // Disable shadows on low quality
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-far={50}
        shadow-camera-left={-25}
        shadow-camera-right={25}
        shadow-camera-top={25}
        shadow-camera-bottom={-25}
      />

      {/* Hemisphere light for scientifically accurate ambient lighting */}
      <hemisphereLight
        skyColor="#b0c0ff" // Deep space color
        groundColor="#102030" // Shadow side color
        intensity={0.05}
      />

      {/* Central point light for the sun */}
      <pointLight
        position={[0, 0, -5]}
        intensity={1.2}
        color="#fff5d8" // Solar spectrum color
        distance={120}
        decay={2} // Physically correct inverse square law
        castShadow={false} // Disable for performance
      />
    </>
  );
};

export default SceneLighting;
