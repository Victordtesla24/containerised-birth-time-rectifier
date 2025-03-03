import React, { useEffect, useState } from 'react';
import { CelestialImage, ParallaxCelestialBackground, useScrollPosition } from './ImageUtils';
import { createParallaxLayers, getRandomImageFromCategory, preloadImages } from '@/utils/imageLoader';

interface CelestialGalleryProps {
  className?: string;
}

/**
 * A showcase component demonstrating various ways to use the celestial images
 */
export const CelestialGallery: React.FC<CelestialGalleryProps> = ({ className = '' }) => {
  const [isLoading, setIsLoading] = useState(true);
  const scrollPosition = useScrollPosition();
  const [paralaxLayers, setParalaxLayers] = useState(createParallaxLayers(3));
  
  // Preload images for better user experience
  useEffect(() => {
    const imagesToPreload = [
      getRandomImageFromCategory('backgrounds-1'),
      getRandomImageFromCategory('backgrounds-2'),
      getRandomImageFromCategory('nebulea'),
    ];
    
    // Preload images and set loading state
    preloadImages(imagesToPreload).then(() => {
      setIsLoading(false);
    });
  }, []);
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center w-full h-40">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  return (
    <div className={`w-full ${className}`}>
      {/* Multi-layer parallax background as page background */}
      <div className="fixed inset-0 -z-10">
        <ParallaxCelestialBackground 
          layers={paralaxLayers}
          scrollPosition={scrollPosition}
          className="h-screen"
        />
      </div>
      
      <div className="container mx-auto px-4 py-8">
        <h2 className="text-2xl font-bold mb-6 text-white">Celestial Gallery</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Individual images with hover effects */}
          <div className="group transition-all duration-300 hover:scale-105">
            <CelestialImage 
              src={getRandomImageFromCategory('backgrounds-1')}
              alt="Space Background"
              className="rounded-lg h-48 shadow-lg"
            />
            <p className="mt-2 text-white opacity-80 group-hover:opacity-100">Space Background</p>
          </div>
          
          <div className="group transition-all duration-300 hover:scale-105">
            <CelestialImage 
              src={getRandomImageFromCategory('nebulea')}
              alt="Nebula"
              className="rounded-lg h-48 shadow-lg"
            />
            <p className="mt-2 text-white opacity-80 group-hover:opacity-100">Nebula</p>
          </div>
          
          <div className="group transition-all duration-300 hover:scale-105">
            <CelestialImage 
              src={getRandomImageFromCategory('backgrounds-2')}
              alt="Galaxy"
              className="rounded-lg h-48 shadow-lg"
            />
            <p className="mt-2 text-white opacity-80 group-hover:opacity-100">Galaxy</p>
          </div>
        </div>
      </div>
    </div>
  );
}; 