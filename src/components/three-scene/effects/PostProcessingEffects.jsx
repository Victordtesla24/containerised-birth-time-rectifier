import React, { Suspense, useState, useEffect } from 'react';
import { useThree } from '@react-three/fiber';
import * as THREE from 'three';
import ErrorBoundary from '../../../components/ErrorBoundary';
import { useQuality } from '../core/QualityContext';
import dynamic from 'next/dynamic';

// Import postprocessing components dynamically with better error handling
const DynamicEffectComposer = dynamic(
  () => import('@react-three/postprocessing')
    .then(mod => {
      if (!mod || !mod.EffectComposer) {
        console.warn('EffectComposer module not fully loaded');
        throw new Error('EffectComposer unavailable');
      }
      return mod.EffectComposer;
    })
    .catch(err => {
      console.error('Failed to load EffectComposer:', err);
      return () => null; // Return empty component on error
    }),
  { ssr: false, suspense: true }
);

const DynamicBloom = dynamic(
  () => import('@react-three/postprocessing')
    .then(mod => {
      if (!mod || !mod.Bloom) {
        console.warn('Bloom module not fully loaded');
        throw new Error('Bloom unavailable');
      }
      return mod.Bloom;
    })
    .catch(err => {
      console.error('Failed to load Bloom:', err);
      return () => null;
    }),
  { ssr: false, suspense: true }
);

const DynamicToneMapping = dynamic(
  () => import('@react-three/postprocessing')
    .then(mod => {
      if (!mod || !mod.ToneMapping) {
        throw new Error('ToneMapping unavailable');
      }
      return mod.ToneMapping;
    })
    .catch(err => {
      console.error('Failed to load ToneMapping:', err);
      return () => null;
    }),
  { ssr: false, suspense: true }
);

const DynamicVignette = dynamic(
  () => import('@react-three/postprocessing')
    .then(mod => {
      if (!mod || !mod.Vignette) {
        throw new Error('Vignette unavailable');
      }
      return mod.Vignette;
    })
    .catch(err => {
      console.error('Failed to load Vignette:', err);
      return () => null;
    }),
  { ssr: false, suspense: true }
);

const DynamicSMAA = dynamic(
  () => import('@react-three/postprocessing')
    .then(mod => {
      if (!mod || !mod.SMAA) {
        throw new Error('SMAA unavailable');
      }
      return mod.SMAA;
    })
    .catch(err => {
      console.error('Failed to load SMAA:', err);
      return () => null;
    }),
  { ssr: false, suspense: true }
);

const DynamicDepthOfField = dynamic(
  () => import('@react-three/postprocessing')
    .then(mod => {
      if (!mod || !mod.DepthOfField) {
        throw new Error('DepthOfField unavailable');
      }
      return mod.DepthOfField;
    })
    .catch(err => {
      console.error('Failed to load DepthOfField:', err);
      return () => null;
    }),
  { ssr: false, suspense: true }
);

// Dynamic import for ChromaticAberration
const DynamicChromaticAberration = dynamic(
  () => import('@react-three/postprocessing')
    .then(mod => {
      if (!mod || !mod.ChromaticAberration) {
        throw new Error('ChromaticAberration unavailable');
      }
      return mod.ChromaticAberration;
    })
    .catch(err => {
      console.error('Failed to load ChromaticAberration:', err);
      return () => null;
    }),
  { ssr: false, suspense: true }
);

// Dynamic import for SSAO (Screen Space Ambient Occlusion)
const DynamicSSAO = dynamic(
  () => import('@react-three/postprocessing')
    .then(mod => {
      if (!mod || !mod.SSAO) {
        throw new Error('SSAO unavailable');
      }
      return mod.SSAO;
    })
    .catch(err => {
      console.error('Failed to load SSAO:', err);
      return () => null;
    }),
  { ssr: false, suspense: true }
);

// Import BlendFunction directly for more control
import { BlendFunction } from 'postprocessing';

/**
 * Enhanced post-processing effects component with professional-grade settings
 * Applies cinematic visual effects based on quality level for a polished appearance
 */
