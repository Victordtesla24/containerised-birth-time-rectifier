import * as THREE from 'three';

// Central texture cache to avoid duplicate loading
const textureCache = new Map();
const loadingPromises = new Map();
const lowResTextureCache = new Map();

// Texture resolution mapping based on quality level
const resolutionMapping = {
  ultra: {
    suffix: '-4k',
    size: 4096
  },
  high: {
    suffix: '-2k',
    size: 2048
  },
  medium: {
    suffix: '-1k',
    size: 1024
  },
  low: {
    suffix: '-512',
    size: 512
  }
};

// Default settings for textures
const defaultSettings = {
  colorSpace: THREE.SRGBColorSpace,
  generateMipmaps: true,
  minFilter: THREE.LinearMipmapLinearFilter,
  magFilter: THREE.LinearFilter,
  anisotropy: 4,
  wrapS: THREE.RepeatWrapping,
  wrapT: THREE.RepeatWrapping
};

/**
 * Advanced texture loader with quality settings, memory management and caching
 */
class AdvancedTextureLoader {
  constructor() {
    this.loader = new THREE.TextureLoader();
    this.compressionSupported = this._checkCompressionSupport();
    this.maxTextureSize = this._getMaxTextureSize();
    this.deviceMemory = navigator.deviceMemory || 4;
    this.isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

    // Set loading manager for progress tracking
    const loadingManager = new THREE.LoadingManager();
    loadingManager.onProgress = (url, loaded, total) => {
      console.log(`Loading texture: ${Math.round((loaded / total) * 100)}% (${url})`);
    };

    this.loader.manager = loadingManager;

    // Track memory usage
    this.totalTextureMemory = 0;
    this.textureMemoryLimit = this._calculateMemoryLimit();

    console.log('Texture system initialized:', {
      compressionSupported: this.compressionSupported,
      maxTextureSize: this.maxTextureSize,
      memoryLimit: `${Math.round(this.textureMemoryLimit / (1024 * 1024))}MB`
    });
  }

  /**
   * Check WebGL compression format support
   */
  _checkCompressionSupport() {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');

    if (!gl) return { astc: false, etc: false, s3tc: false, pvrtc: false };

    return {
      astc: !!gl.getExtension('WEBGL_compressed_texture_astc'),
      etc: !!gl.getExtension('WEBGL_compressed_texture_etc'),
      s3tc: !!gl.getExtension('WEBGL_compressed_texture_s3tc'),
      pvrtc: !!gl.getExtension('WEBGL_compressed_texture_pvrtc')
    };
  }

  /**
   * Get maximum texture size supported by GPU
   */
  _getMaxTextureSize() {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    return gl ? gl.getParameter(gl.MAX_TEXTURE_SIZE) : 2048;
  }

  /**
   * Calculate texture memory limit based on device capabilities
   */
  _calculateMemoryLimit() {
    // Base limit on device memory and GPU capabilities
    const baseMemory = this.deviceMemory * 128 * 1024 * 1024; // MB to bytes
    const maxTextureInfluence = (this.maxTextureSize / 8192) * 256 * 1024 * 1024;
    const mobileReduction = this.isMobile ? 0.5 : 1.0;

    return Math.min(baseMemory, maxTextureInfluence) * mobileReduction;
  }

  /**
   * Calculate approximate memory usage of a texture
   */
  _calculateTextureMemoryUsage(texture) {
    if (!texture) return 0;

    const width = texture.image ? texture.image.width : 1;
    const height = texture.image ? texture.image.height : 1;
    const bytesPerPixel = 4; // RGBA
    const mipmapFactor = texture.generateMipmaps ? 1.33 : 1.0;

    return width * height * bytesPerPixel * mipmapFactor;
  }

