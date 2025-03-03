import { ChartData, PlanetPosition, HouseData } from '@/types';
import { ChartDimensions, PlanetRenderData, HouseRenderData, AspectData, CelestialLayerRenderData } from './types';

export const calculateChartDimensions = (
  width: number,
  height: number
): ChartDimensions => {
  const minDimension = Math.min(width, height);
  const radius = (minDimension * 0.45) - 20; // Leave space for labels
  const centerX = width / 2;
  const centerY = height / 2;

  return {
    width,
    height,
    radius,
    centerX,
    centerY,
  };
};

export const degreesToRadians = (degrees: number): number => {
  return (degrees * Math.PI) / 180;
};

// Convert zodiac sign and degree to absolute longitude (0-360)
export const signAndDegreeToLongitude = (sign: string, degree: number): number => {
  const signs = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 
    'Leo', 'Virgo', 'Libra', 'Scorpio', 
    'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
  ];
  
  const signIndex = signs.indexOf(sign);
  if (signIndex === -1) {
    console.warn(`Unknown sign: ${sign}, defaulting to Aries`);
    return degree;
  }
  
  return (signIndex * 30) + degree;
};

export const calculatePlanetPosition = (
  planet: any, // Using any to handle both API and internal formats
  dimensions: ChartDimensions
): PlanetRenderData => {
  const { radius, centerX, centerY } = dimensions;
  
  // Handle both formats: direct longitude or sign+degree
  let longitude;
  if (typeof planet.longitude === 'number') {
    longitude = planet.longitude;
  } else if (planet.sign && typeof planet.degree === 'number') {
    longitude = signAndDegreeToLongitude(planet.sign, planet.degree);
  } else {
    console.warn('Planet has neither longitude nor sign+degree:', planet);
    // Default to 0 but try to extract from name if possible
    const defaultPos: Record<string, number> = {
      'Sun': 0, 'Moon': 30, 'Mercury': 60, 'Venus': 90,
      'Mars': 120, 'Jupiter': 150, 'Saturn': 180
    };
    longitude = defaultPos[planet.name] || 0;
  }
  
  // Convert to radians for calculation (add 90 degrees to start from the top)
  const angle = degreesToRadians(longitude + 90);
  
  // Calculate x,y coordinates
  const x = centerX + radius * Math.cos(angle);
  const y = centerY + radius * Math.sin(angle);
  
  // Get speed if available, or default to 0
  const speed = typeof planet.speed === 'number' ? planet.speed : 0;
  
  return {
    id: planet.id || planet.name,
    name: planet.name,
    x,
    y,
    degree: longitude,
    house: typeof planet.house === 'number' ? planet.house : 1,
    speed: speed,
  };
};

export const calculateHousePosition = (
  house: any, // Using any to handle both API and internal formats
  dimensions: ChartDimensions
): HouseRenderData => {
  const { radius, centerX, centerY } = dimensions;
  
  // Handle both formats: explicit degrees or derived from sign
  let startDegree, endDegree;
  
  if (house.startDegree !== undefined && house.endDegree !== undefined) {
    startDegree = house.startDegree;
    endDegree = house.endDegree;
  } else {
    // If no start/end degrees, calculate from house number (assuming equal houses)
    const houseNumber = house.number || 1;
    startDegree = (houseNumber - 1) * 30;
    endDegree = houseNumber * 30;
    
    // If sign is provided, adjust based on sign
    if (house.sign) {
      const signBaseOffset = signAndDegreeToLongitude(house.sign, 0);
      const houseOffset = (houseNumber - 1) % 12;
      startDegree = signBaseOffset + (houseOffset * 30);
      endDegree = startDegree + 30;
    }
  }
  
  // Convert to radians for calculation (add 90 degrees to start from the top)
  const startAngle = degreesToRadians(startDegree + 90);
  const endAngle = degreesToRadians(endDegree + 90);
  const midAngle = (startAngle + endAngle) / 2;

  return {
    number: house.number,
    startX: centerX + radius * Math.cos(startAngle),
    startY: centerY + radius * Math.sin(startAngle),
    endX: centerX + radius * Math.cos(endAngle),
    endY: centerY + radius * Math.sin(endAngle),
    midpointX: centerX + (radius * 0.9) * Math.cos(midAngle),
    midpointY: centerY + (radius * 0.9) * Math.sin(midAngle),
    startDegree: startDegree,
    endDegree: endDegree,
  };
};

