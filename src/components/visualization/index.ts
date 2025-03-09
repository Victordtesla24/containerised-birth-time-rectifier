// Export canvas-based visualization components
export * from './canvas';

// Export Three.js-based visualization components
export * from './three';

// Export common components and utilities
export * from './common';

// Re-export the adapters with generic names for easier usage
import { CanvasVisualization } from './canvas';
import { ThreeJsVisualization } from './three';
import VisualizationAdapter from './VisualizationAdapter';

// Default export the adaptive visualization component that will
// use the appropriate implementation based on device capabilities
export default VisualizationAdapter;

// Export the adapter as a named export as well
export { VisualizationAdapter };

// Export specific implementations for explicit use when needed
export const CelestialVisualization = VisualizationAdapter;

// For backward compatibility
export { CelestialBackground } from './CelestialBackground';
export { default as ConfidenceMeter } from './ConfidenceMeter';
export { default as CelestialChart } from './CelestialChart';
