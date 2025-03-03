import React, { useState } from 'react';
import Image from 'next/image';
import { motion } from 'framer-motion';

// Types for our image components
interface CelestialImageProps {
  src: string;
  alt: string;
  className?: string;
  width?: number;
  height?: number;
  priority?: boolean;
  quality?: number;
  onClick?: () => void;
  fallbackColor?: string;
}

interface BackgroundImageProps {
  src: string;
  alt?: string;
  overlayOpacity?: number;
  overlayColor?: string;
  parallaxEffect?: boolean;
  scrollPosition?: number;
  children?: React.ReactNode;
  className?: string;
  fallbackColor?: string;
}

/**
 * A wrapper around Next.js Image component optimized for celestial images
 * with fallback handling for better browser compatibility
 */
export const CelestialImage: React.FC<CelestialImageProps> = ({
  src,
  alt,
  className = '',
  width = 0,
  height = 0,
  priority = false,
  quality = 85,
  onClick,
  fallbackColor = '#1a1a2e'
}) => {
  const [imageError, setImageError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Improved path resolution - better handling of different image paths
  // Ensure we don't double-prepend `/images/` for paths that already have it
  let imageSrc = src;
  if (!src.startsWith('/') && !src.startsWith('http')) {
    imageSrc = `/images/${src}`;
  }

  // Log image paths in development for debugging
  if (process.env.NODE_ENV === 'development') {
    console.debug(`Loading image: ${imageSrc} (original: ${src})`);
  }

  // Handle image error
  const handleError = () => {
    console.warn(`Failed to load image: ${imageSrc}`);
    setImageError(true);
  };

  // Handle image load
  const handleLoad = () => {
    setIsLoading(false);
  };

  return (
    <div 
      className={`relative overflow-hidden ${className}`} 
      onClick={onClick}
      style={{ backgroundColor: fallbackColor }}
    >
      {/* Fallback colored div if image fails to load */}
      {imageError && (
        <div 
          className="absolute inset-0 celestial-image-fallback" 
          style={{ 
            backgroundColor: fallbackColor,
            opacity: 0.8
          }}
        />
      )}

      {/* Show loading state */}
      {isLoading && !imageError && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 z-10">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      )}

      {/* Only render Image if no error */}
      {!imageError && (
        <Image
          src={imageSrc}
          alt={alt}
          width={width || undefined}
          height={height || undefined}
          quality={quality}
          priority={priority}
          className="object-cover w-full h-full"
          onError={handleError}
          onLoad={handleLoad}
          // Using fill for images without specified dimensions
          {...(!width && !height ? { fill: true } : {})}
        />
      )}
    </div>
  );
};

/**
 * Component for creating full-screen or container background images
 * with optional overlay and parallax effects
 */
export const BackgroundImage: React.FC<BackgroundImageProps> = ({
  src,
  alt = 'Background image',
  overlayOpacity = 0,
  overlayColor = 'black',
  parallaxEffect = false,
  scrollPosition = 0,
  children,
  className = '',
  fallbackColor = '#1a1a2e'
}) => {
  // Calculate transform for parallax effect
  const transform = parallaxEffect
    ? { transform: `translateY(${scrollPosition * 0.2}px)` }
    : {};

  // Ensure src begins with the correct path
  const imageSrc = src.startsWith('/') || src.startsWith('http')
    ? src
    : `/images/${src}`;

  return (
    <div 
      className={`relative ${className}`}
      style={{ overflow: 'hidden', backgroundColor: fallbackColor }}
    >
      {/* Background image with z-index to ensure it's below content but above other backgrounds */}
      <div
        className="absolute inset-0 w-full h-full bg-cover bg-center"
        style={{
          backgroundImage: `url(${imageSrc})`,
          ...transform,
          zIndex: -1,
        }}
      />
      
      {/* Optional overlay */}
      {overlayOpacity > 0 && (
        <div 
          className="absolute inset-0 w-full h-full"
          style={{ 
            backgroundColor: overlayColor,
            opacity: overlayOpacity,
            zIndex: 0,
          }}
        />
      )}
      
      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};

/**
 * Animated background image with parallax and motion effects
 */
export const AnimatedBackgroundImage: React.FC<BackgroundImageProps> = (props) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1 }}
      className="relative w-full h-full"
    >
      <BackgroundImage {...props} />
    </motion.div>
  );
};

/**
 * Multi-layer parallax background with depth effect
 */
export const ParallaxCelestialBackground: React.FC<{
  layers: { src: string; depth: number; opacity?: number }[];
  scrollPosition?: number;
  className?: string;
  children?: React.ReactNode;
}> = ({ layers, scrollPosition = 0, className = '', children }) => {
  return (
    <div className={`relative ${className}`}>
      {layers.map((layer, index) => {
        // Ensure src begins with the correct path
        const imageSrc = layer.src.startsWith('/') || layer.src.startsWith('http') 
          ? layer.src 
          : `/images/${layer.src}`;
        
        return (
          <div
            key={index}
            className="absolute inset-0 w-full h-full bg-cover bg-center"
            style={{
              backgroundImage: `url(${imageSrc})`,
              transform: `translateY(${scrollPosition * (0.1 + layer.depth * 0.01)}px)`,
              opacity: layer.opacity || 1,
              zIndex: -10 + index
            }}
          />
        );
      })}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};

// Helper hook for parallax effect
export const useScrollPosition = () => {
  const [scrollPosition, setScrollPosition] = React.useState(0);
  
  React.useEffect(() => {
    const handleScroll = () => {
      setScrollPosition(window.scrollY);
    };
    
    window.addEventListener('scroll', handleScroll);
    
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);
  
  return scrollPosition;
}; 