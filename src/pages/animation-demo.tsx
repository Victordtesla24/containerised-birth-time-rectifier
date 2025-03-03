import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { CelestialNavbar } from '@/components/common/CelestialNavbar';
import { CelestialDemo } from '@/components/demo/CelestialDemo';
import { AnimatedBackgroundImage, useScrollPosition } from '@/components/common/ImageUtils';
import { getRandomImageFromCategory, preloadImages } from '@/utils/imageLoader';

export default function AnimationDemo() {
  const scrollPosition = useScrollPosition();
  const [isLoading, setIsLoading] = useState(true);
  const [backgroundImage, setBackgroundImage] = useState('');

  // Preload images
  useEffect(() => {
    const randomBackground = getRandomImageFromCategory('backgrounds-1');
    setBackgroundImage(randomBackground);
    
    // Preload images
    preloadImages([randomBackground]).then(() => {
      setIsLoading(false);
    });
  }, []);

  if (isLoading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-black">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Celestial Animations | Birth Time Rectifier</title>
        <meta name="description" content="Showcase of celestial animations and effects" />
      </Head>
      
      {/* Background image */}
      <AnimatedBackgroundImage
        src={backgroundImage}
        overlayOpacity={0.8}
        overlayColor="#000830"
        parallaxEffect={true}
        scrollPosition={scrollPosition}
        className="fixed inset-0 -z-10"
      />
      
      {/* Navbar */}
      <CelestialNavbar />
      
      <main className="min-h-screen py-12 pt-28">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-white mb-4">Celestial Animation Gallery</h1>
            <p className="text-blue-200 max-w-2xl mx-auto">
              Explore our collection of animated celestial bodies with consistent space backgrounds
            </p>
          </div>
          
          {/* Demo Component */}
          <CelestialDemo />
          
          {/* Implementation Details */}
          <div className="max-w-3xl mx-auto mt-16 bg-gradient-to-br from-slate-900/90 to-blue-900/20 backdrop-blur-sm 
            rounded-xl p-6 border border-blue-800/30">
            <h2 className="text-2xl font-bold text-white mb-4">Implementation Details</h2>
            <p className="text-blue-200 mb-4">
              These animations are implemented using a minimal approach with:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-blue-200">
              <li>Framer Motion for animations (already in the project dependencies)</li>
              <li>CSS gradients for consistent backgrounds</li>
              <li>CSS filters for glow effects</li>
              <li>Mix-blend-mode for seamless image integration</li>
            </ul>
            <p className="text-blue-200 mt-4">
              No additional libraries were needed, keeping the implementation lightweight and efficient.
            </p>
          </div>
        </div>
      </main>
    </>
  );
} 