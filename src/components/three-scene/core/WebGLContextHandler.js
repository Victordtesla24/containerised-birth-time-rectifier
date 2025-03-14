import { useEffect, useRef } from 'react';
import { useThree } from '@react-three/fiber';

/**
 * Component that handles WebGL context loss and restoration gracefully.
 * Attaches event listeners to the WebGL canvas to detect context problems
 * and provides recovery mechanisms.
 */
export function WebGLContextHandler() {
  const { gl, invalidate } = useThree();
  const errorMessageRef = useRef(null);

  useEffect(() => {
    if (!gl || !gl.domElement) return;

    // Handler for WebGL context loss
    const handleContextLost = (event) => {
      event.preventDefault(); // Allows for context restoration
      console.warn('WebGL context lost. Trying to recover...');

      // Create a user-visible error message
      if (!errorMessageRef.current && typeof document !== 'undefined') {
        const errorDiv = document.createElement('div');
        errorDiv.style.position = 'fixed';
        errorDiv.style.top = '50%';
        errorDiv.style.left = '50%';
        errorDiv.style.transform = 'translate(-50%, -50%)';
        errorDiv.style.background = 'rgba(0, 0, 0, 0.8)';
        errorDiv.style.color = 'white';
        errorDiv.style.padding = '20px';
        errorDiv.style.borderRadius = '8px';
        errorDiv.style.textAlign = 'center';
        errorDiv.style.zIndex = '1000';

        errorDiv.innerHTML = `
          <h3 style="color: #ef4444; margin-bottom: 10px;">Graphics Error</h3>
          <p>WebGL context was lost. Please wait while we try to recover.</p>
        `;

        document.body.appendChild(errorDiv);
        errorMessageRef.current = errorDiv;
      }

      // Try to reduce quality settings if available
      try {
        if (typeof window !== 'undefined' && window.__reduceQuality) {
          window.__reduceQuality();
        }
      } catch (e) {
        console.error('Error reducing quality:', e);
      }
    };

    // Handler for WebGL context restoration
    const handleContextRestored = () => {
      console.log('WebGL context restored. Resuming rendering.');

      // Remove error message if it exists
      if (errorMessageRef.current && typeof document !== 'undefined') {
        document.body.removeChild(errorMessageRef.current);
        errorMessageRef.current = null;
      }

      // Force a re-render of the scene
      invalidate();
    };

    // Add event listeners
    gl.domElement.addEventListener('webglcontextlost', handleContextLost);
    gl.domElement.addEventListener('webglcontextrestored', handleContextRestored);

    // Clean up event listeners on unmount
    return () => {
      gl.domElement.removeEventListener('webglcontextlost', handleContextLost);
      gl.domElement.removeEventListener('webglcontextrestored', handleContextRestored);

      // Remove any error message if component unmounts
      if (errorMessageRef.current && typeof document !== 'undefined') {
        try {
          document.body.removeChild(errorMessageRef.current);
        } catch (e) {
          console.warn('Error removing WebGL error message:', e);
        }
        errorMessageRef.current = null;
      }
    };
  }, [gl, invalidate]);

  // This component doesn't render anything itself
  return null;
}

export default WebGLContextHandler;