  /**
   * Load a texture with quality-based resolution
   * @param {string} basePath - Base path to the texture without quality suffix
   * @param {string} qualityLevel - Quality level (ultra, high, medium, low)
   * @param {object} settings - Additional texture settings
   * @returns {Promise<THREE.Texture>}
   */
  async loadTexture(basePath, qualityLevel = 'high', settings = {}) {
    // Determine actual quality level based on device capabilities
    const actualQuality = this._adjustQualityForDevice(qualityLevel);

    // Extract base path and extension
    const lastDotIndex = basePath.lastIndexOf('.');
    const baseWithoutExt = lastDotIndex > 0 ? basePath.substring(0, lastDotIndex) : basePath;
    const extension = lastDotIndex > 0 ? basePath.substring(lastDotIndex) : '.jpg';

    // Construct path with quality suffix
    const resolution = resolutionMapping[actualQuality];
    const texturePath = `${baseWithoutExt}${resolution.suffix}${extension}`;

    // Check if texture is already cached
    if (textureCache.has(texturePath)) {
      return textureCache.get(texturePath);
    }

    // Check if texture is already loading
    if (loadingPromises.has(texturePath)) {
      return loadingPromises.get(texturePath);
    }

    // Start with low-res version while high-res loads (progressive loading)
    const lowResPath = `${baseWithoutExt}-512${extension}`;
    let lowResTexture = null;

    // Try to load low-res version first if not already cached
    if (actualQuality !== 'low' && !lowResTextureCache.has(lowResPath)) {
      try {
        const lowResPromise = this._loadTextureInternal(lowResPath, { generateMipmaps: false });
        lowResTextureCache.set(lowResPath, lowResPromise);
        lowResTexture = await lowResPromise;
      } catch (error) {
        console.warn(`Failed to load low-res texture: ${lowResPath}`, error);
      }
    } else if (lowResTextureCache.has(lowResPath)) {
      lowResTexture = await lowResTextureCache.get(lowResPath);
    }

    // Load the full resolution texture
    const loadPromise = new Promise((resolve, reject) => {
      // If we have a low-res texture, return it immediately while high-res loads
      if (lowResTexture) {
        resolve(lowResTexture);
      }

      this._loadTextureInternal(texturePath, settings)
        .then(texture => {
          // Replace low-res with high-res
          textureCache.set(texturePath, texture);

          // Update texture memory tracking
          this.totalTextureMemory += this._calculateTextureMemoryUsage(texture);
          this._enforceMemoryLimit();

          // If we didn't already resolve with low-res, resolve now
          if (!lowResTexture) {
            resolve(texture);
          } else {
            // Replace the texture in all materials using the low-res version
            this._replaceTexture(lowResTexture, texture);
          }
        })
        .catch(error => {
          console.error(`Failed to load texture: ${texturePath}`, error);

          // If we have low-res texture, keep using it
          if (lowResTexture) {
            console.warn(`Falling back to low-res texture for: ${texturePath}`);
            textureCache.set(texturePath, lowResTexture);
          } else {
            reject(error);
          }
        });
    });

    loadingPromises.set(texturePath, loadPromise);
    return loadPromise;
  }

  /**
   * Internal texture loading function
   */
  _loadTextureInternal(path, settings = {}) {
    return new Promise((resolve, reject) => {
      this.loader.load(
        path,
        texture => {
          // Apply default settings and overrides
          const finalSettings = { ...defaultSettings, ...settings };
          Object.keys(finalSettings).forEach(key => {
            texture[key] = finalSettings[key];
          });

          // Adjust anisotropy to GPU capabilities
          const renderer = this._getRenderer();
          if (renderer) {
            const maxAnisotropy = renderer.capabilities.getMaxAnisotropy();
            texture.anisotropy = Math.min(finalSettings.anisotropy, maxAnisotropy);
          }

          resolve(texture);
        },
        undefined,
        error => {
          console.error(`Error loading texture ${path}:`, error);
          reject(error);
        }
      );
    });
  }

  /**
   * Adjust quality level based on device capabilities
   */
  _adjustQualityForDevice(requestedQuality) {
    // Enforce maximum texture size limits
    const requestedSize = resolutionMapping[requestedQuality].size;

    if (requestedSize > this.maxTextureSize) {
      if (this.maxTextureSize >= 2048) return 'high';
      if (this.maxTextureSize >= 1024) return 'medium';
      return 'low';
    }

    // Adjust based on available memory
    if (this.deviceMemory <= 2 && requestedQuality !== 'low') {
      return 'low';
    } else if (this.deviceMemory <= 4 && requestedQuality === 'ultra') {
      return 'high';
    }

    // Mobile devices limited to high quality
    if (this.isMobile && requestedQuality === 'ultra') {
      return 'high';
    }

    return requestedQuality;
  }

