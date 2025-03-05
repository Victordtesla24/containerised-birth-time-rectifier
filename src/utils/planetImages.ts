/**
 * Planet image path utilities for consistent planet imagery across the application
 */

// Planet types
export type PlanetType =
  | 'sun'
  | 'moon'
  | 'mercury'
  | 'venus'
  | 'mars'
  | 'jupiter'
  | 'saturn'
  | 'uranus'
  | 'neptune'
  | 'pluto';

// Function to get a standardized planet image path
export const getPlanetImagePath = (planetName: string): string => {
  const planet = planetName.toLowerCase() as PlanetType;

  // Define available images for each planet - using absolute paths to prevent path resolution issues
  const planetImages: Record<PlanetType, string[]> = {
    sun: [
      '/images/planets/sun/sun-1.jpg',
      '/images/planets/sun/sun-2.jpg',
      '/images/planets/sun/sun-3.jpg',
      '/images/planets/sun/sun-4.jpg',
      '/images/planets/sun/sun-5.jpg',
    ],
    moon: [
      '/images/planets/moon/moon-1.jpg',
      '/images/planets/moon/moon-2.jpg',
    ],
    mercury: [
      '/images/planets/mercury/mercury-1.jpg',
      '/images/planets/mercury/mercury-2.jpg',
      '/images/planets/mercury/mercury-3.jpg',
    ],
    venus: [
      '/images/planets/venus/venus-2.jpg',
      '/images/planets/venus/venus-3.jpg',
    ],
    mars: [
      '/images/planets/mars/mars.jpg',
      '/images/planets/mars/mars-3.jpg',
    ],
    jupiter: [
      '/images/planets/jupiter/jupiter-3.jpg',
    ],
    saturn: [
      '/images/planets/saturn/saturn-1.jpg',
      '/images/planets/saturn/saturn-2.jpg',
      '/images/planets/saturn/saturn-3.jpg',
      '/images/planets/saturn/saturn-4.jpg',
      '/images/planets/saturn/saturn-5.jpg',
      '/images/planets/saturn/saturn-6.jpg',
      '/images/planets/saturn/saturn-7.jpg',
      '/images/planets/saturn/saturn-8.jpg',
    ],
    uranus: [
      '/images/planets/jupiter/jupiter-3.jpg', // Fallback to Jupiter if Uranus images don't exist
    ],
    neptune: [
      '/images/planets/saturn/saturn-4.jpg', // Fallback to Saturn if Neptune images don't exist
    ],
    pluto: [
      '/images/planets/mercury/mercury-2.jpg', // Fallback to Mercury if Pluto images don't exist
    ],
  };

  // Get the image array for the specified planet or default to sun
  const images = planetImages[planet] || planetImages.sun;

  // Return first image, or a random one if returnRandom is true
  return images[0];
};

// Get a specific planet image by index (0-based)
export const getPlanetImageByIndex = (planetName: string, index: number): string => {
  const planet = planetName.toLowerCase() as PlanetType;

  // Get the image array for the specified planet or default to sun
  const images = getPlanetImagePaths(planet);

  // Ensure index is within bounds
  const safeIndex = Math.max(0, Math.min(index, images.length - 1));

  return images[safeIndex];
};

// Get all image paths for a specific planet
export const getPlanetImagePaths = (planetName: string): string[] => {
  const planet = planetName.toLowerCase() as PlanetType;

  const planetImages: Record<PlanetType, string[]> = {
    sun: [
      '/images/planets/sun/sun-1.jpg',
      '/images/planets/sun/sun-2.jpg',
      '/images/planets/sun/sun-3.jpg',
      '/images/planets/sun/sun-4.jpg',
      '/images/planets/sun/sun-5.jpg',
    ],
    moon: [
      '/images/planets/moon/moon-1.jpg',
      '/images/planets/moon/moon-2.jpg',
    ],
    mercury: [
      '/images/planets/mercury/mercury-1.jpg',
      '/images/planets/mercury/mercury-2.jpg',
      '/images/planets/mercury/mercury-3.jpg',
    ],
    venus: [
      '/images/planets/venus/venus-2.jpg',
      '/images/planets/venus/venus-3.jpg',
    ],
    mars: [
      '/images/planets/mars/mars.jpg',
      '/images/planets/mars/mars-3.jpg',
    ],
    jupiter: [
      '/images/planets/jupiter/jupiter-3.jpg',
    ],
    saturn: [
      '/images/planets/saturn/saturn-1.jpg',
      '/images/planets/saturn/saturn-2.jpg',
      '/images/planets/saturn/saturn-3.jpg',
      '/images/planets/saturn/saturn-4.jpg',
      '/images/planets/saturn/saturn-5.jpg',
      '/images/planets/saturn/saturn-6.jpg',
      '/images/planets/saturn/saturn-7.jpg',
      '/images/planets/saturn/saturn-8.jpg',
    ],
    uranus: [
      '/images/planets/jupiter/jupiter-3.jpg',
    ],
    neptune: [
      '/images/planets/saturn/saturn-4.jpg',
    ],
    pluto: [
      '/images/planets/mercury/mercury-2.jpg',
    ],
  };

  return planetImages[planet] || planetImages.sun;
};

// Get fallback color for planets
export const getPlanetFallbackColor = (planetName: string): string => {
  const planet = planetName.toLowerCase();

  switch (planet) {
    case 'sun': return '#ff9900';
    case 'moon': return '#e0e0e0';
    case 'mercury': return '#95a5a6';
    case 'venus': return '#2ecc71';
    case 'mars': return '#e74c3c';
    case 'jupiter': return '#f39c12';
    case 'saturn': return '#d35400';
    case 'uranus': return '#3498db';
    case 'neptune': return '#2980b9';
    case 'pluto': return '#34495e';
    default: return '#3B82F6';
  }
};

// Get glow color for planets
export const getPlanetGlowColor = (planetName: string): string => {
  const planet = planetName.toLowerCase();

  switch (planet) {
    case 'sun': return 'rgba(255, 160, 60, 0.8)';
    case 'moon': return 'rgba(220, 220, 240, 0.5)';
    case 'mercury': return 'rgba(150, 165, 166, 0.6)';
    case 'venus': return 'rgba(200, 255, 200, 0.6)';
    case 'mars': return 'rgba(255, 100, 100, 0.6)';
    case 'jupiter': return 'rgba(255, 200, 100, 0.6)';
    case 'saturn': return 'rgba(255, 140, 80, 0.6)';
    case 'uranus': return 'rgba(100, 200, 255, 0.6)';
    case 'neptune': return 'rgba(80, 150, 255, 0.6)';
    case 'pluto': return 'rgba(100, 100, 120, 0.6)';
    default: return 'rgba(100, 200, 255, 0.6)';
  }
};

// Get all planet image paths (for preloading)
export const getAllPlanetImagePaths = (): string[] => {
  const planets: PlanetType[] = [
    'sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn'
  ];

  return planets.map(planet => getPlanetImagePath(planet));
};
