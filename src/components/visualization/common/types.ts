/**
 * Common interfaces and types for visualization components
 */

// Quality level definitions
export type QualityLevel = 'low' | 'medium' | 'high' | 'ultra';

// Common props for celestial visualizations
export interface CelestialVisualizationProps {
  /** Enable or disable shooting stars effect */
  enableShootingStars?: boolean;
  /** Enable or disable orbital paths */
  enableOrbits?: boolean;
  /** Enable or disable nebula effects */
  enableNebulaEffects?: boolean;
  /** Enable or disable mouse interactions */
  mouseInteractive?: boolean;
  /** Set quality level for rendering */
  quality?: QualityLevel;
  /** Depth of perspective effect */
  perspectiveDepth?: number;
  /** Number of particles to render */
  particleCount?: number;
}

// Mouse position interface
export interface MousePosition {
  x: number;
  y: number;
}

// Shared shader settings
export interface ShaderSettings {
  /** Early optimization for transparent fragments */
  transparencyOptimization?: boolean;
  /** Light culling optimization */
  lightCulling?: boolean;
  /** Bloom effect settings */
  bloom?: {
    enabled: boolean;
    intensity: number;
    threshold: number;
    radius: number;
  };
}
