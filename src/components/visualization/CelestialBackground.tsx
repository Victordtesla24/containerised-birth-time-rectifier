import React, { useEffect, useRef, useState, useMemo } from 'react';

// Detect device capabilities for performance optimization
const detectDeviceCapabilities = () => {
  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
  const hasReducedMotion = typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

  // Detect WebGL support
  let hasWebGL = false;
  try {
    const canvas = document.createElement('canvas');
    hasWebGL = !!(window.WebGLRenderingContext &&
      (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
  } catch(e) {
    hasWebGL = false;
  }

  return {
    isMobile,
    hasReducedMotion,
    hasWebGL,
    // Set quality based on device capability
    qualityLevel: isMobile ? 'low' : (hasWebGL ? 'high' : 'medium')
  };
};

interface Star {
  x: number;
  y: number;
  radius: number;
  opacity: number;
  speed?: number;
  initialOpacity?: number;
}

export const CelestialBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [renderFallback, setRenderFallback] = useState(false);
  const animationRef = useRef<number>();
  const starsRef = useRef<Star[]>([]);
  const fpsRef = useRef<number>(0);
  const lastFrameTimeRef = useRef<number>(0);
  const frameCountRef = useRef<number>(0);
  const lastFpsUpdateRef = useRef<number>(0);

  // Use useMemo to avoid recalculating device capabilities on every render
  const deviceCapabilities = useMemo(() => detectDeviceCapabilities(), []);

  const starCount = deviceCapabilities.qualityLevel === 'low' ? 100 :
                   deviceCapabilities.qualityLevel === 'medium' ? 200 : 300;

  // Progressive loading to improve initial render performance
  useEffect(() => {
    // Set loaded after a short delay to show progressive loading
    const timer = setTimeout(() => {
      setIsLoaded(true);
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let ctx: CanvasRenderingContext2D | null = null;

    try {
      ctx = canvas.getContext('2d', { alpha: false });
      if (!ctx) throw new Error('Failed to get 2D context');

      // Optimize canvas rendering
      if (deviceCapabilities.qualityLevel !== 'high') {
        // Lower resolution for better performance on slower devices
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.width = window.innerWidth * 0.75;
        canvas.height = window.innerHeight * 0.75;
      } else {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
      }
    } catch (error) {
      console.error('Error initializing canvas:', error);
      setRenderFallback(true);
      return;
    }

    // Create star field with optimized count based on device capability
    const createStars = (count: number): Star[] => {
      const stars = [];
      for (let i = 0; i < count; i++) {
        const x = Math.random() * canvas.width;
        const y = Math.random() * canvas.height;
        // Vary star sizes less on lower-end devices
        const radius = deviceCapabilities.qualityLevel === 'low'
          ? 0.5 + Math.random() * 0.5
          : Math.random() * 1.5;
        const opacity = 0.1 + Math.random() * 0.9;
        const speed = deviceCapabilities.qualityLevel === 'high'
          ? 0.05 + Math.random() * 0.1
          : 0;
        stars.push({
          x,
          y,
          radius,
          opacity,
          speed,
          initialOpacity: opacity
        });
      }
      return stars;
    };

    // Initialize stars
    starsRef.current = createStars(starCount);

    // Animation with frame rate throttling
    const animate = (timestamp: number) => {
      if (!ctx) return;

      // Calculate FPS
      if (lastFrameTimeRef.current) {
        const delta = timestamp - lastFrameTimeRef.current;
        frameCountRef.current++;

        // Update FPS counter once per second
        if (timestamp - lastFpsUpdateRef.current > 1000) {
          fpsRef.current = Math.round(frameCountRef.current * 1000 / (timestamp - lastFpsUpdateRef.current));
          frameCountRef.current = 0;
          lastFpsUpdateRef.current = timestamp;
        }

        // Skip frames if the FPS is too high (for power saving)
        if (fpsRef.current > 40 && deviceCapabilities.qualityLevel !== 'high') {
          if (frameCountRef.current % 2 !== 0) {
            animationRef.current = requestAnimationFrame(animate);
            return;
          }
        }
      }

      lastFrameTimeRef.current = timestamp;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw gradient background with fallback solid color
      try {
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        gradient.addColorStop(0, '#0f172a');
        gradient.addColorStop(1, '#1e3a8a');
        ctx.fillStyle = gradient;
      } catch (error) {
        ctx.fillStyle = '#0f172a';
        console.warn('Gradient failed, using solid color fallback');
      }

      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw stars with animation based on quality level
      starsRef.current.forEach(star => {
        if (deviceCapabilities.qualityLevel === 'high' && star.speed) {
          // Animate star opacity for twinkling effect on high-quality mode
          star.opacity = star.initialOpacity! * (0.5 + Math.sin(timestamp * 0.001 * star.speed) * 0.5);
        }

        try {
          ctx!.beginPath();
          ctx!.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
          ctx!.fillStyle = `rgba(255, 255, 255, ${star.opacity})`;
          ctx!.fill();
        } catch (error) {
          // Fallback to simple rectangle if arc fails
          ctx!.fillStyle = `rgba(255, 255, 255, ${star.opacity})`;
          ctx!.fillRect(star.x, star.y, 1, 1);
        }
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    // Start animation
    animationRef.current = requestAnimationFrame(animate);

    // Handle resize with debounce for performance
    let resizeTimeout: NodeJS.Timeout;
    const handleResize = () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        if (deviceCapabilities.qualityLevel !== 'high') {
          canvas.width = window.innerWidth * 0.75;
          canvas.height = window.innerHeight * 0.75;
        } else {
          canvas.width = window.innerWidth;
          canvas.height = window.innerHeight;
        }

        // Recalculate star positions
        starsRef.current = createStars(starCount);
      }, 200);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      clearTimeout(resizeTimeout);
    };
  }, [deviceCapabilities.qualityLevel, starCount]);

  // Fallback renderer in case of canvas errors
  if (renderFallback) {
    return (
      <div
        className="fixed top-0 left-0 w-full h-full -z-10 bg-gradient-to-b from-blue-900 to-indigo-900"
      ></div>
    );
  }

  return (
    <>
      {!isLoaded && (
        <div className="fixed top-0 left-0 w-full h-full -z-10 bg-blue-900"></div>
      )}
      <canvas
        ref={canvasRef}
        className={`fixed top-0 left-0 w-full h-full -z-10 ${isLoaded ? 'opacity-100' : 'opacity-0'} transition-opacity duration-1000`}
        aria-hidden="true"
      />
    </>
  );
};
