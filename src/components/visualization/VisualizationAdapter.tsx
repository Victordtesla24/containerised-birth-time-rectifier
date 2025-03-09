import React, { useEffect, useState } from 'react';
import { CelestialVisualizationProps } from './common/types';
import { CanvasVisualization } from './canvas';
import { ThreeJsVisualization } from './three';

/**
 * Enhanced browser capabilities detection with performance profiling
 * @returns Object with detailed browser capability flags and performance metrics
 */
const detectCapabilities = () => {
  // Enhanced WebGL detection with fail-safe fallbacks and version determination
  const webGLInfo = (() => {
    try {
      // Try to get WebGL2 context first with proper type casting
      const canvas = document.createElement('canvas');
      const gl2 = canvas.getContext('webgl2') as WebGL2RenderingContext | null;

      if (gl2) {
        // Check for key WebGL2 features like multiple render targets and transform feedback
        const hasInstancedArrays = !!gl2.getExtension('ANGLE_instanced_arrays');
        const hasFloatTextures = !!gl2.getExtension('OES_texture_float');
        const hasHalfFloatTextures = !!gl2.getExtension('OES_texture_half_float');
        const hasDepthTexture = !!gl2.getExtension('WEBGL_depth_texture');

        // Get renderer info for better GPU detection
        const rendererInfo = gl2.getExtension('WEBGL_debug_renderer_info');
        const renderer = rendererInfo && rendererInfo.UNMASKED_RENDERER_WEBGL ?
                        gl2.getParameter(rendererInfo.UNMASKED_RENDERER_WEBGL) :
                        'Unknown GPU';

        // Calculate max texture size for better quality decisions
        const maxTextureSize = gl2.getParameter(gl2.MAX_TEXTURE_SIZE);

        return {
          hasWebGL: true,
          hasWebGL2: true,
          renderer,
          maxTextureSize,
          hasInstancedArrays,
          hasFloatTextures,
          hasHalfFloatTextures,
          hasDepthTexture,
          version: 2
        };
      }

      // Fall back to WebGL1 with proper type casting
      const gl1 = (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')) as WebGLRenderingContext | null;

      if (gl1) {
        // Check for key WebGL1 extensions that would help with rendering quality
        const hasInstancedArrays = !!gl1.getExtension('ANGLE_instanced_arrays');
        const hasFloatTextures = !!gl1.getExtension('OES_texture_float');
        const hasHalfFloatTextures = !!gl1.getExtension('OES_texture_half_float');
        const hasDepthTexture = !!gl1.getExtension('WEBGL_depth_texture');

        // Get renderer info
        const rendererInfo = gl1.getExtension('WEBGL_debug_renderer_info');
        const renderer = rendererInfo && rendererInfo.UNMASKED_RENDERER_WEBGL ?
                        gl1.getParameter(rendererInfo.UNMASKED_RENDERER_WEBGL) :
                        'Unknown GPU';

        // Calculate max texture size
        const maxTextureSize = gl1.getParameter(gl1.MAX_TEXTURE_SIZE);

        return {
          hasWebGL: true,
          hasWebGL2: false,
          renderer,
          maxTextureSize,
          hasInstancedArrays,
          hasFloatTextures,
          hasHalfFloatTextures,
          hasDepthTexture,
          version: 1
        };
      }

      return {
        hasWebGL: false,
        hasWebGL2: false,
        renderer: 'No WebGL Support',
        maxTextureSize: 0,
        hasInstancedArrays: false,
        hasFloatTextures: false,
        hasHalfFloatTextures: false,
        hasDepthTexture: false,
        version: 0
      };
    } catch (e) {
      console.error('WebGL detection error:', e);
      return {
        hasWebGL: false,
        hasWebGL2: false,
        renderer: 'WebGL Detection Error',
        maxTextureSize: 0,
        hasInstancedArrays: false,
        hasFloatTextures: false,
        hasHalfFloatTextures: false,
        hasDepthTexture: false,
        version: 0
      };
    }
  })();

  // Enhanced device detection with more sophisticated metrics

  // Check for mobile device with better detection
  const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera || '';
  const isMobile = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini|mobile|tablet/i.test(userAgent.toLowerCase());

  // Device form factor determination
  const isTablet = isMobile && (
    /ipad/i.test(userAgent) ||
    (/android/i.test(userAgent) && !/mobile/i.test(userAgent)) ||
    (window.innerWidth >= 600 && window.innerWidth <= 1024)
  );

  // Screen properties for better resolution-based decisions
  const screenInfo = {
    width: window.screen.width,
    height: window.screen.height,
    devicePixelRatio: window.devicePixelRatio || 1,
    effectiveResolution: Math.max(
      window.screen.width * (window.devicePixelRatio || 1),
      window.screen.height * (window.devicePixelRatio || 1)
    )
  };

  // Check for device memory (available in Chrome, or estimate based on other factors)
  const deviceMemory = (navigator as any).deviceMemory ||
                      (isMobile ? (isTablet ? 4 : 2) : 8);

  // Check for CPU cores with better fallbacks
  const cpuCores = navigator.hardwareConcurrency ||
                  (isMobile ? (isTablet ? 4 : 2) : 8);

  // Performance estimation based on combined factors
  const gpuTier = (() => {
    const renderer = webGLInfo.renderer.toLowerCase();

    // High-end GPU detection
    if (
      renderer.includes('nvidia') ||
      renderer.includes('radeon') ||
      renderer.includes('geforce') ||
      renderer.includes('intel iris') ||
      (webGLInfo.maxTextureSize >= 16384)
    ) {
      return 'high';
    }

    // Mid-range GPU detection
    if (
      renderer.includes('intel') ||
      renderer.includes('adreno') ||
      (webGLInfo.maxTextureSize >= 8192)
    ) {
      return 'medium';
    }

    return 'low';
  })();

  // Combined performance score (0-100)
  const performanceScore = () => {
    let score = 0;

    // WebGL version (0-30 points)
    score += webGLInfo.version === 2 ? 30 : (webGLInfo.version === 1 ? 15 : 0);

    // GPU tier (0-30 points)
    score += gpuTier === 'high' ? 30 : (gpuTier === 'medium' ? 20 : 10);

    // CPU cores (0-20 points)
    score += Math.min(cpuCores, 8) * 2.5;

    // Memory (0-20 points)
    score += Math.min(deviceMemory, 8) * 2.5;

    return score;
  };

  // Calculate recommended quality level based on performance score
  const qualityLevel = (() => {
    const score = performanceScore();

    if (score >= 80) return 'ultra';
    if (score >= 60) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
  })();

  return {
    webGL: webGLInfo,
    device: {
      isMobile,
      isTablet,
      deviceMemory,
      cpuCores,
      performanceScore: performanceScore(),
      screen: screenInfo
    },
    // Quality determination
    gpuTier,
    qualityLevel,
    // Legacy properties for backward compatibility
    hasWebGL: webGLInfo.hasWebGL,
    hasWebGL2: webGLInfo.hasWebGL2,
    isHighPower: qualityLevel === 'high' || qualityLevel === 'ultra',
    isLowPower: qualityLevel === 'low'
  };
};

/**
 * VisualizationAdapter component
 * Chooses the appropriate visualization implementation based on device capabilities
 *
 * @param {CelestialVisualizationProps} props - Visualization properties
 */
const VisualizationAdapter: React.FC<CelestialVisualizationProps> = (props) => {
  const [capabilities, setCapabilities] = useState<any>(null);
  const [preferCanvas, setPreferCanvas] = useState(false);

  // Detect capabilities on mount
  useEffect(() => {
    const detected = detectCapabilities();
    setCapabilities(detected);

    // Choose canvas for very low power devices
    setPreferCanvas(detected.isLowPower || !detected.hasWebGL);

    // Log detected capabilities
    console.log('Device capabilities:', detected);
  }, []);

  // Don't render until capabilities are detected
  if (!capabilities) {
    return <div className="loading-visualization">Initializing visualization...</div>;
  }

  // Use Canvas implementation for low-power devices
  if (preferCanvas) {
    return <CanvasVisualization {...props} />;
  }

  // Use Three.js for all other devices
  return <ThreeJsVisualization {...props} />;
};

export default VisualizationAdapter;
