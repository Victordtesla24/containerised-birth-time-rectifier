import React, { useEffect, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { useQuality } from './QualityContext';

/**
 * PerformanceMonitor component that tracks frame rates and adaptively
 * adjusts quality settings to maintain smooth performance
 */
const PerformanceMonitor = () => {
  const { gl } = useThree();
  const { adjustQualityForPerformance, autoAdjust, fpsTarget } = useQuality();

  // Reference to store performance data
  const performanceRef = useRef({
    frameCount: 0,
    lastTime: performance.now(),
    fps: 60,
    lastQualityCheck: 0,
    rollingFPS: [],
    memoryUsage: null,
    qualityReductions: 0
  });

  // Initialize performance monitoring
  useEffect(() => {
    // Set initial timestamp
    performanceRef.current.lastTime = performance.now();
    performanceRef.current.lastQualityCheck = performance.now();

    // Try to get memory info if available
    if (performance.memory) {
      try {
        performanceRef.current.memoryUsage = {
          jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
          totalJSHeapSize: performance.memory.totalJSHeapSize,
          usedJSHeapSize: performance.memory.usedJSHeapSize
        };
      } catch (e) {
        console.log('Memory performance API not available', e);
      }
    }

    // Log initial setup
    console.log('Performance monitoring initialized');

    // No cleanup needed
  }, []);

  // Track frame rate during rendering
  useFrame(() => {
    // Get current performance data
    const perfData = performanceRef.current;

    // Increment frame counter
    perfData.frameCount++;

    // Check if we should calculate FPS (every 0.5 seconds)
    const currentTime = performance.now();
    const elapsed = currentTime - perfData.lastTime;

    if (elapsed >= 500) {
      // Calculate FPS
      const fps = (perfData.frameCount / elapsed) * 1000;
      perfData.fps = Math.round(fps);

      // Add to rolling average (store last 5 measurements)
      perfData.rollingFPS.push(fps);
      if (perfData.rollingFPS.length > 5) {
        perfData.rollingFPS.shift();
      }

      // Calculate average FPS
      const avgFPS = perfData.rollingFPS.reduce((sum, val) => sum + val, 0) / perfData.rollingFPS.length;

      // Reset counters
      perfData.frameCount = 0;
      perfData.lastTime = currentTime;

      // Log performance every ~5 seconds
      if (currentTime - perfData.lastPerformanceLog > 5000) {
        console.log(`Current performance: ${Math.round(avgFPS)} FPS (target: ${fpsTarget})`);
        perfData.lastPerformanceLog = currentTime;

        // Update memory usage if available
        if (performance.memory) {
          try {
            perfData.memoryUsage = {
              jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
              totalJSHeapSize: performance.memory.totalJSHeapSize,
              usedJSHeapSize: performance.memory.usedJSHeapSize
            };

            // Log memory usage
            console.log(`Memory usage: ${Math.round(perfData.memoryUsage.usedJSHeapSize / 1048576)} MB / ${Math.round(perfData.memoryUsage.jsHeapSizeLimit / 1048576)} MB`);
          } catch (e) {
            // Ignore errors trying to access memory info
          }
        }
      }

      // Check if we should adjust quality (every ~3 seconds)
      if (autoAdjust && currentTime - perfData.lastQualityCheck > 3000) {
        // Get current renderer memory info if available
        let rendererMemoryInfo = null;
        if (gl.info && gl.info.memory) {
          rendererMemoryInfo = { ...gl.info.memory };
        }

        // Check if performance is consistently below target
        const performanceDeficit = avgFPS < fpsTarget * 0.8;

        // Check if memory usage is approaching limits
        let memoryPressure = false;
        if (perfData.memoryUsage) {
          // Consider memory pressure if over 90% of available heap
          memoryPressure = perfData.memoryUsage.usedJSHeapSize > perfData.memoryUsage.jsHeapSizeLimit * 0.9;
        }

        // Check WebGL specific memory (textures, geometries)
        let glResourcePressure = false;
        if (rendererMemoryInfo) {
          // These thresholds are somewhat arbitrary - adjust based on your scene
          glResourcePressure =
            rendererMemoryInfo.geometries > 1000 ||
            rendererMemoryInfo.textures > 100;
        }

        // If we need to adjust quality
        if (performanceDeficit || memoryPressure || glResourcePressure) {
          // Track quality reductions
          perfData.qualityReductions++;

          // Log what triggered the reduction
          console.log(`Quality adjustment needed: ${performanceDeficit ? 'Low FPS' : ''}${memoryPressure ? 'Memory pressure' : ''}${glResourcePressure ? 'GL resource pressure' : ''}`);

          // Call the quality adjustment function from context
          adjustQualityForPerformance(avgFPS);
        }
        // If performance is good, we might increase quality
        else if (avgFPS > fpsTarget * 1.2 && perfData.qualityReductions === 0) {
          adjustQualityForPerformance(avgFPS);
        }

        // Update last check time
        perfData.lastQualityCheck = currentTime;
      }
    }
  });

  // This component doesn't render anything visually
  return null;
};

export default PerformanceMonitor;
