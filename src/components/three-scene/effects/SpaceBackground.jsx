import React, { useRef, useMemo, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useQuality } from '../core/QualityContext';

/**
 * Enhanced multi-layered background with parallax effect
 * Creates a dynamic background with multiple layers for depth
 */
function SpaceBackground({ mousePosition }) {
  const { qualityLevel } = useQuality();
  const bgLayersRef = useRef([]);
  const { scene } = useThree();
  const time = useRef(0);
  const loaded = useRef(false);

  // Define background layers based on quality settings
  const backgroundLayers = useMemo(() => {
    // Base number of layers based on quality level
    const layerCount = qualityLevel === 'low' ? 2 :
                      qualityLevel === 'medium' ? 3 : 4;

    // Define available background images in both folders
    const backgrounds1 = [
      '/images/backgrounds-1/galaxy-1.jpg',
      '/images/backgrounds-1/galaxy-2.jpg',
      '/images/backgrounds-1/galaxy-3.jpg',
      '/images/backgrounds-1/galaxy-4.jpg',
      '/images/backgrounds-1/space-background-1.jpg',
      '/images/backgrounds-1/space-background-2.jpg',
      '/images/backgrounds-1/space-background-3.jpg',
      '/images/backgrounds-1/space-background-4.jpg',
      '/images/backgrounds-1/space-background-5.jpg'
    ];

    const backgrounds2 = [
      '/images/backgrounds-2/space-galaxy-1.jpg',
      '/images/backgrounds-2/space-galaxy-3.jpg',
      '/images/backgrounds-2/space-galaxy-5.jpg',
      '/images/backgrounds-2/space-galaxy-7.jpg',
      '/images/backgrounds-2/space-galaxy-9.jpg'
    ];

    // Choose specific images for different layers
    const selectedBgs = [
      backgrounds1[3], // Deep background
      qualityLevel !== 'low' ? backgrounds2[0] : backgrounds1[0], // Middle layer
      qualityLevel !== 'low' ? backgrounds2[2] : backgrounds1[4], // Foreground
      qualityLevel === 'high' || qualityLevel === 'ultra' ? backgrounds2[4] : null // Extra detail
    ].filter(Boolean).slice(0, layerCount);

    // Define layer configurations
    return selectedBgs.map((path, index) => {
      const depth = 100 - index * (80 / layerCount);
      const size = 80 - index * (40 / layerCount);

      return {
        path,
        depth,
        size,
        // Parallax strength increases for closer layers
        parallaxStrength: 0.02 + (index * 0.01),
        // Rotation speed decreases for background layers
        rotationSpeed: 0.00005 / (index + 1),
        opacity: index === 0 ? 1.0 : 0.7 - (index * 0.1)
      };
    });
  }, [qualityLevel]);

  // Create and load textures with proper memory management
  useEffect(() => {
    // Use a shared texture loader
    const loader = new THREE.TextureLoader();
    const texturePromises = [];
    const textures = [];

    // Function to load a texture with proper settings
    const loadTexture = (path) => {
      return new Promise((resolve) => {
        loader.load(
          path,
          (texture) => {
            texture.encoding = THREE.sRGBEncoding;
            texture.minFilter = THREE.LinearFilter;
            texture.generateMipmaps = false; // Save memory
            textures.push(texture);
            resolve(texture);
          },
          undefined,
          (error) => {
            console.warn(`Failed to load texture: ${path}`, error);
            // Resolve anyway to continue with other textures
            resolve(null);
          }
        );
      });
    };

    // Load all textures in parallel
    backgroundLayers.forEach(layer => {
      texturePromises.push(loadTexture(layer.path));
    });

    // When all textures are loaded
    Promise.all(texturePromises).then(loadedTextures => {
      // Store valid loaded textures
      bgLayersRef.current = backgroundLayers.map((layer, index) => ({
        ...layer,
        texture: loadedTextures[index]
      })).filter(layer => layer.texture);
      loaded.current = true;
    });

    // Cleanup function
    return () => {
      // Dispose textures properly to prevent memory leaks
      textures.forEach(texture => {
        if (texture) {
          texture.dispose();
        }
      });
    };
  }, [backgroundLayers]);

  // Create the background mesh layers when textures are loaded
  useFrame((state, delta) => {
    if (!loaded.current || bgLayersRef.current.length === 0) return;

    // Increment time for subtle animation
    time.current += delta;

    // Update each layer with parallax effect
    bgLayersRef.current.forEach((layer, index) => {
      if (!layer.mesh) {
        // Create layer mesh on first render after texture loading
        // Use much larger spherical geometry for immersive background
        const geometry = new THREE.SphereGeometry(layer.depth, 32, 32);
        const material = new THREE.MeshBasicMaterial({
          map: layer.texture,
          transparent: true, // All layers are transparent for better blending
          opacity: layer.opacity,
          depthWrite: false,
          depthTest: false,
          side: THREE.BackSide, // Render on inside of sphere for immersive effect
          blending: index > 0 ? THREE.AdditiveBlending : THREE.NormalBlending
        });

        layer.mesh = new THREE.Mesh(geometry, material);
        layer.mesh.position.z = 0; // Center the sphere for proper background
        layer.mesh.renderOrder = -1000 + index; // Background renders first

        // Add to scene
        scene.add(layer.mesh);
      }

      // Apply parallax motion based on mouse position
      if (mousePosition && layer.mesh) {
        // Calculate rotation based on mouse instead of position
        // for more natural spherical parallax
        const rotationX = mousePosition.y * layer.parallaxStrength * 0.05;
        const rotationY = mousePosition.x * layer.parallaxStrength * 0.05;

        // Smooth rotation for more natural feel
        layer.mesh.rotation.x += (rotationX - (layer.mesh.rotation.x || 0)) * 0.01;
        layer.mesh.rotation.y += (rotationY - (layer.mesh.rotation.y || 0)) * 0.01;

        // Apply subtle rotation for ambient motion - different for each layer
        layer.mesh.rotation.z += layer.rotationSpeed * Math.sin(time.current * 0.05);
      }
    });

    // Set scene background
    if (scene && !scene.userData.hasParallaxBackground) {
      // Create a rich gradient background using a CubeTexture
      const gradientGenerator = (face, size) => {
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');

        // Create different gradients based on the cube face
        // for a more natural space background
        const gradient = ctx.createRadialGradient(
          size/2, size/2, 0,
          size/2, size/2, size
        );

        // Different color schemes for different faces
        switch(face) {
          case 0: // Right
            gradient.addColorStop(0, '#050a30');
            gradient.addColorStop(1, '#000000');
            break;
          case 1: // Left
            gradient.addColorStop(0, '#070a25');
            gradient.addColorStop(1, '#000000');
            break;
          case 2: // Top
            gradient.addColorStop(0, '#080818');
            gradient.addColorStop(1, '#000000');
            break;
          case 3: // Bottom
            gradient.addColorStop(0, '#050510');
            gradient.addColorStop(1, '#000000');
            break;
          case 4: // Front
            gradient.addColorStop(0, '#060a20');
            gradient.addColorStop(1, '#000000');
            break;
          case 5: // Back
            gradient.addColorStop(0, '#040610');
            gradient.addColorStop(1, '#000000');
            break;
        }

        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, size, size);
        return canvas;
      };

      // Create cube textures
      const size = 128;
      const cubeTextures = [
        gradientGenerator(0, size), // right
        gradientGenerator(1, size), // left
        gradientGenerator(2, size), // top
        gradientGenerator(3, size), // bottom
        gradientGenerator(4, size), // front
        gradientGenerator(5, size), // back
      ].map(canvas => new THREE.CanvasTexture(canvas));

      // Create cube texture
      const cubeTexture = new THREE.CubeTexture(cubeTextures);
      cubeTexture.needsUpdate = true;

      // Set as background
      scene.background = cubeTexture;
      scene.userData.hasParallaxBackground = true;
    }
  });

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Remove meshes from scene
      bgLayersRef.current.forEach(layer => {
        if (layer.mesh) {
          scene.remove(layer.mesh);
          layer.mesh.geometry.dispose();
          layer.mesh.material.dispose();
        }
      });

      // Reset scene background
      if (scene) {
        scene.background = new THREE.Color(0x000000);
        delete scene.userData.hasParallaxBackground;
      }
    };
  }, [scene]);

  return null;
}

export default SpaceBackground;
