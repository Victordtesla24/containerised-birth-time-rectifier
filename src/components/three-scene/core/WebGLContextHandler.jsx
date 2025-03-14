import React, { useEffect, useRef } from 'react';
import { useThree } from '@react-three/fiber';

/**
 * Component that handles WebGL context loss and recovery
 *
 * WebGL contexts can be lost for various reasons:
 * - System resource constraints
 * - GPU driver crashes
 * - Browser tab freezing/resuming
 * - Background tab resource management
 *
 * This component ensures the application gracefully handles these scenarios
 */
const WebGLContextHandler = ({ onContextLost, onContextRestored }) => {
  const { gl, invalidate } = useThree();
  const notificationRef = useRef(null);
  const contextLostRef = useRef(false);

  useEffect(() => {
    if (!gl?.domElement) return;

    // Handle WebGL context loss
    const handleContextLost = (event) => {
      // Prevent default behavior
      event.preventDefault();

      console.warn('WebGL context lost. Attempting to recover...');
      contextLostRef.current = true;

      // Create notification element
      if (!notificationRef.current) {
        const notification = document.createElement('div');
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.left = '50%';
        notification.style.transform = 'translateX(-50%)';
        notification.style.padding = '10px 20px';
        notification.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
        notification.style.color = 'white';
        notification.style.borderRadius = '5px';
        notification.style.zIndex = '9999';
        notification.style.fontFamily = 'sans-serif';
        notification.style.fontSize = '14px';
        notification.style.textAlign = 'center';
        notification.textContent = 'Recovering 3D rendering...';
        document.body.appendChild(notification);
        notificationRef.current = notification;
      }

      // Call optional callback
      if (onContextLost) {
        onContextLost();
      }
    };

    // Handle WebGL context restoration
    const handleContextRestored = () => {
      console.log('WebGL context restored successfully!');
      contextLostRef.current = false;

      // Remove notification if it exists
      if (notificationRef.current) {
        document.body.removeChild(notificationRef.current);
        notificationRef.current = null;
      }

      // Force a re-render of the entire scene
      invalidate();

      // Call optional callback
      if (onContextRestored) {
        onContextRestored();
      }
    };

    // Add event listeners
    gl.domElement.addEventListener('webglcontextlost', handleContextLost);
    gl.domElement.addEventListener('webglcontextrestored', handleContextRestored);

    // Debug info - helps identify if context handler is active
    console.log('WebGL context handler initialized');

    // Clean up event listeners on unmount
    return () => {
      if (gl?.domElement) {
        gl.domElement.removeEventListener('webglcontextlost', handleContextLost);
        gl.domElement.removeEventListener('webglcontextrestored', handleContextRestored);
      }

      // Clean up notification if it exists
      if (notificationRef.current) {
        document.body.removeChild(notificationRef.current);
        notificationRef.current = null;
      }
    };
  }, [gl, invalidate, onContextLost, onContextRestored]);

  // Set up one-time context check for tests only
  useEffect(() => {
    // Check context only once at startup for tests
    const checkContextOnce = () => {
      if (!gl || contextLostRef.current) return;

      try {
        // Perform a simple, non-intrusive WebGL check that won't cause CPU spikes
        if (gl.isContextLost && gl.isContextLost()) {
          console.warn('WebGL context is lost on initial check');
          contextLostRef.current = true;

          // Create notification element only if needed
          if (!notificationRef.current) {
            const notification = document.createElement('div');
            notification.setAttribute('data-testid', 'webgl-error-notification');
            notification.style.position = 'fixed';
            notification.style.top = '20px';
            notification.style.left = '50%';
            notification.style.transform = 'translateX(-50%)';
            notification.style.padding = '10px 20px';
            notification.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
            notification.style.color = 'white';
            notification.style.borderRadius = '5px';
            notification.style.zIndex = '9999';
            notification.style.fontFamily = 'sans-serif';
            notification.style.fontSize = '14px';
            notification.style.textAlign = 'center';
            notification.textContent = 'WebGL rendering unavailable. Using fallback mode.';
            document.body.appendChild(notification);
            notificationRef.current = notification;
          }

          // Call optional callback for parent components
          if (onContextLost) {
            onContextLost();
          }
        }
      } catch (error) {
        // If checking causes an error, the context is probably not functional
        console.warn('Error checking WebGL context, assuming context issue:', error.message);

        // Only set context lost if not already set
        if (!contextLostRef.current) {
          contextLostRef.current = true;

          // Call optional callback
          if (onContextLost) {
            onContextLost();
          }
        }
      }
    };

    // Run the check once after a short delay to let initialization complete
    const timeoutId = setTimeout(checkContextOnce, 2000);

    // Clean up timeout
    return () => {
      clearTimeout(timeoutId);
    };
  }, [gl, onContextLost]);

  // Component doesn't render anything visual
  return null;
};

export default WebGLContextHandler;
