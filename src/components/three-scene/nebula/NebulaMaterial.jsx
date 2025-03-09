import React, { useMemo } from 'react';
import * as THREE from 'three';
import NebulaShaders from './NebulaShaders';

/**
 * Create an advanced nebula shader material with optimized settings
 *
 * @param {Object} props - Material properties and dependencies
 * @param {Array} props.loadedTextures - Array of loaded nebula textures
 * @param {string} props.qualityLevel - Current quality level ('low', 'medium', 'high')
 * @returns {THREE.ShaderMaterial} Configured shader material for the nebula
 */
const createNebulaMaterial = ({ loadedTextures, qualityLevel }) => {
  // Check if textures are loaded
  if (!loadedTextures || loadedTextures.length === 0) {
    return null;
  }

  // Create an advanced volumetric nebula shader with enhanced visuals and performance
  return new THREE.ShaderMaterial({
    uniforms: {
      time: { value: 0 },
      nebulaTextures: { value: loadedTextures },
      textureCount: { value: loadedTextures.length },
      // Enhanced color palette for more visually appealing cosmic nebula
      baseColor: { value: new THREE.Color('#061224') },      // Deeper blue base
      accentColor: { value: new THREE.Color('#304878') },    // Rich blue accent
      glowColor: { value: new THREE.Color('#6090ff') },      // Brighter blue glow
      dustColor: { value: new THREE.Color('#ff5040') },      // Warmer dust color
      cloudColor: { value: new THREE.Color('#80c0ff') },     // Brighter cloud color
      resolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
      intensity: {
        // Higher intensity values for more pronounced nebula effects
        value: qualityLevel === 'low' ? 1.0 :
               qualityLevel === 'medium' ? 1.5 : 2.0
      },
      // cameraPosition is already defined by Three.js - using different name
      viewerPosition: { value: new THREE.Vector3() },
      mousePosition: { value: new THREE.Vector2() },
      mouseVelocity: { value: new THREE.Vector2(0, 0) },
      // Enhanced parallax strength for more dramatic effect
      parallaxStrength: {
        value: qualityLevel === 'low' ? 0.03 :
               qualityLevel === 'medium' ? 0.08 : 0.12
      },
      viewportAspect: { value: window.innerWidth / window.innerHeight }
    },
    vertexShader: NebulaShaders.vertexShader,
    fragmentShader: NebulaShaders.fragmentShader,
    transparent: true,
    depthWrite: false,
    side: THREE.BackSide,
    blending: THREE.AdditiveBlending,
  });
};

/**
 * Creates a nebula material with optimized performance and memory management
 * This component only handles the material creation, not the rendering or animation
 */
const NebulaMaterialUtils = {
  createNebulaMaterial
};

export default NebulaMaterialUtils;
