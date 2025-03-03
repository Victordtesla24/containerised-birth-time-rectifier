import * as THREE from 'three';
import { ProgressiveLoader } from './ProgressiveLoader';

export interface Vector3D {
  x: number;
  y: number;
  z: number;
}

export interface CelestialLayerData {
  depth: number;
  content: 'stars' | 'nebulae' | 'galaxies';
  parallaxFactor: number;
  position: Vector3D;
}

export interface CelestialLayerConfig extends CelestialLayerData {
  loader: ProgressiveLoader;
  scene: THREE.Scene;
}

export interface CelestialBackgroundProps {
  scrollPosition?: number;
  quality?: 'low' | 'medium' | 'high';
  layers?: CelestialLayerData[];
}

export interface QualitySettings {
  size: number;
  mipmap: boolean;
  anisotropy: number;
}

export interface TextureCache {
  texture: THREE.Texture;
  quality: QualitySettings;
  lastUsed: number;
}

export interface LightingSetup {
  ambient: {
    color: string;
    intensity: number;
  };
  directional: Array<{
    color: string;
    intensity: number;
    position: Vector3D;
  }>;
}

export interface CelestialVisualizationData {
  celestialLayers: CelestialLayerData[];
  cameraPosition: Vector3D;
  lightingSetup: LightingSetup;
} 