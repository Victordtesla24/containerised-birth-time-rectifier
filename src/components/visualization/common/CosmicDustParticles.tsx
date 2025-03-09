import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

interface CosmicDustParticlesProps {
  count?: number;
  color?: string;
  depth?: boolean;
  size?: 'small' | 'medium' | 'large';
  speed?: 'slow' | 'medium' | 'fast';
  mouseReactive?: boolean;
}

const CosmicDustParticles: React.FC<CosmicDustParticlesProps> = ({
  count = 50,
  color = '#FFFFFF',
  depth = true,
  size = 'medium',
  speed = 'medium',
  mouseReactive = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const particles = Array.from({ length: count }).map((_, i) => ({
    id: i,
    x: Math.random() * 100, // % position
    y: Math.random() * 100, // % position
    size: size === 'small'
      ? Math.random() * 1.5 + 0.5
      : size === 'medium'
        ? Math.random() * 2 + 1
        : Math.random() * 3 + 2,
    opacity: Math.random() * 0.5 + 0.2,
    depth: depth ? Math.random() * 100 - 50 : 0, // z-index variation for 3D effect
    animationDuration: speed === 'slow'
      ? Math.random() * 20 + 20
      : speed === 'medium'
        ? Math.random() * 15 + 10
        : Math.random() * 10 + 5,
    delay: Math.random() * 5,
    colorVariation: Math.random() * 20 - 10, // slight color variation
  }));

  // Track mouse position for reactive particles
  useEffect(() => {
    if (!mouseReactive || !containerRef.current) return;

    const container = containerRef.current;
    const particleElements = container.querySelectorAll('.cosmic-dust-particle');

    const handleMouseMove = (e: MouseEvent) => {
      const { left, top, width, height } = container.getBoundingClientRect();
      const mouseX = ((e.clientX - left) / width - 0.5) * 2; // -1 to 1
      const mouseY = ((e.clientY - top) / height - 0.5) * 2; // -1 to 1

      particleElements.forEach((particle, index) => {
        const particleDepth = particles[index].depth;
        const depthFactor = depth ? Math.abs(particleDepth) / 50 : 1;
        const particleEl = particle as HTMLElement;

        // Apply parallax effect based on depth
        const moveX = mouseX * 15 * depthFactor;
        const moveY = mouseY * 15 * depthFactor;

        particleEl.style.transform = `translate3d(${moveX}px, ${moveY}px, ${particleDepth}px)`;
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mouseReactive, particles, depth]);

  return (
    <div
      ref={containerRef}
      className="cosmic-dust-container absolute inset-0 z-0 pointer-events-none overflow-hidden"
      style={{
        perspective: '1000px',
        transformStyle: 'preserve-3d',
      }}
    >
      {particles.map((particle) => {
        // Create a slightly varied color based on the base color
        let particleColor = color;
        if (color.startsWith('#')) {
          // Simple color variation for hex colors
          particleColor = color === '#FFFFFF'
            ? `rgba(255, 255, 255, ${particle.opacity})`
            : `rgba(${parseInt(color.slice(1, 3), 16) + particle.colorVariation},
                   ${parseInt(color.slice(3, 5), 16) + particle.colorVariation},
                   ${parseInt(color.slice(5, 7), 16) + particle.colorVariation},
                   ${particle.opacity})`;
        }

        return (
          <motion.div
            key={particle.id}
            className="cosmic-dust-particle absolute rounded-full"
            style={{
              left: `${particle.x}%`,
              top: `${particle.y}%`,
              width: `${particle.size}px`,
              height: `${particle.size}px`,
              backgroundColor: particleColor,
              boxShadow: `0 0 ${particle.size}px ${particleColor}`,
              transform: `translateZ(${particle.depth}px)`,
              willChange: 'transform, opacity',
            }}
            animate={{
              x: [0, Math.random() * 30 - 15, 0],
              y: [0, Math.random() * 30 - 15, 0],
              opacity: [particle.opacity, particle.opacity * 1.5, particle.opacity],
              scale: [1, Math.random() * 0.3 + 0.9, 1],
            }}
            transition={{
              duration: particle.animationDuration,
              repeat: Infinity,
              repeatType: "reverse",
              ease: "easeInOut",
              delay: particle.delay,
            }}
          />
        );
      })}
    </div>
  );
};

export default CosmicDustParticles;
