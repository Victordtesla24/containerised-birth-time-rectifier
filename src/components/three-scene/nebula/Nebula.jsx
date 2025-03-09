import React, { useRef, useMemo, useState, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useQuality } from '../core/QualityContext';
import TextureLoader from '../utils/TextureLoader';
import NebulaMaterial from './NebulaMaterial';

/**
 * Enhanced nebula effect with advanced volumetric ray marching and parallax
 *
 * @param {Object} props - Component props
 * @param {Object} props.mousePosition - Current mouse position for parallax effects
 */
const Nebula = ({ mousePosition }) => {
  const nebulaMeshRef = useRef();
  const textureRefs = useRef([]);
  const time = useRef(0);
  const { qualityLevel } = useQuality();
  const { gl } = useThree();

  // Available nebula images - using correct folder name
  const nebulaImages = useMemo(() => [
    '/images/nebulea/nebula-1.jpg',
    '/images/nebulea/nebula-2.jpg',
    '/images/nebulea/nebula-4.jpg',
    '/images/nebulea/nebula-6.jpg'
  ], []);

  // Available background images for the skybox
  const backgroundImages = useMemo(() => [
    '/images/backgrounds-1/space-background-1.jpg',
    '/images/backgrounds-1/space-background-2.jpg',
    '/images/backgrounds-1/space-background-3.jpg',
    '/images/backgrounds-1/space-background-4.jpg',
    '/images/backgrounds-1/space-background-5.jpg',
    '/images/backgrounds-1/galaxy-1.jpg',
    '/images/backgrounds-1/galaxy-2.jpg'
  ], []);

  // Determine how many textures to load based on quality level
  const textureCount = useMemo(() => {
    return qualityLevel === 'low' ? 1 :
           qualityLevel === 'medium' ? 2 :
           qualityLevel === 'high' ? 4 : 4;
  }, [qualityLevel]);

  // Use appropriate geometry detail based on quality level for better performance
  const sphereDetail = useMemo(() => {
    return qualityLevel === 'low' ? 16 :
           qualityLevel === 'medium' ? 32 :
           qualityLevel === 'high' ? 48 : 64;
  }, [qualityLevel]);

  // Safely load textures with error handling
  const [loadedTextures, setLoadedTextures] = useState([]);
  const [skyboxTexture, setSkyboxTexture] = useState(null);
  const [texturesLoaded, setTexturesLoaded] = useState(false);

  // Load the nebula textures with enhanced quality settings and memory management
  useEffect(() => {
    // Load nebula and skybox textures using the texture loader utility
    const loadTextures = async () => {
      try {
        // Load nebula textures
        const nebulaTextures = await TextureLoader.loadNebulaTextures(
          nebulaImages,
          textureCount,
          qualityLevel,
          gl
        );

        // Load skybox texture
        const skybox = await TextureLoader.loadSkyboxTexture(
          backgroundImages,
          qualityLevel,
          gl
        );

        // Update state with loaded textures
        setLoadedTextures(nebulaTextures);
        setSkyboxTexture(skybox);
        setTexturesLoaded(true);
      } catch (error) {
        console.error("Error loading textures:", error);
      }
    };

    loadTextures();

    // Cleanup function to dispose textures
    return () => {
      loadedTextures.forEach(texture => {
        if (texture) texture.dispose();
      });

      if (skyboxTexture) skyboxTexture.dispose();
    };
  }, [nebulaImages, backgroundImages, textureCount, gl.capabilities, qualityLevel, gl]);

  // Update the scene background with the skybox and enable HDR-like effects
  const { scene, camera } = useThree();
  useEffect(() => {
    if (skyboxTexture) {
      scene.background = skyboxTexture;

      // Apply a subtle color adjustment to the background for better astronomical appearance
      if (qualityLevel !== 'low') {
        // Enhanced environment with scientifically accurate space coloring
        const prevBackground = scene.background;

        // Adjust color to simulate the slight blue shift of distant objects in space
        if (typeof prevBackground.isColor !== 'undefined') {
          const hslColor = {h: 0, s: 0, l: 0};
          prevBackground.getHSL(hslColor);
          // Add slight blue shift (scientific accuracy for cosmic background)
          hslColor.h = THREE.MathUtils.lerp(hslColor.h, 0.6, 0.15); // Shift toward blue
          hslColor.s = THREE.MathUtils.clamp(hslColor.s * 1.1, 0, 1); // Slightly more saturated
          hslColor.l = THREE.MathUtils.clamp(hslColor.l * 0.85, 0, 1); // Slightly darker

          scene.background = new THREE.Color().setHSL(hslColor.h, hslColor.s, hslColor.l);
        } else {
          // Fallback for when background is a texture or something else
          scene.background = new THREE.Color(0x000814);
        }

        // Enable scene tone mapping for HDR-like appearance
        try {
          if (gl.toneMapping !== THREE.ACESFilmicToneMapping) {
            gl.toneMapping = THREE.ACESFilmicToneMapping;
            gl.toneMappingExposure = 1.2;
            gl.outputEncoding = THREE.sRGBEncoding;
          }
        } catch (e) {
          console.warn('Tone mapping not fully supported:', e);
        }
      }
    }

    return () => {
      scene.background = new THREE.Color(0x000000);
      // Reset tone mapping if needed
      try {
        if (gl.toneMapping !== THREE.NoToneMapping) {
          gl.toneMapping = THREE.NoToneMapping;
          gl.toneMappingExposure = 1.0;
        }
      } catch (e) {
        console.warn('Error resetting tone mapping:', e);
      }
    };
  }, [skyboxTexture, scene, qualityLevel, gl]);

  // Refs for improved camera-relative and mouse-based parallax
  const cameraPositionRef = useRef(new THREE.Vector3());
  const mousePositionRef = useRef(new THREE.Vector2(0, 0));
  const lastMousePosition = useRef({ x: 0, y: 0 });
  const mouseVelocityRef = useRef(new THREE.Vector2(0, 0));

  // Create enhanced nebula material with advanced volumetric effects
  const nebulaMaterial = useMemo(() => {
    return NebulaMaterial.createNebulaMaterial({
      loadedTextures,
      qualityLevel
    });
  }, [loadedTextures, qualityLevel]);

  // Animate nebula with optimized movement and parallax effects
  useFrame((state, delta) => {
    if (!nebulaMeshRef.current || !nebulaMaterial) return;

    // Update mouse velocity for parallax momentum
    if (mousePosition) {
      const currentMouse = { x: mousePosition.x, y: mousePosition.y };
      const dx = currentMouse.x - lastMousePosition.current.x;
      const dy = currentMouse.y - lastMousePosition.current.y;

      // Apply smoothing to velocity
      mouseVelocityRef.current.x = mouseVelocityRef.current.x * 0.9 + dx * 0.1;
      mouseVelocityRef.current.y = mouseVelocityRef.current.y * 0.9 + dy * 0.1;

      lastMousePosition.current = currentMouse;

      // Update shader uniforms with mouse data
      nebulaMaterial.uniforms.mousePosition.value.set(mousePosition.x, mousePosition.y);
      nebulaMaterial.uniforms.mouseVelocity.value.copy(mouseVelocityRef.current);
    }

    // Accumulate time more slowly on lower-end devices
    const timeMultiplier = qualityLevel === 'low' ? 0.05 :
                          qualityLevel === 'medium' ? 0.1 : 0.15;

    time.current += delta * timeMultiplier;
    nebulaMaterial.uniforms.time.value = time.current;

    // Update camera position for shader-based parallax
    camera.getWorldPosition(cameraPositionRef.current);
    // Use viewerPosition instead of cameraPosition to avoid conflicts with built-in uniform
    if (nebulaMaterial.uniforms.viewerPosition) {
      nebulaMaterial.uniforms.viewerPosition.value.copy(cameraPositionRef.current);
    }

    // Apply smooth rotation for a majestic space feeling
    if (state.clock.elapsedTime % 2 < delta) {
      nebulaMeshRef.current.rotation.x += delta * 0.005;
      nebulaMeshRef.current.rotation.y += delta * 0.003;
      nebulaMeshRef.current.rotation.z += delta * 0.002;
    }
  });

  // Render the nebula mesh with a sphere geometry
  return (
    <mesh ref={nebulaMeshRef}>
      <sphereGeometry args={[1, sphereDetail, sphereDetail]} />
      {nebulaMaterial && <primitive object={nebulaMaterial} attach="material" />}
    </mesh>
  );
};

export default Nebula;
