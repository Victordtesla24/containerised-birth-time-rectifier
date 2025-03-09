import React, { useEffect, useRef } from 'react';
import { useThree } from '@react-three/fiber';
import { useQuality } from './QualityContext';
import * as THREE from 'three';

/**
 * Component that detects WebGL capabilities and automatically
 * adjusts settings based on device capabilities
 *
 * This component doesn't render anything visually, but provides
 * critical functionality for optimal rendering performance
 */
const WebGLCapabilityDetector = ({ onCapabilitiesDetected }) => {
  const { gl, capabilities } = useThree();
  const { setQualityLevel } = useQuality();
  const detectionCompletedRef = useRef(false);

  useEffect(() => {
    if (detectionCompletedRef.current) return;

    // Get detailed renderer information
    const renderer = gl;
    const renderInfo = renderer.info;

    // Check for key rendering capabilities
    const maxTextureSize = gl.capabilities.maxTextureSize;
    const maxPrecision = gl.capabilities.precision;
    const maxAnisotropy = gl.capabilities.getMaxAnisotropy();
    const isWebGL2 = gl.capabilities.isWebGL2;

    // Analyze renderer performance capabilities
    const renderSize = renderer.getDrawingBufferSize(new THREE.Vector2());
    const glContext = gl.getContext();

    // Deep detection of extensions and limits
    const extensions = {
      floatTextures: !!glContext.getExtension('OES_texture_float'),
      halfFloatTextures: !!glContext.getExtension('OES_texture_half_float'),
      depthTexture: !!glContext.getExtension('WEBGL_depth_texture'),
      loseContext: !!glContext.getExtension('WEBGL_lose_context'),
      debugRenderer: !!glContext.getExtension('WEBGL_debug_renderer_info'),
      anisotropicFiltering: !!glContext.getExtension('EXT_texture_filter_anisotropic')
    };

    // Get GPU info if available
    let gpuVendor = 'unknown';
    let gpuRenderer = 'unknown';

    if (extensions.debugRenderer) {
      try {
        gpuVendor = glContext.getParameter(
          glContext.getExtension('WEBGL_debug_renderer_info').UNMASKED_VENDOR_WEBGL
        );
        gpuRenderer = glContext.getParameter(
          glContext.getExtension('WEBGL_debug_renderer_info').UNMASKED_RENDERER_WEBGL
        );
      } catch (e) {
        console.warn('Could not detect GPU info:', e);
      }
    }

    // Log information for debugging
    console.log('WebGL Capabilities Detected:', {
      maxTextureSize,
      maxPrecision,
      maxAnisotropy,
      isWebGL2,
      renderSize,
      extensions,
      gpuInfo: { vendor: gpuVendor, renderer: gpuRenderer }
    });

    // Analyze if this is likely a low-end device
    const isLikelyLowEnd = detectLowEndDevice(gpuRenderer, gpuVendor, maxAnisotropy, isWebGL2);

    // Perform a simple render test to check performance
    const testStartTime = performance.now();

    // Create a temporary scene for testing
    const testScene = new THREE.Scene();
    const testCamera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    testCamera.position.z = 5;

    // Create test geometry with appropriate complexity based on initial assessment
    const complexity = isLikelyLowEnd ? 20 : 50;
    const testGeometry = new THREE.SphereGeometry(1, complexity, complexity);
    const testMaterial = new THREE.MeshStandardMaterial();

    // Add test objects
    for (let i = 0; i < (isLikelyLowEnd ? 5 : 20); i++) {
      const testMesh = new THREE.Mesh(testGeometry, testMaterial);
      testMesh.position.set(
        Math.random() * 10 - 5,
        Math.random() * 10 - 5,
        Math.random() * 10 - 5
      );
      testScene.add(testMesh);
    }

    // Add a test light
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(1, 1, 1);
    testScene.add(light);

    // Run test render (temporarily use the real renderer)
    renderer.render(testScene, testCamera);

    // Measure render time
    const renderTime = performance.now() - testStartTime;

    // Clean up test objects
    testScene.clear();

    // Calculate quality level based on all factors
    const detectedCapabilities = {
      isWebGL2,
      maxTextureSize,
      maxAnisotropy,
      renderTimeMs: renderTime,
      gpuInfo: { vendor: gpuVendor, renderer: gpuRenderer },
      extensions,
      isLowEnd: isLikelyLowEnd,
      recommendedQuality: calculateRecommendedQuality(
        isLikelyLowEnd,
        renderTime,
        isWebGL2,
        maxAnisotropy
      )
    };

    // Set quality level based on detection
    setQualityLevel(detectedCapabilities.recommendedQuality);

    // Call optional callback with detection results
    if (onCapabilitiesDetected) {
      onCapabilitiesDetected(detectedCapabilities);
    }

    // Mark detection as completed
    detectionCompletedRef.current = true;

    // Clean up function not needed in this case
  }, [gl, capabilities, setQualityLevel, onCapabilitiesDetected]);

  // Component doesn't render anything
  return null;
};

/**
 * Helper to detect if device is likely low-end
 */
function detectLowEndDevice(gpuRenderer, gpuVendor, maxAnisotropy, isWebGL2) {
  if (!gpuRenderer && !gpuVendor) return true; // Can't detect, assume low-end to be safe

  const renderer = (gpuRenderer || '').toLowerCase();
  const vendor = (gpuVendor || '').toLowerCase();

  // Check for known integrated/mobile GPUs
  const lowEndSignifiers = [
    'intel', 'hd graphics', 'iris', // Intel integrated
    'mali', 'adreno', 'powervr', // Mobile GPUs
    'llvmpipe', 'swiftshader', // Software rendering
    'apple gpu', // Some Apple GPUs can be limited
    'radeon hd' // Older AMD GPUs
  ];

  // Additional indicators of low-end device
  const hasLowAnisotropy = maxAnisotropy <= 4;
  const isNotWebGL2 = !isWebGL2;

  // Check if GPU name contains known low-end indicators
  const isKnownLowEnd = lowEndSignifiers.some(term =>
    renderer.includes(term) || vendor.includes(term)
  );

  return isKnownLowEnd || (hasLowAnisotropy && isNotWebGL2);
}

/**
 * Calculate recommended quality level
 */
function calculateRecommendedQuality(isLowEnd, renderTime, isWebGL2, maxAnisotropy) {
  // Start with medium quality as default
  let recommendedQuality = 'medium';

  // For definitely low-end devices, use low quality
  if (isLowEnd) {
    recommendedQuality = 'low';
  }

  // Check render performance
  if (renderTime > 50) { // Slow render time
    recommendedQuality = 'low';
  } else if (renderTime < 10 && isWebGL2 && maxAnisotropy >= 8) {
    // Fast render, good capabilities
    recommendedQuality = 'high';
  }

  // Limit by WebGL version
  if (!isWebGL2 && recommendedQuality === 'high') {
    recommendedQuality = 'medium'; // Downgrade non-WebGL2 to medium at most
  }

  // On mobile, cap at medium quality
  if (typeof navigator !== 'undefined' && /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
    recommendedQuality = recommendedQuality === 'high' ? 'medium' : recommendedQuality;
  }

  return recommendedQuality;
}

export default WebGLCapabilityDetector;