  /**
   * Keep memory usage below limit by disposing least recently used textures
   */
  _enforceMemoryLimit() {
    if (this.totalTextureMemory <= this.textureMemoryLimit) return;

    // Sort textures by last access time
    const textureEntries = Array.from(textureCache.entries())
      .map(([path, texture]) => ({
        path,
        texture,
        lastAccess: texture.userData.lastAccess || 0,
        size: this._calculateTextureMemoryUsage(texture)
      }))
      .sort((a, b) => a.lastAccess - b.lastAccess);

    // Remove textures until under memory limit
    let disposedMemory = 0;
    const memoryToFree = this.totalTextureMemory - this.textureMemoryLimit * 0.8;

    for (const entry of textureEntries) {
      // Skip textures currently in use
      if (entry.texture.userData.referenceCount > 0) continue;

      // Dispose texture and remove from cache
      entry.texture.dispose();
      textureCache.delete(entry.path);
      disposedMemory += entry.size;

      console.log(`Disposed texture: ${entry.path} (${Math.round(entry.size / 1024)}KB)`);

      if (disposedMemory >= memoryToFree) break;
    }

    this.totalTextureMemory -= disposedMemory;
  }

  /**
   * Replace low-res texture with high-res in all materials
   */
  _replaceTexture(oldTexture, newTexture) {
    if (!oldTexture || !newTexture) return;

    // Copy UV transformations
    newTexture.offset.copy(oldTexture.offset);
    newTexture.repeat.copy(oldTexture.repeat);
    newTexture.center.copy(oldTexture.center);
    newTexture.rotation = oldTexture.rotation;

    // Find all materials using this texture
    THREE.Object3D.prototype.traverse.call(
      this._getSceneRoot(),
      object => {
        if (!object.isMesh) return;

        if (object.material) {
          const materials = Array.isArray(object.material) ? object.material : [object.material];

          materials.forEach(material => {
            // Check all possible texture slots
            ['map', 'normalMap', 'bumpMap', 'specularMap', 'emissiveMap', 'roughnessMap', 'metalnessMap', 'aoMap']
              .forEach(mapName => {
                if (material[mapName] === oldTexture) {
                  material[mapName] = newTexture;
                  material.needsUpdate = true;
                }
              });

            // Check uniforms for shader materials
            if (material.uniforms) {
              Object.values(material.uniforms).forEach(uniform => {
                if (uniform.value === oldTexture) {
                  uniform.value = newTexture;
                  material.needsUpdate = true;
                }
              });
            }
          });
        }
      }
    );
  }

  /**
   * Get reference to THREE.js renderer from the scene
   */
  _getRenderer() {
    // Try to find the renderer in the global scope
    // This is a bit hacky but necessary for integration with React Three Fiber
    return window.__THREE_RENDERER__ || null;
  }

  /**
   * Get reference to scene root
   */
  _getSceneRoot() {
    return window.__THREE_SCENE__ || { traverse: () => {} };
  }

  /**
   * Preload a batch of textures for a specific quality level
   * @param {Array} texturePaths - Array of texture base paths
   * @param {string} qualityLevel - Quality level to load
   */
  preloadTextures(texturePaths, qualityLevel = 'high') {
    return Promise.all(
      texturePaths.map(path => this.loadTexture(path, qualityLevel, { generateMipmaps: true }))
    );
  }

  /**
   * Dispose all textures and clear cache
   */
  dispose() {
    textureCache.forEach(texture => {
      texture.dispose();
    });

    textureCache.clear();
    loadingPromises.clear();

    lowResTextureCache.forEach(promise => {
      promise.then(texture => {
        if (texture) texture.dispose();
      });
    });

    lowResTextureCache.clear();
    this.totalTextureMemory = 0;
  }
}

// Create singleton instance
const textureLoader = new AdvancedTextureLoader();

// Add references to THREE renderer and scene for texture replacement
if (typeof window !== 'undefined') {
  // Patch THREE.WebGLRenderer to store reference
  const originalWebGLRendererConstructor = THREE.WebGLRenderer;
  THREE.WebGLRenderer = function(...args) {
    const renderer = new originalWebGLRendererConstructor(...args);
    window.__THREE_RENDERER__ = renderer;

    // Patch to restore reference if context is lost and restored
    const originalSetAnimationLoop = renderer.setAnimationLoop;
    renderer.setAnimationLoop = function(callback) {
      if (callback) {
        const wrappedCallback = (...args) => {
          window.__THREE_RENDERER__ = renderer;
          return callback(...args);
        };
        return originalSetAnimationLoop.call(this, wrappedCallback);
      }
      return originalSetAnimationLoop.call(this, callback);
    };

    return renderer;
  };

  // Patch THREE.Scene to store reference
  const originalSceneConstructor = THREE.Scene;
  THREE.Scene = function(...args) {
    const scene = new originalSceneConstructor(...args);
    window.__THREE_SCENE__ = scene;
    return scene;
  };
}

export default textureLoader;
