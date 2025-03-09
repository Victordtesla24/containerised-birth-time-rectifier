import textureLoader from './TextureLoader';
import * as THREE from 'three';
import { useQuality } from '../components/three-scene/core/QualityContext';

// Essential textures required for initial rendering
const ESSENTIAL_TEXTURES = [
  '/images/planets/sun/sun-surface',
  '/images/planets/sun/corona-mask',
  '/images/planets/earth/earth-surface',
  '/images/background/stars',
  '/images/background/nebula'
];

// Non-essential textures loaded after initial rendering
const NON_ESSENTIAL_TEXTURES = [
  '/images/planets/sun/sun-chromatic',
  '/images/planets/sun/sun-normal-map',
  '/images/planets/sun/sun-spots',
  '/images/planets/mercury/mercury-surface',
  '/images/planets/venus/venus-surface',
  '/images/planets/earth/earth-normal',
  '/images/planets/earth/earth-specular',
  '/images/planets/mars/mars-surface',
  '/images/planets/jupiter/jupiter-surface',
  '/images/planets/saturn/saturn-surface',
  '/images/planets/saturn/saturn-rings',
  '/images/planets/uranus/uranus-surface',
  '/images/planets/neptune/neptune-surface',
  '/images/background/milky-way'
];

// Map of all solar system texture files for every planet
const PLANET_TEXTURE_MAP = {
  sun: [
    '/images/planets/sun/sun-surface',
    '/images/planets/sun/sun-chromatic',
    '/images/planets/sun/sun-normal-map',
    '/images/planets/sun/sun-spots',
    '/images/planets/sun/corona-mask'
  ],
  mercury: [
    '/images/planets/mercury/mercury-surface',
    '/images/planets/mercury/mercury-normal'
  ],
  venus: [
    '/images/planets/venus/venus-surface',
    '/images/planets/venus/venus-normal'
  ],
  earth: [
    '/images/planets/earth/earth-surface',
    '/images/planets/earth/earth-normal',
    '/images/planets/earth/earth-specular',
    '/images/planets/earth/earth-clouds',
    '/images/planets/earth/earth-night'
  ],
  mars: [
    '/images/planets/mars/mars-surface',
    '/images/planets/mars/mars-normal'
  ],
  jupiter: [
    '/images/planets/jupiter/jupiter-surface'
  ],
  saturn: [
    '/images/planets/saturn/saturn-surface',
    '/images/planets/saturn/saturn-rings'
  ],
  uranus: [
    '/images/planets/uranus/uranus-surface'
  ],
  neptune: [
    '/images/planets/neptune/neptune-surface'
  ],
  background: [
    '/images/background/stars',
    '/images/background/nebula',
    '/images/background/milky-way'
  ]
};

/**
 * Solar system preloader that manages texture loading with visual feedback
 */
class SolarSystemPreloader {
  constructor() {
    this.loadedEssentialTextures = false;
    this.loadedAllTextures = false;
    this.progressCallbacks = [];
    this.completeCallbacks = [];
    this.essentialCallbacks = [];
    this.totalProgress = 0;
    this.progressByCategory = {};

    // Track loading by category
    Object.keys(PLANET_TEXTURE_MAP).forEach(category => {
      this.progressByCategory[category] = 0;
    });

    // Listen for web worker messages if supported
    if (typeof Worker !== 'undefined' && typeof window !== 'undefined') {
      this._setupWorkerListener();
    }
  }

  /**
   * Set up listener for web worker loading (if used)
   */
  _setupWorkerListener() {
    // Listen for messages from texture loading worker
    window.addEventListener('message', (event) => {
      if (event.data.type === 'TEXTURE_LOADED') {
        this._updateProgress(event.data.path, event.data.success);
      }
    });
  }

  /**
   * Update progress based on loaded texture
   */
  _updateProgress(path, success) {
    if (!path) return;

    // Determine which category this texture belongs to
    let category = 'other';
    for (const [cat, paths] of Object.entries(PLANET_TEXTURE_MAP)) {
      if (paths.some(p => path.includes(p))) {
        category = cat;
        break;
      }
    }

    // Update category progress
    const totalInCategory = PLANET_TEXTURE_MAP[category]?.length || 1;
    this.progressByCategory[category] =
      ((this.progressByCategory[category] || 0) * totalInCategory + 1) / totalInCategory;

    // Update total progress
    let total = 0;
    let count = 0;
    Object.values(this.progressByCategory).forEach(progress => {
      total += progress;
      count++;
    });

    this.totalProgress = total / count;

    // Notify progress listeners
    this._notifyProgressListeners();

    // Check if essential textures are loaded
    if (!this.loadedEssentialTextures) {
      const essentialComplete = ESSENTIAL_TEXTURES.every(texPath =>
        PLANET_TEXTURE_MAP[this._getCategoryFromPath(texPath)]?.some(p =>
          path.includes(p) && success
        )
      );

      if (essentialComplete) {
        this.loadedEssentialTextures = true;
        this._notifyEssentialListeners();
      }
    }

    // Check if all textures are loaded
    if (!this.loadedAllTextures && this.totalProgress >= 0.99) {
      this.loadedAllTextures = true;
      this._notifyCompleteListeners();
    }
  }

  /**
   * Get category from texture path
   */
  _getCategoryFromPath(path) {
    for (const [category, paths] of Object.entries(PLANET_TEXTURE_MAP)) {
      if (paths.some(p => path.includes(p))) {
        return category;
      }
    }
    return 'other';
  }

  /**
   * Notify progress listeners
   */
  _notifyProgressListeners() {
    this.progressCallbacks.forEach(callback => {
      try {
        callback(this.totalProgress, this.progressByCategory);
      } catch (error) {
        console.error('Error in progress callback:', error);
      }
    });
  }

