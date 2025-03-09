import React, { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import { useQuality } from '../core/QualityContext';
import * as THREE from 'three';
import textureManager from '../utils/TextureManager';

/**
 * AdaptivePlanetSystem component that adjusts detail level based on
 * quality settings from QualityContext
 */
const AdaptivePlanetSystem = ({ mousePosition = { x: 0, y: 0 } }) => {
  const { qualityLevel, shadows, pixelRatio } = useQuality();

  // References for animation
  const groupRef = useRef();
  const sunRef = useRef();
  const planetsRef = useRef([]);

  // Define planet system properties - quality-dependent
  const systemConfig = useMemo(() => {
    // Base configuration for planet system
    const config = {
      sun: {
        radius: 3,
        detail: qualityLevel === 'low' ? 16 : qualityLevel === 'medium' ? 32 : 48,
        emissiveIntensity: 1.2,
        lightIntensity: 1.5
      },
      planets: [
        {
          name: 'mercury',
          radius: 0.4,
          detail: qualityLevel === 'low' ? 8 : 16,
          distance: 5,
          rotationSpeed: 0.01,
          orbitSpeed: 0.008,
          texturePath: '/textures/planets/mercury/mercury.jpg'
        },
        {
          name: 'venus',
          radius: 0.9,
          detail: qualityLevel === 'low' ? 12 : 24,
          distance: 7.2,
          rotationSpeed: 0.008,
          orbitSpeed: 0.006,
          texturePath: '/textures/planets/venus/venus.jpg'
        },
        {
          name: 'earth',
          radius: 1,
          detail: qualityLevel === 'low' ? 16 : 32,
          distance: 10,
          rotationSpeed: 0.012,
          orbitSpeed: 0.004,
          texturePath: '/textures/planets/earth/earth.jpg',
          bumpMap: qualityLevel !== 'low' ? '/textures/planets/earth/earth_bump.jpg' : null,
          specularMap: qualityLevel === 'high' ? '/textures/planets/earth/earth_specular.jpg' : null,
          cloudsTexture: qualityLevel !== 'low' ? '/textures/planets/earth/earth_clouds.png' : null,
          cloudsOpacity: 0.4,
          atmosphere: qualityLevel === 'high'
        },
        {
          name: 'mars',
          radius: 0.6,
          detail: qualityLevel === 'low' ? 12 : 24,
          distance: 13,
          rotationSpeed: 0.01,
          orbitSpeed: 0.003,
          texturePath: '/textures/planets/mars/mars.jpg'
        },
        {
          name: 'jupiter',
          radius: 2.2,
          detail: qualityLevel === 'low' ? 20 : 36,
          distance: 18,
          rotationSpeed: 0.02,
          orbitSpeed: 0.002,
          texturePath: '/textures/planets/jupiter/jupiter.jpg'
        }
      ],

      // Rendering settings
      renderSettings: {
        shadows: shadows && qualityLevel !== 'low',
        environmentMap: qualityLevel !== 'low',
        postProcessing: qualityLevel === 'high',
        particleDensity: qualityLevel === 'low' ? 500 : qualityLevel === 'medium' ? 2000 : 5000,
        enableBloom: qualityLevel === 'high'
      }
    };

    return config;
  }, [qualityLevel, shadows]);

  // Preload textures
  useEffect(() => {
    const texturesToLoad = systemConfig.planets
      .map(planet => {
        const textures = [planet.texturePath];
        if (planet.bumpMap) textures.push(planet.bumpMap);
        if (planet.specularMap) textures.push(planet.specularMap);
        if (planet.cloudsTexture) textures.push(planet.cloudsTexture);
        return textures;
      })
      .flat();

    textureManager.preloadTextures(texturesToLoad).then(() => {
      console.log('Planet textures preloaded successfully');
    }).catch(error => {
      console.warn('Some planet textures failed to preload:', error);
    });

    // No cleanup needed for texture preloading
  }, [systemConfig]);

  // Create shared geometry instances for performance
  const geometries = useMemo(() => {
    return {
      sun: new THREE.SphereGeometry(
        systemConfig.sun.radius,
        systemConfig.sun.detail,
        systemConfig.sun.detail
      ),
      planets: systemConfig.planets.map(planet =>
        new THREE.SphereGeometry(
          planet.radius,
          planet.detail,
          planet.detail
        )
      )
    };
  }, [systemConfig]);

  // Animation loop - adaptive based on capabilities
  useFrame((state, delta) => {
    if (!groupRef.current) return;

    // Rotate the entire system slightly based on mouse position for interactive feel
    groupRef.current.rotation.y += delta * 0.05;
    groupRef.current.rotation.x = mousePosition.y * 0.1;
    groupRef.current.rotation.y = mousePosition.x * 0.1;

    // Animate sun
    if (sunRef.current) {
      sunRef.current.rotation.y += delta * 0.1;
    }

    // Animate planets - only if they're in view
    planetsRef.current.forEach((planet, i) => {
      if (!planet) return;

      const config = systemConfig.planets[i];

      // Update planet rotation (on its axis)
      planet.rotation.y += delta * config.rotationSpeed;

      // Update orbit position
      const angle = state.clock.elapsedTime * config.orbitSpeed;
      planet.position.x = Math.sin(angle) * config.distance;
      planet.position.z = Math.cos(angle) * config.distance;
    });
  });

  // Create planets with materials optimized for selected quality level
  const createPlanet = (config, index) => {
    // Load texture with fallback
    const loadPlanetTexture = (path, type = 'color') => {
      if (!path) return null;

      // Configure texture loading options
      const textureOptions = {
        generateMipmaps: qualityLevel !== 'low',
        anisotropy: qualityLevel === 'low' ? 1 : qualityLevel === 'medium' ? 4 : 8,
        fallbackType: type
      };

      // Load and configure the texture
      return textureManager.loadTexture(path, textureOptions);
    };

    // Create materials based on quality level
    const createMaterials = () => {
      const texturePromises = [
        loadPlanetTexture(config.texturePath)
      ];

      // Add additional maps for higher quality levels
      if (config.bumpMap) {
        texturePromises.push(loadPlanetTexture(config.bumpMap, 'normal'));
      }

      if (config.specularMap) {
        texturePromises.push(loadPlanetTexture(config.specularMap, 'roughness'));
      }

      // Create appropriate material based on quality level
      return Promise.all(texturePromises).then(textures => {
        const [colorMap, bumpMap, specularMap] = textures;

        // Basic material for low quality
        if (qualityLevel === 'low') {
          return new THREE.MeshBasicMaterial({
            map: colorMap,
            color: 0xffffff
          });
        }

        // Standard material for medium quality
        if (qualityLevel === 'medium') {
          return new THREE.MeshStandardMaterial({
            map: colorMap,
            bumpMap: bumpMap || null,
            bumpScale: 0.05,
            roughness: 0.8,
            metalness: 0.1
          });
        }

        // Physical material for high quality
        return new THREE.MeshStandardMaterial({
          map: colorMap,
          bumpMap: bumpMap || null,
          bumpScale: 0.05,
          roughnessMap: specularMap || null,
          roughness: 0.7,
          metalness: 0.2,
          envMapIntensity: 0.5
        });
      });
    };

    // Create clouds for planets like Earth
    const createClouds = () => {
      if (!config.cloudsTexture || qualityLevel === 'low') return null;

      return loadPlanetTexture(config.cloudsTexture).then(texture => {
        // Create mesh for clouds
        const material = new THREE.MeshStandardMaterial({
          map: texture,
          transparent: true,
          opacity: config.cloudsOpacity || 0.8,
          blending: THREE.AdditiveBlending,
          side: THREE.FrontSide
        });

        const geometry = new THREE.SphereGeometry(
          config.radius + 0.03,
          config.detail,
          config.detail
        );

        return new THREE.Mesh(geometry, material);
      });
    };

    // Handle planet ref assignment
    const handlePlanetRef = (node) => {
      if (node) {
        // Store ref for animation
        planetsRef.current[index] = node;
      }
    };

    return (
      <group key={config.name} position={[config.distance, 0, 0]}>
        <mesh
          ref={handlePlanetRef}
          geometry={geometries.planets[index]}
          castShadow={systemConfig.renderSettings.shadows}
          receiveShadow={systemConfig.renderSettings.shadows}
        >
          {/* Material is loaded asynchronously */}
          <primitive attach="material" object={createMaterials()} />

          {/* Add atmosphere for Earth when in high quality */}
          {config.atmosphere && qualityLevel === 'high' && (
            <mesh>
              <sphereGeometry args={[config.radius + 0.12, config.detail, config.detail]} />
              <meshBasicMaterial
                color={0x6a93ff}
                transparent={true}
                opacity={0.2}
                side={THREE.BackSide}
              />
            </mesh>
          )}

          {/* Add clouds layer if available */}
          {config.cloudsTexture && (
            <primitive object={createClouds()} />
          )}
        </mesh>
      </group>
    );
  };

  // Create the sun
  const createSun = () => {
    // Load sun texture
    const texture = textureManager.loadTexture('/textures/sun.jpg', {
      generateMipmaps: qualityLevel !== 'low',
      anisotropy: qualityLevel === 'low' ? 1 : 4
    });

    // Create sun material based on quality
    const material = qualityLevel === 'low'
      ? new THREE.MeshBasicMaterial({
        map: texture,
        color: 0xffff80,
        emissive: 0xffff00,
        emissiveIntensity: systemConfig.sun.emissiveIntensity
      })
      : new THREE.MeshStandardMaterial({
        map: texture,
        emissive: 0xffff00,
        emissiveIntensity: systemConfig.sun.emissiveIntensity,
        roughness: 0.7,
        metalness: 0.0
      });

    return (
      <mesh ref={sunRef} geometry={geometries.sun} material={material}>
        {/* Add point light only when not in low quality */}
        {qualityLevel !== 'low' && (
          <pointLight
            color={0xffffff}
            intensity={systemConfig.sun.lightIntensity}
            distance={40}
            castShadow={systemConfig.renderSettings.shadows}
            shadow-mapSize-width={qualityLevel === 'high' ? 2048 : 1024}
            shadow-mapSize-height={qualityLevel === 'high' ? 2048 : 1024}
          />
        )}
      </mesh>
    );
  };

  // Add stars background if not in low quality
  const createStarfield = () => {
    if (qualityLevel === 'low') return null;

    // Determine particle count based on quality
    const particleCount = systemConfig.renderSettings.particleDensity;

    // Create star particles
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const sizes = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      // Position stars in a sphere
      const radius = 50 + Math.random() * 200;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);

      // Randomize star colors (white to blue-white)
      colors[i * 3] = 0.8 + Math.random() * 0.2;        // R
      colors[i * 3 + 1] = 0.8 + Math.random() * 0.2;    // G
      colors[i * 3 + 2] = 0.9 + Math.random() * 0.1;    // B

      // Randomize star sizes
      sizes[i] = Math.random() * 2 + 0.5;
    }

    return (
      <points>
        <bufferGeometry>
          <bufferAttribute
            attachObject={['attributes', 'position']}
            count={particleCount}
            array={positions}
            itemSize={3}
          />
          <bufferAttribute
            attachObject={['attributes', 'color']}
            count={particleCount}
            array={colors}
            itemSize={3}
          />
          <bufferAttribute
            attachObject={['attributes', 'size']}
            count={particleCount}
            array={sizes}
            itemSize={1}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.1}
          vertexColors
          sizeAttenuation
          transparent
          depthWrite={false}
        />
      </points>
    );
  };

  return (
    <group ref={groupRef}>
      {/* Ambient light for better visibility */}
      <ambientLight intensity={0.1} />

      {/* Main sun */}
      {createSun()}

      {/* Planets */}
      {systemConfig.planets.map(createPlanet)}

      {/* Starfield background */}
      {createStarfield()}
    </group>
  );
};

export default AdaptivePlanetSystem;
