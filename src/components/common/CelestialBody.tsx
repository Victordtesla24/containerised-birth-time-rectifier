import React from 'react';
import { motion } from 'framer-motion';
import { CelestialImage } from './ImageUtils';

interface CelestialBodyProps {
  src: string;
  alt: string;
  className?: string;
  type?: 'sun' | 'planet' | 'moon' | 'star' | 'nebula';
  rotate?: boolean;
  rotationDuration?: number;
  glow?: boolean;
  glowColor?: string;
  glowIntensity?: 'low' | 'medium' | 'high';
  pulseEffect?: boolean;
  onClick?: () => void;
  fallbackColor?: string;
  children?: React.ReactNode;
}

/**
 * Enhanced celestial body component with consistent backgrounds and animations
 * with improved browser compatibility
 */
export const CelestialBody: React.FC<CelestialBodyProps> = ({
  src,
  alt,
  className = '',
  type = 'planet',
  rotate = false,
  rotationDuration = 60,
  glow = false,
  glowColor,
  glowIntensity = 'medium',
  pulseEffect = false,
  onClick,
  fallbackColor,
  children,
}) => {
  // Set default glow color based on type if not provided
  const defaultGlowColors = {
    sun: 'rgba(255, 160, 60, 0.8)',
    planet: 'rgba(100, 200, 255, 0.6)',
    moon: 'rgba(220, 220, 240, 0.5)',
    star: 'rgba(200, 220, 255, 0.7)',
    nebula: 'rgba(180, 120, 255, 0.6)',
  };

  const effectiveGlowColor = glowColor || defaultGlowColors[type];
  
  // Set glow intensity
  const glowIntensityValues = {
    low: { 
      dropShadow: '0 0 4px',
      boxShadow: '0 0 15px 2px'
    },
    medium: { 
      dropShadow: '0 0 8px',
      boxShadow: '0 0 25px 4px'
    },
    high: { 
      dropShadow: '0 0 15px',
      boxShadow: '0 0 40px 8px'
    },
  };

  // Create glow effect that's more cross-browser compatible
  const glowStyle = glow ? {
    boxShadow: `${glowIntensityValues[glowIntensity].boxShadow} ${effectiveGlowColor}`,
  } : {};

  // Animation variants
  const rotationAnimation = rotate ? {
    animate: { 
      rotate: 360,
      transition: { 
        duration: rotationDuration, 
        repeat: Infinity, 
        ease: "linear" 
      }
    }
  } : {};

  const pulseAnimation = pulseEffect ? {
    animate: { 
      scale: [1, 1.05, 1],
      transition: { 
        duration: 3, 
        repeat: Infinity, 
        ease: "easeInOut" 
      }
    }
  } : {};

  // Generate a fallback background color based on type
  const getFallbackColor = () => {
    if (fallbackColor) return fallbackColor;
    
    switch(type) {
      case 'sun': return '#FF9D00';
      case 'moon': return '#E1E1E8';
      case 'planet': return '#4B7AC7';
      case 'star': return '#FFFFFF';
      case 'nebula': return '#8A4FFF';
      default: return '#4B7AC7';
    }
  };

  // Ensure image source begins with proper path
  const ensureImagePath = (src: string) => {
    // If src is already an absolute path or URL, return as is
    if (src.startsWith('/') || src.startsWith('http')) {
      return src;
    }
    // Otherwise, add /images/ prefix
    return `/images/${src}`;
  };

  return (
    <motion.div
      className={`relative overflow-hidden rounded-full ${className}`}
      style={{
        ...glowStyle,
        background: type === 'sun' ? 
          "radial-gradient(circle at center, rgba(255,180,0,0.2) 60%, rgba(20,0,0,0.6) 100%)" : 
          type === 'moon' ?
          "radial-gradient(circle at center, rgba(220,220,240,0.2) 70%, rgba(0,20,60,0.8) 100%)" :
          "radial-gradient(circle at center, rgba(0,0,0,0) 70%, rgba(0,20,60,0.8) 100%)"
      }}
      {...rotationAnimation}
      {...pulseAnimation}
      onClick={onClick}
    >
      <div className="celestial-image-container relative w-full h-full">
        {/* Base colored background that matches the planet type */}
        <div className="absolute inset-0" style={{ backgroundColor: getFallbackColor(), opacity: 0.6 }} />
        
        {/* Actual planet image */}
        <CelestialImage
          src={ensureImagePath(src)}
          alt={alt}
          className={`w-full h-full ${type === 'sun' ? 'celestial-sun' : type === 'moon' ? 'celestial-moon' : ''}`}
          fallbackColor={getFallbackColor()}
        />
        
        {/* Subtle overlay for better blending with background */}
        <div 
          className="absolute inset-0 pointer-events-none"
          style={{ 
            background: type === 'sun' 
              ? "radial-gradient(circle at center, rgba(255,120,0,0.2) 0%, rgba(0,0,0,0) 70%)" 
              : type === 'moon'
              ? "radial-gradient(circle at center, rgba(220,220,240,0.2) 0%, rgba(0,0,0,0) 70%)"
              : "radial-gradient(circle at center, rgba(100,150,255,0.1) 0%, rgba(0,0,0,0) 70%)" 
          }}
        />
        
        {/* Optional content (like planet letter) */}
        {children && (
          <div className="absolute inset-0 flex items-center justify-center text-white font-bold text-xl">
            {children}
          </div>
        )}
      </div>
    </motion.div>
  );
}; 