import * as THREE from 'three';
import { useLoader } from '@react-three/fiber';
import { useState, useEffect } from 'react';

/**
 * Manages texture loading with robust error handling and fallbacks.
 * Provides a centralized system for texture asset management.
 */
class TextureManager {
  constructor() {
    this.textureLoader = new THREE.TextureLoader();
    this.textureCache = new Map();
    this.fallbacks = new Map();
    this.errorsLogged = new Set();

    // Register default fallbacks
    this.registerCategoryFallback('environment', '/textures/fallbacks/environment.jpg');
    this.registerCategoryFallback('material', '/textures/fallbacks/material.jpg');
    this.registerCategoryFallback('normal', '/textures/fallbacks/normal.jpg');
    this.registerCategoryFallback('height', '/textures/fallbacks/height.jpg');
    this.registerCategoryFallback('roughness', '/textures/fallbacks/roughness.jpg');
    this.registerCategoryFallback('metalness', '/textures/fallbacks/metalness.jpg');
    // Default fallback for any texture type
    this.registerCategoryFallback('default', '/textures/fallbacks/default.jpg');
  }

  /**
   * Register a fallback texture for a specific category
   */
  registerCategoryFallback(category, fallbackPath) {
    this.fallbacks.set(category.toLowerCase(), fallbackPath);
  }

  /**
   * Get the texture category from its path
   */
  getTextureCategory(path) {
    if (!path) return 'default';

    // Extract category from path
    const lowerPath = path.toLowerCase();

    // Check for common texture types in the path
    if (lowerPath.includes('environment') || lowerPath.includes('skybox')) return 'environment';
    if (lowerPath.includes('normal')) return 'normal';
    if (lowerPath.includes('height') || lowerPath.includes('displacement')) return 'height';
    if (lowerPath.includes('roughness')) return 'roughness';
    if (lowerPath.includes('metalness') || lowerPath.includes('metallic')) return 'metalness';
    if (lowerPath.includes('texture') || lowerPath.includes('material')) return 'material';

    return 'default';
  }

  /**
   * Get a fallback texture path based on the original texture path
   */
  getFallbackPath(path) {
    if (!path) return this.fallbacks.get('default');

    const category = this.getTextureCategory(path);
    return this.fallbacks.get(category) || this.fallbacks.get('default');
  }

  /**
   * Load a texture with retry logic
   */
  async loadTexture(path, retryCount = 0) {
    // Skip if path is empty
    if (!path) {
      const fallbackPath = this.getFallbackPath('default');
      console.warn('Empty texture path provided, using fallback:', fallbackPath);
      return this.loadTexture(fallbackPath);
    }

    // Check cache first
    if (this.textureCache.has(path)) {
      return this.textureCache.get(path);
    }

    const maxRetries = 2;

    try {
      // create a promise for texture loading
      const texture = await new Promise((resolve, reject) => {
        this.textureLoader.setCrossOrigin('anonymous');
        this.textureLoader.load(
          path,
          (loadedTexture) => {
            resolve(loadedTexture);
          },
          // Progress callback
          (xhr) => {
            // console.log(`${path} ${Math.round((xhr.loaded / xhr.total) * 100)}% loaded`);
          },
          // Error callback
          (error) => {
            reject(error);
          }
        );
      });

      // Configure texture
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.generateMipmaps = true;
      texture.name = path;

      // Cache the texture
      this.textureCache.set(path, texture);
      return texture;
    } catch (error) {
      // Only log each error once to avoid console spam
      if (!this.errorsLogged.has(path)) {
        console.warn(`Error loading texture ${path}`, error);
        this.errorsLogged.add(path);
      }

      // Retry logic
      if (retryCount < maxRetries) {
        console.log(`Retrying texture load (${retryCount + 1}/${maxRetries}): ${path}`);
        return this.loadTexture(path, retryCount + 1);
      }

      // If all retries failed, try to load a fallback texture
      const fallbackPath = this.getFallbackPath(path);

      // Prevent infinite recursion if fallbackPath is the same as path
      if (fallbackPath && fallbackPath !== path) {
        console.log(`Using fallback texture for ${path}: ${fallbackPath}`);
        return this.loadTexture(fallbackPath);
      } else {
        // Create a basic placeholder texture as a last resort
        console.error(`All attempts to load texture failed: ${path}`);
        const placeholderTexture = new THREE.Texture();
        placeholderTexture.colorSpace = THREE.SRGBColorSpace;
        placeholderTexture.minFilter = THREE.LinearFilter;
        placeholderTexture.needsUpdate = true;

        // Store in cache to prevent repeated failures
        this.textureCache.set(path, placeholderTexture);
        return placeholderTexture;
      }
    }
  }

  /**
   * Get a texture (load if needed)
   */
  getTexture(path) {
    if (this.textureCache.has(path)) {
      return this.textureCache.get(path);
    }

    // Start loading but don't wait
    this.loadTexture(path)
      .then(() => {
        // Texture is now cached for future use
      })
      .catch((error) => {
        console.error(`Failed to load texture: ${path}`, error);
      });

    // Return a placeholder while loading
    const placeholder = new THREE.Texture();
    placeholder.colorSpace = THREE.SRGBColorSpace;
    placeholder.needsUpdate = true;
    return placeholder;
  }

  /**
   * Preload textures without waiting for them
   */
  preloadTextures(paths) {
    paths.forEach(path => {
      this.loadTexture(path).catch(() => {
        // Errors are handled in loadTexture
      });
    });
  }

  /**
   * Remove textures from cache that are no longer needed
   */
  clearUnusedTextures(keysInUse) {
    const keysSet = new Set(keysInUse);

    // Don't dispose fallback textures
    const fallbackValues = Array.from(this.fallbacks.values());
    fallbackValues.forEach(fbPath => keysSet.add(fbPath));

    for (const [key, texture] of this.textureCache.entries()) {
      if (!keysSet.has(key)) {
        texture.dispose();
        this.textureCache.delete(key);
        this.errorsLogged.delete(key);
      }
    }
  }
}

// Singleton instance
const textureManager = new TextureManager();

/**
 * React hook to use the texture manager in components
 */
export function useTexture(path) {
  return useLoader(THREE.TextureLoader, path, (loader) => {
    loader.setCrossOrigin('anonymous');
  });
}

/**
 * Safe version of useTexture that won't cause errors with hook rules
 */
export function useSafeTexture(path) {
  // Use the hook unconditionally (always for the main path)
  const [texturePath, setTexturePath] = useState(path);
  const [errorOccurred, setErrorOccurred] = useState(false);

  useEffect(() => {
    // Reset error state when path changes
    setErrorOccurred(false);
    setTexturePath(path);
  }, [path]);

  // Use a try-catch in a custom callback for useLoader
  const textureWithErrorHandling = useLoader(
    THREE.TextureLoader,
    texturePath,
    (loader) => {
      loader.setCrossOrigin('anonymous');
    },
    (error) => {
      console.error(`Error loading texture ${texturePath}:`, error);
      // Only update if we haven't already switched to fallback
      if (!errorOccurred) {
        setErrorOccurred(true);
        const fallbackPath = textureManager.getFallbackPath(texturePath);
        // Only change path if fallback is different
        if (fallbackPath && fallbackPath !== texturePath) {
          setTexturePath(fallbackPath);
        }
      }
      // Return a basic placeholder texture
      const placeholderTexture = new THREE.Texture();
      placeholderTexture.needsUpdate = true;
      return placeholderTexture;
    }
  );

  return textureWithErrorHandling;
}

export default textureManager;
