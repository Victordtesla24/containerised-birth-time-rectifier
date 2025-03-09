import React, { createContext, useContext, useState, useEffect } from 'react';

// Create context for quality management
const QualityContext = createContext(null);

/**
 * Determines device capabilities and sets appropriate quality level
 * @returns {Object} Object containing device capability information
 */
function detectDeviceCapabilities() {
  // Default to medium quality for safety
  let initialQuality = 'medium';
  let antialiasing = true;
  let shadows = true;
  let maxTextureSize = 2048;
  let pixelRatio = typeof window !== 'undefined' ? window.devicePixelRatio : 1;

  // Cap pixel ratio to avoid performance issues on high-DPI displays
  pixelRatio = Math.min(pixelRatio, 2);

  try {
    // Check if WebGL is available
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');

    if (!gl) {
      // WebGL not available, fallback to low quality
      return {
        qualityLevel: 'low',
        antialiasing: false,
        pixelRatio: 1,
        shadows: false,
        maxTextureSize: 1024,
        glSupported: false
      };
    }

    // Check GPU vendor and renderer
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    const vendor = debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : '';
    const renderer = debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : '';

    // Log to help with debugging
    console.log('GPU detected:', renderer, vendor);

    // Check maximum texture size
    maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);

    // Get max viewport dimensions
    const maxViewportDims = gl.getParameter(gl.MAX_VIEWPORT_DIMS);

    // Check if the GPU is likely a mobile/low-end GPU
    const isLowEndGPU = isLowEndRenderer(renderer, vendor);

    // Check if memory is constrained
    const isMemoryConstrained = navigator.deviceMemory
      ? navigator.deviceMemory < 4
      : isLowEndGPU;

    // Check processing power (very approximate method)
    const isLowPower = isLowPowerDevice();

    // Determine quality based on GPU and memory constraints
    if (isMemoryConstrained || isLowEndGPU || isLowPower) {
      initialQuality = 'low';
      antialiasing = false;
      shadows = false;
      pixelRatio = Math.min(pixelRatio, 1);
    } else if (
      maxTextureSize >= 8192 &&
      !isLowEndGPU &&
      !isMemoryConstrained &&
      !isLowPower
    ) {
      initialQuality = 'high';
    }

    return {
      qualityLevel: initialQuality,
      antialiasing,
      pixelRatio,
      shadows,
      maxTextureSize,
      glSupported: true,
      gpuInfo: { vendor, renderer }
    };
  } catch (error) {
    console.warn('Error detecting device capabilities:', error);
    // Fall back to low quality settings on error
    return {
      qualityLevel: 'low',
      antialiasing: false,
      pixelRatio: 1,
      shadows: false,
      maxTextureSize: 1024,
      glSupported: false
    };
  }
}

/**
 * Check if renderer string suggests a low-end GPU
 */
function isLowEndRenderer(renderer = '', vendor = '') {
  renderer = renderer.toLowerCase();
  vendor = vendor.toLowerCase();

  // Check for integrated/mobile GPUs and older models
  const lowEndKeywords = [
    'intel', 'hd graphics', 'uhd graphics', 'iris',
    'mali', 'adreno', 'apple gpu', 'apple a', 'powervr',
    'radeon hd', 'llvmpipe', 'swiftshader', 'angle'
  ];

  return lowEndKeywords.some(keyword =>
    renderer.includes(keyword) || vendor.includes(keyword)
  );
}

/**
 * Attempt to detect if this is likely a low-power device
 * Note: This is an approximation as there's no definitive API for this
 */
function isLowPowerDevice() {
  // Check for mobile devices
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i
    .test(navigator.userAgent);

  // Check for device memory (only in Chrome)
  const hasLowMemory = navigator.deviceMemory
    ? navigator.deviceMemory < 4
    : false;

  // Check for battery status
  const hasBattery = 'getBattery' in navigator;

  // Check hardware concurrency (CPU cores/threads)
  const hasLowCores = navigator.hardwareConcurrency
    ? navigator.hardwareConcurrency <= 4
    : false;

  // If multiple indicators point to a low-power device
  return (isMobile && (hasLowMemory || hasLowCores)) ||
         (hasBattery && hasLowCores && hasLowMemory);
}

