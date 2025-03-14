import React, { createContext, useContext, useState, useEffect } from 'react';

// Create a context for quality settings
const QualityContext = createContext();

/**
 * Quality levels for rendering optimization
 */
export const QUALITY_LEVELS = {
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
};

/**
 * QualityProvider component that manages rendering quality settings
 * based on device capabilities.
 */
export function QualityProvider({ children }) {
  // Default to medium quality until we detect capabilities
  const [qualityLevel, setQualityLevel] = useState(QUALITY_LEVELS.MEDIUM);
  const [pixelRatio, setPixelRatio] = useState(1);
  const [antialiasing, setAntialiasing] = useState(true);
  const [deviceCapabilities, setDeviceCapabilities] = useState({
    detected: false,
    gpu: 'unknown',
    browser: 'unknown',
    mobile: false,
    supportsWebGL2: true,
  });

  useEffect(() => {
    // Detect device capabilities
    const detectCapabilities = () => {
      // Only run on client
      if (typeof window === 'undefined') return;

      try {
        // Get device pixel ratio
        const dpr = window.devicePixelRatio || 1;
        setPixelRatio(Math.min(dpr, 2)); // Cap pixel ratio at 2 for performance

        // Check if mobile
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
          navigator.userAgent
        );

        // Create a test canvas to check WebGL2 support
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl2');
        const supportsWebGL2 = !!gl;

        // Get basic GPU info if possible
        let gpuInfo = 'unknown';
        if (gl) {
          const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
          if (debugInfo) {
            gpuInfo = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
          }
        }

        // Set detected capabilities
        setDeviceCapabilities({
          detected: true,
          gpu: gpuInfo,
          browser: navigator.userAgent,
          mobile: isMobile,
          supportsWebGL2,
        });

        // Determine quality level based on capabilities
        if (!supportsWebGL2) {
          setQualityLevel(QUALITY_LEVELS.LOW);
          setAntialiasing(false);
        } else if (isMobile || dpr < 1.5) {
          // Mobile devices or lower-res displays get medium quality
          setQualityLevel(QUALITY_LEVELS.MEDIUM);
          setAntialiasing(dpr > 1); // Only use antialiasing on higher DPI mobile devices
        } else {
          // Default to high quality for desktop browsers with good WebGL support
          setQualityLevel(QUALITY_LEVELS.HIGH);
          setAntialiasing(true);
        }

        // Performance testing - adjust quality if rendering is slow
        let lastTime = performance.now();
        let frameCount = 0;
        let lowFPSCount = 0;

        const checkPerformance = () => {
          const now = performance.now();
          const elapsed = now - lastTime;
          frameCount++;

          // Check every second
          if (elapsed >= 1000) {
            const fps = (frameCount * 1000) / elapsed;

            // If FPS is consistently low, reduce quality
            if (fps < 30) {
              lowFPSCount++;
              if (lowFPSCount >= 3 && qualityLevel !== QUALITY_LEVELS.LOW) {
                console.log('Performance issue detected, reducing quality level');
                setQualityLevel(prev =>
                  prev === QUALITY_LEVELS.HIGH ? QUALITY_LEVELS.MEDIUM : QUALITY_LEVELS.LOW
                );
                setAntialiasing(false);
                lowFPSCount = 0; // Reset counter after adjustment
              }
            } else {
              lowFPSCount = 0; // Reset counter if performance is good
            }

            // Reset counters
            frameCount = 0;
            lastTime = now;
          }

          // Continue checking for a period after initialization
          if (lowFPSCount < 5) {
            requestAnimationFrame(checkPerformance);
          }
        };

        // Start performance monitoring
        requestAnimationFrame(checkPerformance);
      } catch (error) {
        console.error('Error detecting device capabilities:', error);
        // Default to low quality on error
        setQualityLevel(QUALITY_LEVELS.LOW);
        setAntialiasing(false);
      }
    };

    detectCapabilities();
  }, []);

  // Create the context value
  const contextValue = {
    qualityLevel,
    setQualityLevel,
    pixelRatio,
    antialiasing,
    deviceCapabilities,
  };

  return (
    <QualityContext.Provider value={contextValue}>
      {children}
    </QualityContext.Provider>
  );
}

// Custom hook to use the quality context
export function useQuality() {
  const context = useContext(QualityContext);
  if (!context) {
    throw new Error('useQuality must be used within a QualityProvider');
  }
  return context;
}
