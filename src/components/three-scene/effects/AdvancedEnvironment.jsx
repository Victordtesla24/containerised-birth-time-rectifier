import React from 'react';
import { Environment, Lightformer } from '@react-three/drei';
import { useQuality } from '../core/QualityContext';

/**
 * Enhanced environment component with scientific accuracy
 * Sets up the scene environment with proper lighting and background
 */
function AdvancedEnvironment() {
  const { qualityLevel } = useQuality();

  // Skip on low quality to save resources
  if (qualityLevel === 'low') {
    return null;
  }

  // Adjust environment complexity based on quality
  const resolution = qualityLevel === 'medium' ? 128 : 256;

  return (
    <>
      <Environment
        preset="night"
        resolution={resolution}
        background={false}
      >
        {/* Only add light source elements on high quality */}
        {qualityLevel === 'high' && (
          <>
            {/* Distant stars as point light sources */}
            <Lightformer
              form="circle"
              intensity={0.5}
              position={[10, 10, 10]}
              scale={10}
              color="#557799"
            />
            <Lightformer
              form="circle"
              intensity={0.3}
              position={[-10, 5, -10]}
              scale={5}
              color="#445577"
            />

            {/* Galactic plane subtle glow */}
            <Lightformer
              form="ring"
              intensity={0.1}
              position={[0, 0, 10]}
              scale={20}
              color="#334455"
              rotation-x={Math.PI / 2}
            />
          </>
        )}
      </Environment>
    </>
  );
}

export default AdvancedEnvironment;
