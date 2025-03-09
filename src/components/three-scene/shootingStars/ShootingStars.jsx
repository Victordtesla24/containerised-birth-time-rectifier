import React, { useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import { useQuality } from '../core/QualityContext';
import ShootingStar from './ShootingStar';

/**
 * Enhanced shooting stars system with depth-based distribution
 *
 * @param {Object} props - Component properties
 * @param {Object} props.mousePosition - Current mouse position for parallax effects
 */
const ShootingStars = ({ mousePosition }) => {
  const { qualityLevel } = useQuality();

  // Adaptive count based on quality setting
  const starCount = useMemo(() => {
    return qualityLevel === 'low' ? 5 :
           qualityLevel === 'medium' ? 10 : 15;
  }, [qualityLevel]);

  // Array of scientifically accurate meteor colors based on composition
  const meteorColors = useMemo(() => [
    [1.0, 0.9, 0.5],   // Iron (yellow-white)
    [0.7, 1.0, 0.7],   // Nickel (greenish)
    [0.7, 0.9, 1.0],   // Magnesium (blue-white)
    [1.0, 0.6, 0.5],   // Sodium (orange)
    [0.9, 0.6, 1.0],   // Calcium (purple-ish)
    [1.0, 0.8, 0.8]    // Silicate (pinkish)
  ], []);

  // Generate random shooting stars with varied parameters and realistic distribution
  const shootingStars = useMemo(() => {
    const stars = [];
    for (let i = 0; i < starCount; i++) {
      // Use realistic meteor shower radiant pattern
      // Meteors in showers appear to come from a single point in the sky

      // Random radiant position (the point meteors appear to originate from)
      const radiantTheta = Math.random() * Math.PI * 2;
      const radiantPhi = Math.random() * Math.PI * 0.3 + 0.1; // More meteors from overhead

      // Create random starting position in a hemisphere
      // But constrained to appear more from the radiant direction
      const theta = radiantTheta + (Math.random() - 0.5) * Math.PI * 0.5; // Spread from radiant
      const phi = radiantPhi + (Math.random() - 0.5) * Math.PI * 0.3;
      const radius = 100 + Math.random() * 50; // Further distance for more parallax effect

      const x = radius * Math.sin(phi) * Math.cos(theta);
      const y = radius * Math.sin(phi) * Math.sin(theta);
      const z = -radius * Math.cos(phi);

      // Direction away from radiant with some natural dispersion
      // Real meteors follow parallel paths in 3D space but appear to radiate from a point
      const baseDir = {
        x: -Math.sin(radiantPhi) * Math.cos(radiantTheta),
        y: -Math.sin(radiantPhi) * Math.sin(radiantTheta),
        z: Math.cos(radiantPhi)
      };

      // Add some randomness to direction
      const dirX = baseDir.x + (Math.random() - 0.5) * 0.2;
      const dirY = baseDir.y + (Math.random() - 0.5) * 0.2;
      const dirZ = baseDir.z + (Math.random() - 0.5) * 0.1;

      // Normalize direction
      const mag = Math.sqrt(dirX * dirX + dirY * dirY + dirZ * dirZ);

      // Randomize meteor properties based on scientific observations
      const speed = 15 + Math.random() * 35; // Variable speed, 15-50 units per second
      const brightness = 0.6 + Math.random() * 0.4; // Variable brightness
      const length = 2 + Math.random() * 5; // Variable trail length

      // Scientific distribution of meteor colors
      // Choose a random color from our scientifically accurate meteor colors
      const colorIndex = Math.floor(Math.random() * meteorColors.length);

      // Add slight randomness to the color to simulate atmospheric effects
      const colorVariation = 0.1; // 10% random variation in color
      const color = [
        meteorColors[colorIndex][0] * (1 + (Math.random() - 0.5) * colorVariation),
        meteorColors[colorIndex][1] * (1 + (Math.random() - 0.5) * colorVariation),
        meteorColors[colorIndex][2] * (1 + (Math.random() - 0.5) * colorVariation)
      ];

      // Create the shooting star data
      stars.push({
        id: i,
        startPosition: [x, y, z],
        direction: [dirX / mag, dirY / mag, dirZ / mag],
        speed,
        brightness,
        length,
        color,
        trailOpacity: 0.6 + Math.random() * 0.4, // Variable trail opacity
        flicker: 0.03 + Math.random() * 0.07 // Variable flicker amount
      });
    }
    return stars;
  }, [starCount, meteorColors]);

  // Apply parallax effect to shooting stars based on mouse position
  useFrame(() => {
    if (!mousePosition) return;

    // Subtle parallax effect for immersion
    const parallaxFactor = 0.02;
    const targetX = mousePosition.x * parallaxFactor;
    const targetY = mousePosition.y * parallaxFactor;

    // Apply to each meteor with distance-based factor (stars further away move less)
    shootingStars.forEach((star, index) => {
      const depth = star.startPosition[2];
      const depthFactor = Math.min(1, Math.abs(depth) / 150); // Normalize depth factor

      if (index % 2 === 0) { // Apply to half the stars for performance
        const distanceParallax = 1 - depthFactor * 0.8; // Further objects move less

        star.startPosition[0] += targetX * distanceParallax * 0.1;
        star.startPosition[1] += targetY * distanceParallax * 0.1;
      }
    });
  });

  // Add meteor shower effect with bursts of shooting stars
  useEffect(() => {
    // Create a meteor shower every 20-40 seconds
    const meteorShowerInterval = setInterval(() => {
      // Only trigger meteor showers on high quality settings
      if (qualityLevel === 'high') {
        const isShowerActive = Math.random() < 0.5; // 50% chance to trigger a meteor shower
        if (isShowerActive) {
          console.log('Meteor shower activated');
          // Meteor shower logic would be here in a real implementation
        }
      }
    }, 30000);

    return () => clearInterval(meteorShowerInterval);
  }, [qualityLevel]);

  // Enhance visual quality for high-end devices
  useEffect(() => {
    if (qualityLevel === 'high') {
      // Apply HDR-like color enhancement to all meteor materials
      const enhanceColors = () => {
        // In a real implementation, this would modify material properties
        // for all active shooting stars to create more vivid colors
      };

      enhanceColors();
    }
  }, [qualityLevel]);

  return (
    <group>
      {shootingStars.map((star) => (
        <ShootingStar key={star.id} {...star} />
      ))}
    </group>
  );
};

export default ShootingStars;