  /**
   * Notify essential textures loaded listeners
   */
  _notifyEssentialListeners() {
    this.essentialCallbacks.forEach(callback => {
      try {
        callback();
      } catch (error) {
        console.error('Error in essential complete callback:', error);
      }
    });
  }

  /**
   * Notify complete listeners
   */
  _notifyCompleteListeners() {
    this.completeCallbacks.forEach(callback => {
      try {
        callback();
      } catch (error) {
        console.error('Error in complete callback:', error);
      }
    });
  }

  /**
   * Preload all essential textures with the specified quality level
   */
  preloadEssentialTextures(qualityLevel = 'high') {
    console.log(`Preloading essential textures (${qualityLevel})...`);

    return textureLoader.preloadTextures(ESSENTIAL_TEXTURES, qualityLevel)
      .then(textures => {
        console.log(`Essential textures loaded. (${textures.length} textures)`);
        this.loadedEssentialTextures = true;
        this._notifyEssentialListeners();
        return textures;
      })
      .catch(error => {
        console.error('Error preloading essential textures:', error);
        // Continue anyway to allow fallback rendering
        this.loadedEssentialTextures = true;
        this._notifyEssentialListeners();
        return [];
      });
  }

  /**
   * Preload non-essential textures after essentials are loaded
   */
  preloadAllTextures(qualityLevel = 'high') {
    // First make sure essential textures are loaded
    const preloadPromise = this.loadedEssentialTextures
      ? Promise.resolve()
      : this.preloadEssentialTextures(qualityLevel);

    return preloadPromise.then(() => {
      console.log(`Preloading remaining textures (${qualityLevel})...`);

      return textureLoader.preloadTextures(NON_ESSENTIAL_TEXTURES, qualityLevel)
        .then(textures => {
          console.log(`All textures loaded. (${textures.length} additional textures)`);
          this.loadedAllTextures = true;
          this._notifyCompleteListeners();
          return textures;
        })
        .catch(error => {
          console.error('Error preloading all textures:', error);
          // Continue anyway with what we have
          this.loadedAllTextures = true;
          this._notifyCompleteListeners();
          return [];
        });
    });
  }

  /**
   * Preload textures for a specific planet
   */
  preloadPlanetTextures(planet, qualityLevel = 'high') {
    const planetTextures = PLANET_TEXTURE_MAP[planet] || [];
    if (planetTextures.length === 0) {
      console.warn(`No textures found for planet: ${planet}`);
      return Promise.resolve([]);
    }

    console.log(`Preloading textures for ${planet}...`);
    return textureLoader.preloadTextures(planetTextures, qualityLevel);
  }

  /**
   * Register a callback for loading progress updates
   */
  onProgress(callback) {
    if (typeof callback === 'function') {
      this.progressCallbacks.push(callback);
    }
    return this; // For chaining
  }

  /**
   * Register a callback for when essential textures are loaded
   */
  onEssentialLoaded(callback) {
    if (typeof callback === 'function') {
      this.essentialCallbacks.push(callback);
      // Call immediately if already loaded
      if (this.loadedEssentialTextures) {
        callback();
      }
    }
    return this; // For chaining
  }

  /**
   * Register a callback for when all textures are loaded
   */
  onComplete(callback) {
    if (typeof callback === 'function') {
      this.completeCallbacks.push(callback);
      // Call immediately if already loaded
      if (this.loadedAllTextures) {
        callback();
      }
    }
    return this; // For chaining
  }

  /**
   * Remove progress callback
   */
  removeProgressCallback(callback) {
    this.progressCallbacks = this.progressCallbacks.filter(cb => cb !== callback);
    return this;
  }

  /**
   * Remove essential loaded callback
   */
  removeEssentialCallback(callback) {
    this.essentialCallbacks = this.essentialCallbacks.filter(cb => cb !== callback);
    return this;
  }

  /**
   * Remove complete callback
   */
  removeCompleteCallback(callback) {
    this.completeCallbacks = this.completeCallbacks.filter(cb => cb !== callback);
    return this;
  }

  /**
   * Reset preloader state
   */
  reset() {
    this.loadedEssentialTextures = false;
    this.loadedAllTextures = false;
    this.totalProgress = 0;
    Object.keys(this.progressByCategory).forEach(category => {
      this.progressByCategory[category] = 0;
    });
  }
}

// Create a singleton instance
const preloader = new SolarSystemPreloader();

/**
 * React hook for using the preloader
 */
export function usePreloader() {
  const { qualityLevel } = useQuality();

  return {
    preloadEssentialTextures: () => preloader.preloadEssentialTextures(qualityLevel),
    preloadAllTextures: () => preloader.preloadAllTextures(qualityLevel),
    preloadPlanetTextures: (planet) => preloader.preloadPlanetTextures(planet, qualityLevel),
    onProgress: (callback) => preloader.onProgress(callback),
    onEssentialLoaded: (callback) => preloader.onEssentialLoaded(callback),
    onComplete: (callback) => preloader.onComplete(callback),
    removeProgressCallback: (callback) => preloader.removeProgressCallback(callback),
    removeEssentialCallback: (callback) => preloader.removeEssentialCallback(callback),
    removeCompleteCallback: (callback) => preloader.removeCompleteCallback(callback),
    getTotalProgress: () => preloader.totalProgress,
    getCategoryProgress: (category) => preloader.progressByCategory[category] || 0,
    isEssentialLoaded: () => preloader.loadedEssentialTextures,
    isComplete: () => preloader.loadedAllTextures
  };
}

export default preloader;