/**
 * Provider component for quality settings
 * Manages quality levels and device capabilities across the app
 */
const QualityProvider = ({ children }) => {
  // State for quality settings
  const [settings, setSettings] = useState({
    qualityLevel: 'medium', // Default before detection: low, medium, high
    antialiasing: true,
    pixelRatio: 1,
    shadows: true,
    maxTextureSize: 2048,
    glSupported: true,
    autoAdjust: true, // Auto-adjust quality based on performance
    fpsTarget: 30, // Target FPS for auto-adjustment
    gpuInfo: { vendor: '', renderer: '' }
  });

  // Run device detection once on client side
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const capabilities = detectDeviceCapabilities();
      setSettings(prev => ({
        ...prev,
        ...capabilities
      }));

      // Log detected capabilities for debugging
      console.log('Device capabilities detected:', capabilities);
    }
  }, []);

  // Function to update quality level
  const setQualityLevel = (level) => {
    if (!['low', 'medium', 'high'].includes(level)) {
      console.warn(`Invalid quality level: ${level}. Using 'medium' instead.`);
      level = 'medium';
    }

    setSettings(prev => {
      // Update related settings based on quality level
      const newSettings = { ...prev, qualityLevel: level };

      switch (level) {
        case 'low':
          newSettings.shadows = false;
          newSettings.antialiasing = false;
          newSettings.pixelRatio = Math.min(window.devicePixelRatio, 1);
          break;
        case 'medium':
          newSettings.shadows = true;
          newSettings.antialiasing = true;
          newSettings.pixelRatio = Math.min(window.devicePixelRatio, 1.5);
          break;
        case 'high':
          newSettings.shadows = true;
          newSettings.antialiasing = true;
          newSettings.pixelRatio = Math.min(window.devicePixelRatio, 2);
          break;
      }

      return newSettings;
    });
  };

  // Toggle automatic quality adjustment
  const toggleAutoAdjust = () => {
    setSettings(prev => ({
      ...prev,
      autoAdjust: !prev.autoAdjust
    }));
  };

  // Function called by PerformanceMonitor to adjust quality based on FPS
  const adjustQualityForPerformance = (currentFPS) => {
    if (!settings.autoAdjust) return;

    setSettings(prev => {
      // Don't adjust if we just changed settings recently (avoid oscillation)
      if (prev.lastAdjustment && Date.now() - prev.lastAdjustment < 5000) {
        return prev;
      }

      const newSettings = { ...prev, lastAdjustment: Date.now() };

      // If performance is poor, reduce quality
      if (currentFPS < prev.fpsTarget * 0.7) {
        if (prev.qualityLevel === 'high') {
          newSettings.qualityLevel = 'medium';
          newSettings.shadows = true;
          newSettings.antialiasing = true;
          newSettings.pixelRatio = Math.min(window.devicePixelRatio, 1.5);
        } else if (prev.qualityLevel === 'medium') {
          newSettings.qualityLevel = 'low';
          newSettings.shadows = false;
          newSettings.antialiasing = false;
          newSettings.pixelRatio = Math.min(window.devicePixelRatio, 1);
        }
      }
      // If performance is good, consider increasing quality
      else if (currentFPS > prev.fpsTarget * 1.5) {
        if (prev.qualityLevel === 'low') {
          newSettings.qualityLevel = 'medium';
          newSettings.shadows = true;
          newSettings.antialiasing = true;
          newSettings.pixelRatio = Math.min(window.devicePixelRatio, 1.5);
        } else if (prev.qualityLevel === 'medium') {
          newSettings.qualityLevel = 'high';
          newSettings.shadows = true;
          newSettings.antialiasing = true;
          newSettings.pixelRatio = Math.min(window.devicePixelRatio, 2);
        }
      }

      return newSettings;
    });
  };

  // The context value containing current settings and update functions
  const contextValue = {
    ...settings,
    setQualityLevel,
    toggleAutoAdjust,
    adjustQualityForPerformance
  };

  return (
    <QualityContext.Provider value={contextValue}>
      {children}
    </QualityContext.Provider>
  );
};

// Custom hook to access quality settings
export const useQuality = () => {
  const context = useContext(QualityContext);
  if (!context) {
    throw new Error('useQuality must be used within a QualityProvider');
  }
  return context;
};

export default QualityProvider;
