/**
 * WebGL Compatibility Testing Utility
 *
 * This utility checks if WebGL is available and properly functioning on the current browser.
 * It provides fallback options for environments with limited or no WebGL support.
 */

/**
 * Test if WebGL is available in the current browser
 * @returns {boolean} True if WebGL is available, false otherwise
 */
export function isWebGLAvailable() {
  try {
    // Try to create a WebGL context
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');

    // If context creation fails, WebGL is not available
    if (!ctx) {
      console.warn('WebGL not available in this browser');
      return false;
    }

    // Test if we can create a simple WebGL program
    try {
      const vertexShader = ctx.createShader(ctx.VERTEX_SHADER);
      const fragmentShader = ctx.createShader(ctx.FRAGMENT_SHADER);

      if (!vertexShader || !fragmentShader) {
        console.warn('Failed to create WebGL shaders');
        return false;
      }

      // Clean up test resources
      ctx.deleteShader(vertexShader);
      ctx.deleteShader(fragmentShader);

      return true;
    } catch (err) {
      console.warn('WebGL shader creation failed:', err);
      return false;
    }
  } catch (err) {
    console.warn('WebGL detection error:', err);
    return false;
  }
}

/**
 * Test if WebGL2 is available in the current browser
 * @returns {boolean} True if WebGL2 is available, false otherwise
 */
export function isWebGL2Available() {
  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('webgl2');

    return !!ctx;
  } catch (err) {
    console.warn('WebGL2 detection error:', err);
    return false;
  }
}

/**
 * Get the recommended quality level based on the device capabilities
 * @returns {'high'|'medium'|'low'} The recommended quality level
 */
export function getRecommendedQualityLevel() {
  // Check if the environment variable is set to force fallback mode
  if (process.env.NEXT_PUBLIC_WEBGL_FALLBACK_ENABLED === 'true') {
    return 'low';
  }

  try {
    // Test for WebGL2 support first
    if (isWebGL2Available()) {
      // Check for high-end GPU support (approximate test)
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl2');

      if (gl) {
        // Get max texture size as a rough indicator of GPU capability
        const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
        const maxSamples = gl.getParameter(gl.MAX_SAMPLES);

        // Check if device has good GPU capabilities
        if (maxTextureSize >= 8192 && maxSamples >= 4) {
          return 'high';
        }

        return 'medium';
      }
    }

    // If WebGL2 is not available, but WebGL1 is, use medium quality
    if (isWebGLAvailable()) {
      return 'medium';
    }

    // Fallback to low quality if WebGL is not available
    return 'low';
  } catch (err) {
    console.warn('Error detecting quality level:', err);
    return 'low';
  }
}

/**
 * Checks if the device has enough performance for complex 3D visualization
 * @returns {boolean} True if the device is capable of running complex visualizations
 */
export function hasAdequatePerformance() {
  // Simple detection for mobile devices which might have performance issues
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    typeof navigator !== 'undefined' ? navigator.userAgent : ''
  );

  // Basic performance check
  if (isMobile) {
    // Most mobile devices should use low quality settings
    return false;
  }

  return getRecommendedQualityLevel() !== 'low';
}

/**
 * Creates a fallback element when WebGL is not available
 * @param {string} message - The message to display
 * @param {Object} containerStyle - Optional styles for the container
 * @returns {HTMLElement} The fallback element
 */
export function createWebGLFallbackElement(message = 'Advanced 3D visualization is not available on your device', containerStyle = {}) {
  const container = document.createElement('div');

  Object.assign(container.style, {
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#050a20',
    color: 'white',
    textAlign: 'center',
    padding: '20px',
    ...containerStyle
  });

  container.innerHTML = `
    <div style="max-width: 400px;">
      <h3 style="margin-bottom: 16px; font-size: 20px;">Visualization Fallback Mode</h3>
      <p style="margin-bottom: 16px;">${message}</p>
      <p style="margin-bottom: 16px; font-size: 14px;">We're using simplified visuals for compatibility with your device.</p>
      <div style="width: 80px; height: 80px; margin: 20px auto; background: url('/textures/sun_fallback.svg') no-repeat center; background-size: contain;"></div>
    </div>
  `;

  container.setAttribute('data-testid', 'webgl-fallback');

  return container;
}
