import { ChartData } from '@/types';

export interface ChartRendererProps {
  data: ChartData;
  width?: number;
  height?: number;
  showLabels?: boolean;
  onPlanetClick?: (planetId: string) => void;
  selectedDivisionalChart?: string;
  showCelestialLayers?: boolean;
}

export interface ChartDimensions {
  width: number;
  height: number;
  radius: number;
  centerX: number;
  centerY: number;
}

export interface PlanetRenderData {
  id: string;
  name: string;
  x: number;
  y: number;
  degree: number;
  house: number;
  speed: number;
}

export interface HouseRenderData {
  number: number;
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  midpointX: number;
  midpointY: number;
  startDegree: number;
  endDegree: number;
}

export interface AspectData {
  planet1: string;
  planet2: string;
  aspect: number;
  orb: number;
}

export interface ChartTransform {
  scale: number;
  pan: {
    x: number;
    y: number;
  };
}

export interface CelestialLayerRenderData {
  depth: number;
  parallaxFactor: number;
  gradient: {
    startColor: string;
    endColor: string;
    opacity: number;
  };
} 