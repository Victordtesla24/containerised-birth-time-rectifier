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

  // Set up periodical check for context state if needed
  useEffect(() => {
    // Function to check if context is lost and attempt recovery
    const checkContextState = () => {
      if (!gl) return;

      try {
        // Try a simple WebGL operation - if context is lost, this will throw an error
        const isLost = gl.getError() === gl.CONTEXT_LOST_WEBGL;

        if (isLost && !contextLostRef.current) {
          console.warn('Detected lost WebGL context during check');
          contextLostRef.current = true;

          // Try to recover by forcing a new render frame
          invalidate();

          // Show notification if not already shown
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
        } else if (!isLost && contextLostRef.current) {
          // Context has been restored after loss
          console.log('WebGL context recovered');
          contextLostRef.current = false;

          // Remove notification if it exists
          if (notificationRef.current) {
            document.body.removeChild(notificationRef.current);
            notificationRef.current = null;
          }

          // Force a re-render
          invalidate();
        }
      } catch (error) {
        // An error here likely means the context is lost
        if (!contextLostRef.current) {
          console.warn('Error in WebGL context check, likely context lost:', error);
          contextLostRef.current = true;

          // Try to recover by forcing a new render frame
          try {
            invalidate();
          } catch (e) {
            // Ignore errors during invalidation when context is lost
          }
        }
      }
    };

    // Check context state periodically
    const intervalId = setInterval(checkContextState, 10000); // Every 10 seconds

    return () => {
      clearInterval(intervalId);
    };
  }, [gl, invalidate]);

  // Component doesn't render anything visual
  return null;
};

export default WebGLContextHandler;
