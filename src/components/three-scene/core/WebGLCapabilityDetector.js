/**
 * WebGLCapabilityDetector - Detects WebGL capabilities and hardware limitations
 *
 * This utility analyzes the GPU capabilities and recommends appropriate
 * rendering settings for optimal performance.
 */

class WebGLCapabilityDetector {
  constructor() {
    this.capabilities = {
      webglSupported: false,
      webgl2Supported: false,
      maxTextureSize: 0,
      maxTextures: 0,
      devicePixelRatio: 1,
      isMobile: false,
      isLowEndDevice: false,
      vendor: '',
      renderer: '',
      hasHardwareAcceleration: true
    };

    this.detect();
  }

  /**
   * Analyzes current device capabilities
   */
  detect() {
    try {
      // Detect basic WebGL support
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');

      if (!gl) {
        this.capabilities.webglSupported = false;
        return this.capabilities;
      }

      this.capabilities.webglSupported = true;

      // Detect WebGL2 support
      const gl2 = canvas.getContext('webgl2');
      this.capabilities.webgl2Supported = !!gl2;

      // Get hardware information
      const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
      if (debugInfo) {
        this.capabilities.vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
        this.capabilities.renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
      }

      // Get texture capabilities
      this.capabilities.maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
      this.capabilities.maxTextures = gl.getParameter(gl.MAX_COMBINED_TEXTURE_IMAGE_UNITS);

      // Get device info
      this.capabilities.devicePixelRatio = window.devicePixelRatio || 1;
      this.capabilities.isMobile = this.detectMobileDevice();

      // Detect low-end devices based on various indicators
      this.capabilities.isLowEndDevice = this.detectLowEndDevice(gl);

      // Detect hardware acceleration
      this.capabilities.hasHardwareAcceleration = this.detectHardwareAcceleration();

      // Clean up
      gl.getExtension('WEBGL_lose_context')?.loseContext();

      return this.capabilities;
    } catch (error) {
      console.error('Error detecting WebGL capabilities:', error);
      this.capabilities.webglSupported = false;
      return this.capabilities;
    }
  }

  /**
   * Detects if device is mobile based on user agent
   */
  detectMobileDevice() {
    const userAgent = navigator.userAgent || navigator.vendor || window.opera;
    const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
    return mobileRegex.test(userAgent);
  }

  /**
   * Detects if the device is likely a low-end device
   */
  detectLowEndDevice(gl) {
    const memory = navigator.deviceMemory || 4; // Default to middle value if not available
    const concurrency = navigator.hardwareConcurrency || 4;

    let isLowEnd = false;

    // Memory-based detection (low memory is a strong indicator)
    if (memory <= 2) {
      isLowEnd = true;
    }

    // CPU core-based detection (fewer cores often means low-end)
    if (concurrency <= 2) {
      isLowEnd = true;
    }

    // Texture size-based detection
    if (this.capabilities.maxTextureSize < 4096) {
      isLowEnd = true;
    }

    // Mobile devices are more likely to struggle with complex graphics
    if (this.capabilities.isMobile) {
      isLowEnd = true;
    }

    // Known low-performance GPUs based on name
    if (this.capabilities.renderer) {
      const lowEndGPUs = [
        'intel hd graphics',
        'gma',
        'mali-4',
        'mali-t6',
        'adreno 3',
        'adreno 4',
        'powervr',
        'apple a7',
        'apple a8'
      ];

      const rendererLower = this.capabilities.renderer.toLowerCase();
      if (lowEndGPUs.some(gpu => rendererLower.includes(gpu))) {
        isLowEnd = true;
      }
    }

    return isLowEnd;
  }

  /**
   * Detects if hardware acceleration is enabled
   */
  detectHardwareAcceleration() {
    // Create a canvas and test its performance
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return true; // Assume hardware acceleration if we can't test

    // Canvas operations perform better with hardware acceleration
    const startTime = performance.now();

    // Perform a representative drawing operation
    for (let i = 0; i < 1000; i++) {
      ctx.fillStyle = `rgb(${i % 255}, ${(i * 2) % 255}, ${(i * 3) % 255})`;
      ctx.fillRect(i % 100, i % 100, 10, 10);
    }

    const endTime = performance.now();
    const duration = endTime - startTime;

    // If the operation took too long, hardware acceleration might be disabled
    return duration < 100; // Threshold in milliseconds
  }

  /**
   * Recommends optimal quality settings based on capabilities
   */
  getRecommendedQuality() {
    if (!this.capabilities.webglSupported) {
      return {
        level: 'fallback',
        pixelRatio: 1,
        antialias: false,
        shadows: false,
        textureQuality: 'low',
        particleCount: 0,
        effectsEnabled: false,
        maxTextureSize: 256
      };
    }

    if (this.capabilities.isLowEndDevice) {
      return {
        level: 'low',
        pixelRatio: Math.min(1, this.capabilities.devicePixelRatio),
        antialias: false,
        shadows: false,
        textureQuality: 'low',
        particleCount: 200,
        effectsEnabled: false,
        maxTextureSize: 1024
      };
    }

    if (this.capabilities.isMobile && !this.capabilities.isLowEndDevice) {
      return {
        level: 'medium',
        pixelRatio: Math.min(1.5, this.capabilities.devicePixelRatio),
        antialias: true,
        shadows: false,
        textureQuality: 'medium',
        particleCount: 500,
        effectsEnabled: true,
        maxTextureSize: 2048
      };
    }

    // High-end device
    return {
      level: 'high',
      pixelRatio: this.capabilities.devicePixelRatio,
      antialias: true,
      shadows: true,
      textureQuality: 'high',
      particleCount: 1000,
      effectsEnabled: true,
      maxTextureSize: 4096
    };
  }
}

export default WebGLCapabilityDetector;
