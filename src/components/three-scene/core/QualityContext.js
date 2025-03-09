/**
 * QualityContext
 * Context provider for WebGL quality settings, handles browser capabilities detection
 */
import { createContext, useContext, useEffect, useState } from 'react';

// Create a context with default values
const QualityContext = createContext({
  // Set safe default values that work on server
  webglSupported: false,
  maxTextureSize: 2048,
  maxPrecision: 'highp',

  // General settings
  level: 'medium', // 'low', 'medium', 'high', 'ultra', 'custom'
  pixelRatio: 1,
  antialias: true,

  // Performance settings
  adaptiveQuality: true,
  maxFPS: 60,

  // Device info
  isLowEndDevice: false,
  isMobile: false,

  // Methods
  updateQuality: () => {},
  detectCapabilities: () => {},
});

// Custom hook to use the quality context
export const useQuality = () => {
  const context = useContext(QualityContext);
  if (context === undefined) {
    throw new Error('useQuality must be used within a QualityProvider');
  }
  return context;
};

// Provider component
export const QualityProvider = ({ children }) => {
  // State with default values that are safe for SSR
  const [state, setState] = useState({
    webglSupported: false,
    maxTextureSize: 2048,
    maxPrecision: 'highp',
    level: 'medium',
    pixelRatio: 1,
    antialias: true,
    adaptiveQuality: true,
    maxFPS: 60,
    isLowEndDevice: false,
    isMobile: false,
  });

  // Detect capabilities on the client side only
  useEffect(() => {
    detectCapabilities();
  }, []);

  // Method to detect WebGL capabilities
  const detectCapabilities = () => {
    try {
      // Safety check for SSR - these browser APIs only exist on the client
      if (typeof window === 'undefined' || typeof document === 'undefined') {
        return;
      }

      // Check if WebGL is supported
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');

      if (!gl) {
        setState(prev => ({
          ...prev,
          webglSupported: false,
          level: 'low'
        }));
        return;
      }

      // Now we know WebGL is supported
      setState(prev => ({ ...prev, webglSupported: true }));

      // Get maximum texture size
      const maxTexSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);

      // Check precision support
      let precision = 'highp';
      const highPrecision = gl.getShaderPrecisionFormat(gl.VERTEX_SHADER, gl.HIGH_FLOAT);

      if (!highPrecision || highPrecision.precision === 0) {
        precision = 'mediump';
        const mediumPrecision = gl.getShaderPrecisionFormat(gl.VERTEX_SHADER, gl.MEDIUM_FLOAT);

        if (!mediumPrecision || mediumPrecision.precision === 0) {
          precision = 'lowp';
        }
      }

      // Check if it's a mobile device
      const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
        navigator.userAgent
      );

      // Get device pixel ratio
      const dpr = window.devicePixelRatio || 1;

      // Detect if it's a low-end device
      const hasLimitedResources =
        (isMobileDevice && maxTexSize < 4096) ||
        precision !== 'highp' ||
        (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4);

      // Set initial quality level based on capabilities
      let initialQuality = 'high';

      if (hasLimitedResources) {
        initialQuality = 'low';
      } else if (isMobileDevice || dpr > 2) {
        initialQuality = 'medium';
      }

      // Set appropriate antialias setting
      const useAntialias = initialQuality !== 'low';

      // Set max FPS based on device capabilities
      const targetFrameRate = isMobileDevice && hasLimitedResources ? 30 : 60;

      // Update state with detected values
      setState({
        webglSupported: true,
        maxTextureSize: maxTexSize,
        maxPrecision: precision,
        level: initialQuality,
        pixelRatio: dpr,
        antialias: useAntialias,
        adaptiveQuality: true,
        maxFPS: targetFrameRate,
        isLowEndDevice: hasLimitedResources,
        isMobile: isMobileDevice,
      });

    } catch (error) {
      console.error('Error detecting WebGL capabilities:', error);
      setState(prev => ({
        ...prev,
        webglSupported: false,
        level: 'low'
      }));
    }
  };

  // Method to update quality settings
  const updateQuality = (newSettings = {}) => {
    setState(prev => ({
      ...prev,
      ...newSettings,
    }));
  };

  // Provide context value
  const value = {
    ...state,
    updateQuality,
    detectCapabilities,
  };

  return (
    <QualityContext.Provider value={value}>
      {children}
    </QualityContext.Provider>
  );
};

export default QualityContext;
