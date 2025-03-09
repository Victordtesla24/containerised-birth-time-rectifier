import * as THREE from 'three';

/**
 * Load nebula textures with enhanced error handling and optimizations
 *
 * @param {Array} nebulaImages Array of nebula texture URLs
 * @param {number} textureCount Number of textures to load
 * @param {string} qualityLevel Current quality level ('low', 'medium', 'high')
 * @param {WebGLRenderer} gl Three.js WebGL renderer for capability detection
 * @returns {Promise} Promise resolving to array of loaded textures
 */
const loadNebulaTextures = (nebulaImages, textureCount, qualityLevel, gl) => {
  return new Promise((resolve) => {
    const textureLoader = new THREE.TextureLoader();
    const textures = [];
    const texturePromises = [];

    // Select which nebula images to use based on quality level
    const selectedNebulaImages = nebulaImages.slice(0, textureCount);

    // Load each texture with proper error handling and optimization
    selectedNebulaImages.forEach((url, index) => {
      const promise = new Promise((resolve) => {
        textureLoader.load(
          url,
          // Success callback with optimized settings
          (loadedTexture) => {
            // Configure texture for better quality and performance
            loadedTexture.encoding = THREE.sRGBEncoding;
            loadedTexture.wrapS = loadedTexture.wrapT = THREE.MirroredRepeatWrapping;

            // Optimize filtering based on quality level
            if (qualityLevel === 'low') {
              loadedTexture.minFilter = THREE.LinearFilter;
              loadedTexture.generateMipmaps = false; // Save memory on low-end devices
            } else {
              loadedTexture.minFilter = THREE.LinearMipmapLinearFilter;
              loadedTexture.generateMipmaps = true;
            }

            // Set appropriate anisotropy based on device capability and quality level
            const maxAnisotropy = gl.capabilities.getMaxAnisotropy();
            loadedTexture.anisotropy = qualityLevel === 'low' ?
                                      Math.min(2, maxAnisotropy) :
                                      qualityLevel === 'medium' ?
                                      Math.min(8, maxAnisotropy) :
                                      maxAnisotropy;

            textures[index] = loadedTexture;
            resolve();
          },
          // Progress callback
          undefined,
          // Error callback with better handling
          (error) => {
            console.warn(`Failed to load nebula texture ${url}:`, error);
            // Create a placeholder texture with a color gradient
            const canvas = document.createElement('canvas');
            canvas.width = 256;
            canvas.height = 256;
            const ctx = canvas.getContext('2d');
            const gradient = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
            gradient.addColorStop(0, index === 0 ? '#113355' : index === 1 ? '#551133' : '#335511');
            gradient.addColorStop(1, '#000');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, 256, 256);

            const fallbackTexture = new THREE.CanvasTexture(canvas);
            fallbackTexture.wrapS = fallbackTexture.wrapT = THREE.MirroredRepeatWrapping;
            textures[index] = fallbackTexture;
            resolve();
          }
        );
      });
      texturePromises.push(promise);
    });

    // When all textures are loaded, resolve the promise
    Promise.all(texturePromises).then(() => {
      const validTextures = textures.filter(Boolean); // Filter out any null textures
      console.log(`Loaded ${validTextures.length} nebula textures`);
      resolve(validTextures);
    });
  });
};

/**
 * Load a skybox texture with HDR-like setup
 *
 * @param {Array} backgroundImages Array of background texture URLs
 * @param {string} qualityLevel Current quality level ('low', 'medium', 'high')
 * @param {WebGLRenderer} gl Three.js WebGL renderer for capability detection
 * @returns {Promise} Promise resolving to loaded skybox texture
 */
const loadSkyboxTexture = (backgroundImages, qualityLevel, gl) => {
  return new Promise((resolve) => {
    const textureLoader = new THREE.TextureLoader();

    // Choose background image based on quality - higher quality uses more dramatic backgrounds
    const backgroundIndex = qualityLevel === 'low' ? 0 :
                           qualityLevel === 'medium' ? 5 : 6;

    textureLoader.load(
      backgroundImages[backgroundIndex],
      (loadedTexture) => {
        loadedTexture.encoding = THREE.sRGBEncoding;
        // Use equirectangular mapping for better sky representation
        loadedTexture.mapping = THREE.EquirectangularReflectionMapping;

        // Adjust texture quality based on device capability
        if (qualityLevel !== 'low') {
          loadedTexture.minFilter = THREE.LinearMipmapLinearFilter;
          loadedTexture.generateMipmaps = true;
          loadedTexture.anisotropy = gl.capabilities.getMaxAnisotropy();
        }

        resolve(loadedTexture);
      },
      undefined,
      (error) => {
        console.warn('Failed to load skybox texture:', error);
        // Create a simple gradient fallback
        const canvas = document.createElement('canvas');
        canvas.width = 512;
        canvas.height = 512;
        const ctx = canvas.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 512);
        gradient.addColorStop(0, '#000510');
        gradient.addColorStop(1, '#000');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 512, 512);

        // Add some "stars"
        for (let i = 0; i < 500; i++) {
          const x = Math.random() * 512;
          const y = Math.random() * 512;
          const r = Math.random() * 1.5 + 0.5;
          ctx.beginPath();
          ctx.arc(x, y, r, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255,255,255,${Math.random() * 0.8 + 0.2})`;
          ctx.fill();
        }

        const fallbackTexture = new THREE.CanvasTexture(canvas);
        fallbackTexture.mapping = THREE.EquirectangularReflectionMapping;
        resolve(fallbackTexture);
      }
    );
  });
};

// Create a named object before exporting to fix linting warnings
const TextureLoaderUtils = {
  loadNebulaTextures,
  loadSkyboxTexture
};

export default TextureLoaderUtils;