function PostProcessingEffects() {
  const { qualityLevel, effectsEnabled } = useQuality();
  const [modulesLoaded, setModulesLoaded] = useState(false);
  const { size } = useThree();

  // Check if required modules are available
  useEffect(() => {
    const checkModulesAvailable = async () => {
      try {
        // Try to load the postprocessing module to verify availability
        const postprocessing = await import('@react-three/postprocessing');
        if (postprocessing &&
            typeof postprocessing.EffectComposer === 'function' &&
            typeof postprocessing.Bloom === 'function') {
          setModulesLoaded(true);
        } else {
          console.warn('Some postprocessing modules not available');
          setModulesLoaded(false);
        }
      } catch (error) {
        console.error('Failed to load postprocessing modules:', error);
        setModulesLoaded(false);
      }
    };

    checkModulesAvailable();
  }, []);

  // Skip effects on low quality, when disabled, or when modules aren't loaded
  if (!effectsEnabled || !modulesLoaded) {
    return null;
  }

  // Adaptive settings based on quality level
  const bloomIntensity = qualityLevel === 'low' ? 0.4 :
                      qualityLevel === 'medium' ? 0.6 :
                      qualityLevel === 'high' ? 0.8 : 1.0;

  const bloomRadius = qualityLevel === 'low' ? 0.5 :
                    qualityLevel === 'medium' ? 0.65 :
                    qualityLevel === 'high' ? 0.8 : 1.0;

  const chromaticOffset = qualityLevel === 'low' ? 0.0003 :
                        qualityLevel === 'medium' ? 0.0004 :
                        qualityLevel === 'high' ? 0.0005 : 0.0006;

  return (
    <ErrorBoundary fallback={null}>
      <Suspense fallback={null}>
        {modulesLoaded && (
          <DynamicEffectComposer
            multisampling={qualityLevel === 'ultra' ? 8 : qualityLevel === 'high' ? 4 : qualityLevel === 'medium' ? 2 : 0}
            frameBufferType={THREE.HalfFloatType}
            disableNormalPass={qualityLevel === 'low'} // Skip normal pass on low quality
          >
            {/* Enhanced Bloom effect - more natural and realistic glow with better physics-based settings */}
            <DynamicBloom
              intensity={bloomIntensity}
              radius={bloomRadius}
              luminanceThreshold={0.65} // Lower threshold to catch more bright areas
              luminanceSmoothing={0.9}
              mipmapBlur={true} // Enable mipmap-based blur for better quality on high settings
              resolutionScale={qualityLevel === 'ultra' ? 1 : 0.5} // Higher resolution for ultra quality
            />

            {/* Add more sophisticated depth of field on medium+ quality */}
            {qualityLevel !== 'low' && (
              <DynamicDepthOfField
                focusDistance={10.0} // Focus on the planets
                focalLength={0.12}
                bokehScale={qualityLevel === 'ultra' ? 8 : qualityLevel === 'high' ? 5 : 3}
                height={size.height}
              />
            )}

            {/* Add chromatic aberration for better edge effects on medium+ quality */}
            {qualityLevel !== 'low' && (
              <DynamicChromaticAberration
                offset={[chromaticOffset, chromaticOffset]} // Subtle RGB splitting
                radialModulation={true}
                modulationOffset={0.5}
              />
            )}

            {/* Add SSAO for better depth perception on high+ quality */}
            {(qualityLevel === 'high' || qualityLevel === 'ultra') && (
              <DynamicSSAO
                blendFunction={BlendFunction.MULTIPLY}
                samples={qualityLevel === 'ultra' ? 32 : 16}
                radius={0.5}
                intensity={25}
                rings={3}
                distanceThreshold={1.0}
                distanceFalloff={0.0}
                rangeThreshold={0.5}
                rangeFalloff={0.1}
                bias={0.5}
                luminanceInfluence={0.9}
                color="black"
              />
            )}

            {/* Enhanced tone mapping for better HDR simulation */}
            <DynamicToneMapping
              adaptive={true}
              resolution={qualityLevel === 'ultra' ? 512 : 256}
              middleGrey={0.7}
              maxLuminance={20.0}
              averageLuminance={1.0}
              adaptationRate={1.5}
            />

            {/* Improved vignette effect for more cinematic feel */}
            <DynamicVignette
              offset={0.15}
              darkness={0.75}
              opacity={qualityLevel === 'low' ? 0.2 : 0.3}
            />

            {/* Advanced anti-aliasing */}
            <DynamicSMAA
              preset={qualityLevel === 'ultra' ? 4 : qualityLevel === 'high' ? 3 : 2}
              edgeDetectionMode={1} // More accurate edge detection
            />
          </DynamicEffectComposer>
        )}
      </Suspense>
    </ErrorBoundary>
  );
}

export default PostProcessingEffects;
