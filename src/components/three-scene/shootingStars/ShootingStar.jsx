import React, { useRef, useMemo, useEffect } from 'react';

import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

/**
 * Enhanced shooting star with realistic physical properties and visual effects
 *
 * @param {Object} props - Component properties
 * @param {Array} props.startPosition - Starting position coordinates
 * @param {Array} props.direction - Direction vector
 * @param {number} props.speed - Movement speed
 * @param {number} props.brightness - Star brightness
 * @param {number} props.length - Trail length
 * @param {Array} props.color - RGB color values
 * @param {number} props.trailOpacity - Opacity of the trail
 * @param {number} props.flicker - Amount of flicker effect
 */
const ShootingStar = ({
  startPosition,
  direction,
  speed,
  brightness,
  length,
  color = [1, 1, 1],
  trailOpacity = 0.8,
  flicker = 0.05
}) => {
  const ref = useRef();
  const time = useRef({ value: Math.random() * 10 });
  const active = useRef(true);
  const resetTimer = useRef(Math.random() * 10 + 10); // Random delay before reappearing
  const flickerOffset = useRef(Math.random() * 100); // Unique flicker pattern per star

  // Create advanced shooting star material with realistic atmospheric scattering
  const material = useMemo(() => {
    // Scientifically accurate color based on temperature and atmospheric scattering
    // Most meteors glow in the 1500-3000K range, creating colors from amber to blue-white
    const temperatureColor = new THREE.Color(
      color[0] * brightness * 0.9,
      color[1] * brightness,
      color[2] * brightness * (1 + 0.3 * (brightness - 0.8) / 0.2) // Blue increases with brightness
    );

    return new THREE.ShaderMaterial({
      uniforms: {
        color: { value: temperatureColor },
        time: { value: 0 },
        flicker: { value: flicker },
        flickerOffset: { value: flickerOffset.current }
      },
      vertexShader: `
        uniform vec3 color;
        uniform float time;
        uniform float flicker;
        uniform float flickerOffset;

        attribute float size;
        attribute vec3 colorAttr;
        attribute float offset;

        varying vec3 vColor;
        varying float vAttenuation;

        // Improved noise function for natural flickering
        float noise(float x) {
          return sin(x) * sin(x * 1.5) * sin(x * 4.3 + flickerOffset);
        }

        void main() {
          // Generate unique flicker for each particle based on its position
          float flick = 1.0 + noise(time * 10.0 + position.x * 0.5) * flicker;

          // Apply dynamic color with atmospheric scattering
          vColor = color * colorAttr * flick;

          // Calculate view distance-based attenuation
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          float distance = -mvPosition.z;

          // Atmospheric scattering effect - objects get hazier with distance
          vAttenuation = 1.0 / (1.0 + distance * 0.00008);

          // Dynamic size based on distance and atmospheric perspective
          float dynamicSize = size * (300.0 / distance) * (0.8 + vAttenuation * 0.2);
          gl_PointSize = dynamicSize;

          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform vec3 color;
        uniform float time;

        varying vec3 vColor;
        varying float vAttenuation;

        void main() {
          // Enhanced glow effect with physically accurate falloff
          vec2 coord = gl_PointCoord - vec2(0.5);
          float dist = length(coord);

          // Create atmospheric bloom with physically-based light scattering
          float alpha = 1.0 - smoothstep(0.2, 0.5, dist);

          // Add subtle edge flare for more realistic meteor appearance
          float edgeGlow = 1.0 - smoothstep(0.4, 0.5, dist);
          edgeGlow = pow(edgeGlow, 3.0) * 0.4;

          // Apply atmospheric perspective and scattering
          vec3 finalColor = vColor * (alpha + edgeGlow) * vAttenuation;

          // Modulate alpha by atmospheric attenuation
          float finalAlpha = (alpha * alpha + edgeGlow) * vAttenuation;

          gl_FragColor = vec4(finalColor, finalAlpha);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
  }, [brightness, color, flicker]);

  // Create enhanced geometry with more natural, varied particle distribution
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const positions = [];
    const sizes = [];
    const colors = [];
    const offsets = [];

    // Create more detailed and varied particle trail
    const particleCount = Math.floor(length * 30); // More particles for smoother trail

    // Calculate core and tail colors
    const coreColor = new THREE.Color(1, 1, 1); // Bright white core
    const tailColor = new THREE.Color(color[0] * 0.8, color[1] * 0.9, color[2] * 1.1); // Slightly bluer tail

    for (let i = 0; i < particleCount; i++) {
      // Position particles in a line with some randomness for volume
      const t = i / particleCount;
      const randomOffset = Math.random() * 0.1; // Slight randomness for natural appearance

      // Main particles follow the direction vector
      positions.push(
        -t * length * direction[0] + (Math.random() - 0.5) * randomOffset,
        -t * length * direction[1] + (Math.random() - 0.5) * randomOffset,
        -t * length * direction[2] + (Math.random() - 0.5) * randomOffset
      );

      // Size distribution - larger at head, gradually smaller in tail
      // Non-linear falloff for more realistic appearance
      const sizeFactor = Math.pow(1.0 - t, 2.5); // Sharper falloff
      sizes.push(sizeFactor * (2.5 + Math.random() * 0.5));

      // Color transition from bright core to colored trail
      const colorMix = Math.pow(1.0 - t, 2.0); // Square falloff for sharper transition
      const particleColor = new THREE.Color().copy(coreColor).lerp(tailColor, 1.0 - colorMix);

      // Apply brightness gradient with randomized sparkle effect
      const intensityVariation = 1.0 - t * t; // Quadratic falloff for tail
      const sparkle = Math.random() * 0.3; // Random sparkle effect in tail

      colors.push(
        particleColor.r * intensityVariation * (1 + sparkle),
        particleColor.g * intensityVariation * (1 + sparkle),
        particleColor.b * intensityVariation * (1 + sparkle * 0.8) // Slightly less blue variation
      );

      // Add unique offset for animation timing
      offsets.push(Math.random());
    }

    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geo.setAttribute('size', new THREE.Float32BufferAttribute(sizes, 1));
    geo.setAttribute('colorAttr', new THREE.Float32BufferAttribute(colors, 3));
    geo.setAttribute('offset', new THREE.Float32BufferAttribute(offsets, 1));

    return geo;
  }, [direction, length, color]);

  // Update shooting star with more realistic physics
  useFrame((state, delta) => {
    if (!ref.current) return;

    if (active.current) {
      // Move shooting star in its direction with atmospheric drag simulation
      // Meteors slightly slow down as they enter denser parts of the atmosphere
      const atmosphericDrag = 1.0 - 0.02 * delta; // 2% slowdown per second
      const adjustedSpeed = speed * atmosphericDrag;

      ref.current.position.x += direction[0] * adjustedSpeed * delta;
      ref.current.position.y += direction[1] * adjustedSpeed * delta;
      ref.current.position.z += direction[2] * adjustedSpeed * delta;

      // Update time for animation and apply flickering
      time.current.value += delta;
      material.uniforms.time.value = time.current.value;

      // Check if star has traveled beyond view and needs to be reset
      const distanceTraveled = Math.sqrt(
        Math.pow(ref.current.position.x - startPosition[0], 2) +
        Math.pow(ref.current.position.y - startPosition[1], 2) +
        Math.pow(ref.current.position.z - startPosition[2], 2)
      );

      if (distanceTraveled > 60) { // Increased view distance
        active.current = false;
        ref.current.visible = false;
      }
    } else {
      // Wait before resetting the star
      resetTimer.current -= delta;
      if (resetTimer.current <= 0) {
        // Reset position with slight random variation for unpredictability
        const variation = 5.0; // Range of position variation
        ref.current.position.set(
          startPosition[0] + (Math.random() - 0.5) * variation,
          startPosition[1] + (Math.random() - 0.5) * variation,
          startPosition[2] + (Math.random() - 0.5) * variation
        );
        ref.current.visible = true;
        active.current = true;
        flickerOffset.current = Math.random() * 100; // New random flicker pattern
        material.uniforms.flickerOffset.value = flickerOffset.current;
        resetTimer.current = Math.random() * 15 + 5; // Random delay for next appearance
      }
    }
  });

  return (
    <points ref={ref} position={startPosition} material={material} geometry={geometry} />
  );
};

export default ShootingStar;
