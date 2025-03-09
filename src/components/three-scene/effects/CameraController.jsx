import React, { useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useQuality } from '../core/QualityContext';

/**
 * Camera controller component for handling camera interaction and animation
 * Manages camera position, parallax, and orbital controls
 */
function CameraController({ mousePosition }) {
  const { camera } = useThree();
  const { qualityLevel } = useQuality();

  // Dynamic camera settings based on quality
  useEffect(() => {
    if (camera) {
      // Optimize camera settings
      camera.far = qualityLevel === 'low' ? 200 : 1000;
      camera.updateProjectionMatrix();
    }
  }, [camera, qualityLevel]);

  // Apply parallax effect based on mouse position
  useFrame(() => {
    if (camera && mousePosition) {
      // Smooth camera movement based on mouse position
      const targetX = (mousePosition.x * 0.1);
      const targetY = (mousePosition.y * 0.1);

      // Apply smoothing
      camera.position.x += (targetX - camera.position.x) * 0.05;
      camera.position.y += (targetY - camera.position.y) * 0.05;

      // Always look at the center
      camera.lookAt(0, 0, 0);
    }
  });

  return (
    <OrbitControls
      enableZoom={false}
      enablePan={false}
      enableRotate={false}
      minPolarAngle={Math.PI / 2}
      maxPolarAngle={Math.PI / 2}
    />
  );
}

export default CameraController;