export const getPlanetSymbol = (planetName: string): string => {
  const symbols: Record<string, string> = {
    Sun: '☉',
    Moon: '☽',
    Mercury: '☿',
    Venus: '♀',
    Mars: '♂',
    Jupiter: '♃',
    Saturn: '♄',
    Uranus: '⛢',
    Neptune: '♆',
    Pluto: '♇',
    Rahu: '☊',
    Ketu: '☋',
  };

  return symbols[planetName] || planetName[0];
};

export const calculateAspects = (planets: any[]): AspectData[] => {
  const aspects: AspectData[] = [];
  const majorAspects = [0, 60, 90, 120, 180];
  const maxOrb = 8; // Maximum orb in degrees

  // If we already have aspects provided, format them
  if (planets && planets.length > 0 && planets[0]?.aspects) {
    return planets[0].aspects.map((aspect: any) => ({
      planet1: aspect.planet1,
      planet2: aspect.planet2,
      aspect: getAspectDegree(aspect.aspectType),
      orb: aspect.orb || 0,
    }));
  }

  // Otherwise calculate aspects
  for (let i = 0; i < planets.length; i++) {
    for (let j = i + 1; j < planets.length; j++) {
      const planet1 = planets[i];
      const planet2 = planets[j];
      
      // Get longitudes for both planets
      const long1 = planet1.longitude !== undefined ? 
        planet1.longitude : 
        planet1.sign ? signAndDegreeToLongitude(planet1.sign, planet1.degree || 0) : 0;
        
      const long2 = planet2.longitude !== undefined ? 
        planet2.longitude : 
        planet2.sign ? signAndDegreeToLongitude(planet2.sign, planet2.degree || 0) : 0;
      
      let aspect = Math.abs(long1 - long2);
      if (aspect > 180) aspect = 360 - aspect;

      // Find the closest major aspect
      const closestAspect = majorAspects.reduce((prev, curr) => {
        const diffPrev = Math.abs(aspect - prev);
        const diffCurr = Math.abs(aspect - curr);
        return diffCurr < diffPrev ? curr : prev;
      });

      const orb = Math.abs(aspect - closestAspect);
      if (orb <= maxOrb) {
        aspects.push({
          planet1: planet1.name,
          planet2: planet2.name,
          aspect: closestAspect,
          orb,
        });
      }
    }
  }

  // Sort aspects by orb (tighter aspects first)
  return aspects.sort((a, b) => a.orb - b.orb);
};

// Convert aspect types to degrees
function getAspectDegree(aspectType: string): number {
  const aspectMap: Record<string, number> = {
    'Conjunction': 0,
    'Sextile': 60,
    'Square': 90,
    'Trine': 120,
    'Opposition': 180,
  };
  
  return aspectMap[aspectType] || 0;
}

export const calculateCelestialLayer = (
  layer: CelestialLayerRenderData,
  dimensions: ChartDimensions
): { gradient: CanvasGradient; radius: number } => {
  const { centerX, centerY, radius } = dimensions;
  const layerRadius = radius * (1 + layer.depth);

  const gradient = document.createElement('canvas').getContext('2d')!.createRadialGradient(
    centerX, centerY, 0,
    centerX, centerY, layerRadius
  );

  gradient.addColorStop(0, `rgba(255, 255, 255, 0)`);
  gradient.addColorStop(0.5, `rgba(255, 255, 255, ${layer.gradient.opacity * layer.parallaxFactor})`);
  gradient.addColorStop(1, `rgba(255, 255, 255, 0)`);

  return {
    gradient,
    radius: layerRadius,
  };
}; 