// Type definitions for astrological entities

// Planet interface for 3D visualization
export interface Planet {
  id: string;
  name: string;
  position: {
    x: number;
    y: number;
    z: number;
  };
  rotation: {
    x: number;
    y: number;
    z: number;
  };
  scale: number;
  color?: string;
  symbol?: string;
  aspectColor?: string;
}

// Birth chart data structure
export interface BirthChart {
  planets: PlanetPosition[];
  houses: House[];
  aspects: Aspect[];
  ascendant: number;
  midheaven: number;
}

// Planet position in birth chart
export interface PlanetPosition {
  name: string;
  longitude: number;
  latitude: number;
  speed: number;
  housePosition: number;
  sign: string;
  signLongitude: number;
  retrograde: boolean;
}

// House in birth chart
export interface House {
  number: number;
  cusp: number;
  sign: string;
}

// Aspect between planets
export interface Aspect {
  planet1: string;
  planet2: string;
  type: string;
  orb: number;
  description?: string;
}

// Rectification result
export interface RectificationResult {
  originalTime: string;
  rectifiedTime: string;
  confidence: number;
  ascendant: {
    original: number;
    rectified: number;
  };
  midheaven: {
    original: number;
    rectified: number;
  };
  planetaryShifts: {
    name: string;
    originalPosition: number;
    rectifiedPosition: number;
    houseCrossing: boolean;
  }[];
}
