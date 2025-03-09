/**
 * TextureManager
 * Manages texture loading, fallbacks, and cache for optimal WebGL performance
 */
import * as THREE from 'three';

class TextureManager {
  constructor() {
    this.textureCache = {};
    this.fallbackTextures = {};
    this.defaultTexture = null;
    this.initialized = false;

    // Initialize with default fallback texture
    this.initialize();
  }

  /**
   * Initialize the texture manager with a default fallback texture
   * @returns {boolean} Whether initialization was successful
   */
  initialize() {
    if (this.initialized) return true;

    try {
      // Create a simple canvas for the default fallback texture
      const canvas = document.createElement('canvas');
      canvas.width = 64;
      canvas.height = 64;
      const ctx = canvas.getContext('2d');

      // Draw a simple pattern (checkerboard)
      ctx.fillStyle = '#252525';
      ctx.fillRect(0, 0, 64, 64);
      ctx.fillStyle = '#303030';

      for (let x = 0; x < 8; x++) {
        for (let y = 0; y < 8; y++) {
          if ((x + y) % 2 === 0) {
            ctx.fillRect(x * 8, y * 8, 8, 8);
          }
        }
      }

      // Create a texture from the canvas
      this.defaultTexture = new THREE.CanvasTexture(canvas);
      this.defaultTexture.name = 'default-fallback';
      this.defaultTexture.colorSpace = THREE.SRGBColorSpace;

      this.initialized = true;
      return true;
    } catch (error) {
      console.error('Failed to initialize TextureManager:', error);
      return false;
    }
  }

  /**
   * Register a fallback texture for a specific category
   * @param {string} category - The texture category (e.g. 'planet', 'star')
   * @param {string} url - Path to the fallback texture
   */
  registerFallback(category, url) {
    this.fallbackTextures[category] = url;
  }

  /**
   * Get a cached texture by URL
   * @param {string} url - The texture URL
   * @returns {THREE.Texture|null} The cached texture or null if not found
   */
  getCachedTexture(url) {
    return this.textureCache[url] || null;
  }

  /**
   * Load a texture with retry mechanism and fallbacks
   * @param {string} url - The texture URL to load
   * @param {Object} options - Additional options
   * @param {string} options.category - The texture category for fallbacks
   * @param {number} options.maxRetries - Maximum number of retries (default: 2)
   * @param {number} options.retryDelay - Delay between retries in ms (default: 1000)
   * @param {Function} options.onProgress - Progress callback (receives 0-1 value)
   * @returns {Promise<THREE.Texture>} A promise resolving to the loaded texture
   */
  async loadTexture(url, options = {}) {
    const {
      category = 'default',
      maxRetries = 2,
      retryDelay = 1000,
      onProgress = null
    } = options;

    // Check if texture is already cached
    const cachedTexture = this.getCachedTexture(url);
    if (cachedTexture) {
      if (onProgress) onProgress(1);
      return cachedTexture;
    }

    // Attempt to load texture with retries
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        // Notify progress at start
        if (onProgress) onProgress(0);

        // Create a loader with progress tracking
        const loader = new THREE.TextureLoader();

        if (onProgress) {
          loader.onProgress = (xhr) => {
            if (xhr.lengthComputable) {
              const percentComplete = xhr.loaded / xhr.total;
              onProgress(percentComplete);
            }
          };
        }

        // Load the texture
        const texture = await new Promise((resolve, reject) => {
          loader.load(
            url,
            (texture) => {
              // Successfully loaded
              if (onProgress) onProgress(1);
              resolve(texture);
            },
            // Progress callback handled above
            undefined,
            // Error callback
            (error) => {
              reject(error);
            }
          );
        });

        // Configure and cache the texture
        texture.name = url.split('/').pop();
        texture.colorSpace = THREE.SRGBColorSpace;

        // Cache the texture
        this.textureCache[url] = texture;

        return texture;
      } catch (error) {
        if (attempt >= maxRetries) {
          console.warn(`Failed to load texture ${url} after ${maxRetries} retries. Using fallback.`);

          // Try category fallback
          if (category && this.fallbackTextures[category]) {
            try {
              console.info(`Using category fallback for ${category}: ${this.fallbackTextures[category]}`);
              return await this.loadTexture(this.fallbackTextures[category], {
                category: null, // Prevent infinite recursion
                maxRetries: 0, // Don't retry fallbacks
                onProgress
              });
            } catch (fallbackError) {
              console.error('Failed to load fallback texture:', fallbackError);
            }
          }

          // Return default fallback texture as last resort
          if (this.defaultTexture) {
            return this.defaultTexture;
          }

          // If all else fails, throw the original error
          throw error;
        }

        // Retry after delay
        console.warn(`Texture load failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying...`, error);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
      }
    }

    // This shouldn't be reached due to the error handling above, but just in case
    throw new Error(`Failed to load texture: ${url}`);
  }

  /**
   * Preload a set of textures in parallel
   * @param {Array<string>} urls - Array of texture URLs to preload
   * @param {Object} options - Additional options (see loadTexture)
   * @returns {Promise<Object>} A promise resolving to an object mapping URLs to textures
   */
  async preloadTextures(urls, options = {}) {
    const results = {};
    const tasks = urls.map(async url => {
      try {
        const texture = await this.loadTexture(url, options);
        results[url] = texture;
      } catch (error) {
        console.error(`Failed to preload texture: ${url}`, error);
        results[url] = null;
      }
    });

    await Promise.all(tasks);
    return results;
  }

  /**
   * Clear the entire texture cache, or specific textures
   * @param {Array<string>} [urls] - Optional array of specific texture URLs to clear
   */
  clearCache(urls) {
    if (urls && Array.isArray(urls)) {
      // Clear specific textures
      urls.forEach(url => {
        const texture = this.textureCache[url];
        if (texture) {
          texture.dispose();
          delete this.textureCache[url];
        }
      });
    } else {
      // Clear all textures
      Object.values(this.textureCache).forEach(texture => {
        if (texture) {
          texture.dispose();
        }
      });
      this.textureCache = {};
    }
  }

  /**
   * Dispose of the texture manager and all cached textures
   */
  dispose() {
    this.clearCache();

    if (this.defaultTexture) {
      this.defaultTexture.dispose();
      this.defaultTexture = null;
    }

    this.fallbackTextures = {};
    this.initialized = false;
  }
}

// Create a singleton instance
const textureManager = new TextureManager();

export default textureManager;
