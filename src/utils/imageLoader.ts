/**
 * Utility functions for loading and managing image assets
 */

export type ImageCategory = 'backgrounds-1' | 'backgrounds-2' | 'nebulea' | 'planets';
export type PlanetCategory = 'sun' | 'moon' | 'mercury' | 'venus' | 'mars' | 'jupiter' | 'saturn';

/**
 * Maps an image filename to its full path
 */
export const getImagePath = (
  category: ImageCategory,
  filename: string,
  subCategory?: PlanetCategory
): string => {
  if (category === 'planets' && subCategory) {
    return `${category}/${subCategory}/${filename}`;
  }
  return `${category}/${filename}`;
};

/**
 * Gets a random image from a specific category
 */
export const getRandomImageFromCategory = (
  category: ImageCategory,
  subCategory?: PlanetCategory
): string => {
  // Define image sets - this could be expanded with an API call to get directory contents
  const imageSets: Record<ImageCategory, Record<string, string[]>> = {
    'backgrounds-1': {
      'default': [
        'space-background-1.jpg',
        'space-background-2.jpg',
        'space-background-3.jpg',
        'space-background-4.jpg',
        'space-background-5.jpg',
        'galaxy-1.jpg',
        'galaxy-2.jpg',
        'galaxy-3.jpg',
        'galaxy-4.jpg',
      ]
    },
    'backgrounds-2': {
      'default': [
        'space-galaxy-1.jpg',
        'space-galaxy-2.jpg',
        'space-galaxy-3.jpg',
        'space-galaxy-4.jpg',
        'space-galaxy-5.jpg',
        'space-galaxy-6.jpg',
        'space-galaxy-7.jpg',
        'space-galaxy-8.jpg',
        'space-galaxy-9.jpg',
        'space-galaxy-10.jpg',
        'space-galaxy-11.jpg',
      ]
    },
    'nebulea': {
      'default': [
        'nebula-1.jpg',
        'nebula-2.jpg',
        'nebula-4.jpg',
        'nebula-6.jpg',
      ]
    },
    'planets': {
      'sun': [
        'sun-1.jpg',
        'sun-2.jpg',
        'sun-3.jpg',
        'sun-4.jpg',
        'sun-5.jpg',
        'sun-mercury-1.jpg',
      ],
      'mercury': [
        'mercury-1.jpg',
        'mercury-2.jpg',
        'mercury-3.jpg',
      ],
      'venus': [
        'venus-2.jpg',
        'venus-3.jpg',
        'venus.png',
      ],
      'mars': [
        'mars-3.jpg',
        'mars.jpg',
      ],
      'jupiter': [
        'jupiter-3.jpg',
      ],
      'saturn': [
        'saturn-1.jpg',
        'saturn-2.jpg',
        'saturn-3.jpg',
        'saturn-4.jpg',
        'saturn-5.jpg',
        'saturn-6.jpg',
        'saturn-7.jpg',
        'saturn-8.jpg',
      ],
      'default': []
    }
  };

  // Get the appropriate image set
  const imageSet = subCategory 
    ? imageSets[category][subCategory] || imageSets[category]['default']
    : imageSets[category]['default'];
  
  if (!imageSet || imageSet.length === 0) {
    // Fallback: if we requested a planet but didn't specify which one, pick one randomly
    if (category === 'planets' && !subCategory) {
      const planetTypes: PlanetCategory[] = ['sun', 'mercury', 'venus', 'mars', 'jupiter', 'saturn'];
      const randomPlanet = planetTypes[Math.floor(Math.random() * planetTypes.length)];
      return getRandomImageFromCategory(category, randomPlanet);
    }
    return '';
  }
  
  // Select a random image
  const randomIndex = Math.floor(Math.random() * imageSet.length);
  const filename = imageSet[randomIndex];
  
  return getImagePath(category, filename, subCategory);
};

/**
 * Preloads a set of images to improve user experience
 */
export const preloadImages = (imagePaths: string[]): Promise<void[]> => {
  return Promise.all(
    imagePaths.map(path => {
      return new Promise<void>((resolve) => {
        const img = new Image();
        img.src = path.startsWith('/') ? path : `/images/${path}`;
        img.onload = () => resolve();
        img.onerror = () => resolve(); // Resolve even on error to avoid blocking
      });
    })
  );
};

/**
 * Creates a set of layers suitable for the ParallaxCelestialBackground component
 */
export const createParallaxLayers = (numLayers: number = 3): { src: string; depth: number; opacity: number }[] => {
  const layers = [];
  
  // Add a base star layer
  layers.push({
    src: getRandomImageFromCategory('backgrounds-1'),
    depth: 0,
    opacity: 1
  });
  
  // Add nebula layers
  if (numLayers >= 2) {
    layers.push({
      src: getRandomImageFromCategory('nebulea'),
      depth: 2,
      opacity: 0.7
    });
  }
  
  // Add galaxy layers
  if (numLayers >= 3) {
    layers.push({
      src: getRandomImageFromCategory('backgrounds-2'),
      depth: 4,
      opacity: 0.5
    });
  }
  
  return layers;
}; 