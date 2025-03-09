import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';

interface NavItem {
  name: string;
  href: string;
  label: string;
  icon?: string;
}

export const CelestialNavbar: React.FC = () => {
  const router = useRouter();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [hoverItem, setHoverItem] = useState<string | null>(null);
  const orbitRef = useRef<HTMLDivElement>(null);

  // Navigation items with optional icons
  const navItems: NavItem[] = [
    { name: 'home', href: '/', label: 'Home', icon: '🏠' },
    { name: 'analysis', href: '/birth-time-analysis', label: 'Start Analysis', icon: '🔍' },
    { name: 'about', href: '/about', label: 'About', icon: 'ℹ️' },
    { name: 'faq', href: '/faq', label: 'FAQ', icon: '❓' },
  ];

  // Handle scroll effect
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 10) {
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Animation for the orbiting planet in the logo
  useEffect(() => {
    if (!orbitRef.current) return;

    let angle = 0;
    let animationFrameId: number;

    const animate = () => {
      if (!orbitRef.current) return;

      angle += 0.02;
      const x = Math.cos(angle) * 15; // Orbit radius
      const y = Math.sin(angle) * 15;

      orbitRef.current.style.transform = `translate(${x}px, ${y}px)`;
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();
    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  // Track mouse position for parallax effect
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const navRef = useRef<HTMLDivElement>(null);

  // Handle mouse movement for 3D effects
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (navRef.current) {
      const rect = navRef.current.getBoundingClientRect();

      // Calculate mouse position relative to nav center (values from -1 to 1)
      const x = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      const y = ((e.clientY - rect.top) / rect.height - 0.5) * 2;

      setMousePosition({ x, y });
    }
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [handleMouseMove]);

  return (
    <motion.nav
      ref={navRef}
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={`fixed top-0 left-0 right-0 z-50 ${isScrolled ? 'py-2' : 'py-4'} transition-all duration-300 parallax-container`}
      style={{
        backdropFilter: 'blur(10px)',
        backgroundColor: isScrolled ? 'rgba(15, 23, 42, 0.85)' : 'rgba(15, 23, 42, 0.7)',
        boxShadow: isScrolled
          ? '0 4px 20px -1px rgba(0, 0, 0, 0.3), 0 0 15px rgba(59, 130, 246, 0.2)'
          : 'none',
        perspective: '1000px',
        transformStyle: 'preserve-3d'
      }}
    >
      <div className="max-w-7xl mx-auto px-4 flex items-center justify-between">
        {/* Enhanced Logo with animated orbiting element */}
        <Link href="/">
          <div className="flex items-center cursor-pointer group">
            <div className="w-10 h-10 mr-2 relative flex items-center justify-center overflow-visible">
              {/* Main planet */}
              <motion.div
                whileHover={{ scale: 1.1 }}
                className="w-7 h-7 rounded-full z-10 flex items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, #3B82F6, #1E40AF)',
                  boxShadow: '0 0 10px rgba(59, 130, 246, 0.7), inset 0 -2px 5px rgba(0, 0, 0, 0.4)'
                }}
              >
                {/* Planet surface details */}
                <div className="absolute w-full h-full opacity-20">
                  <div className="absolute w-2 h-1 bg-white rounded-full top-1 left-2 rotate-12"></div>
                  <div className="absolute w-1 h-1 bg-white rounded-full top-3 left-1"></div>
                  <div className="absolute w-1.5 h-1 bg-white rounded-full bottom-1 right-2"></div>
                </div>
              </motion.div>

              {/* Orbiting small planet */}
              <div
                ref={orbitRef}
                className="absolute w-2.5 h-2.5 rounded-full z-20"
                style={{
                  background: 'linear-gradient(135deg, #60A5FA, #93C5FD)',
                  boxShadow: '0 0 8px rgba(96, 165, 250, 0.7)'
                }}
              ></div>

              {/* Orbit ring */}
              <div className="absolute w-[40px] h-[40px] rounded-full border border-blue-300/30 z-0"></div>

              {/* Star particles */}
              <div className="absolute w-1 h-1 bg-white rounded-full top-0 right-0 animate-pulse"></div>
              <div className="absolute w-0.5 h-0.5 bg-white rounded-full bottom-1 left-0"></div>
              <div className="absolute w-0.5 h-0.5 bg-white rounded-full top-2 left-1"></div>

              {/* Logo glow effect on hover */}
              <motion.div
                className="absolute inset-0 rounded-full opacity-0 group-hover:opacity-100 z-0"
                initial={{ opacity: 0 }}
                whileHover={{ opacity: 1 }}
                style={{
                  background: 'radial-gradient(circle, rgba(59,130,246,0.4) 0%, rgba(59,130,246,0) 70%)',
                  filter: 'blur(5px)',
                  transform: 'scale(1.5)'
                }}
                transition={{ duration: 0.3 }}
              ></motion.div>
            </div>

            {/* Title with animated gradient */}
            <div className="flex flex-col">
              <motion.span
                className="text-xl font-bold text-white"
                style={{
                  textShadow: '0 2px 4px rgba(0,0,0,0.3), 0 0 10px rgba(59, 130, 246, 0.3)',
                  backgroundImage: 'linear-gradient(90deg, #FFFFFF, #93C5FD, #FFFFFF)',
                  backgroundSize: '200% auto',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  animation: 'gradientShift 5s ease infinite'
                }}
              >
                Birth Time Rectification
              </motion.span>
              <span className="text-xs text-blue-300 tracking-wide opacity-80">Cosmic Pattern Analysis</span>
            </div>

            {/* CSS animations are defined in a global stylesheet */}
          </div>
        </Link>

        {/* Desktop Navigation with true 3D hover effects */}
        <div className="hidden md:flex items-center gap-6 cosmic-menu">
          {navItems.map((item) => (
            <Link
              key={item.name}
              href={item.href}
            >
              <motion.div
                className={`cosmic-menu-item relative px-3 py-2 rounded-md text-sm font-medium flex items-center overflow-hidden ${router.pathname === item.href ? 'active' : ''}`}
                style={{
                  color: router.pathname === item.href ? '#93C5FD' : '#E5E7EB',
                  backgroundColor: router.pathname === item.href ? 'rgba(59, 130, 246, 0.1)' : 'transparent'
                }}
                onHoverStart={() => setHoverItem(item.name)}
                onHoverEnd={() => setHoverItem(null)}
                whileHover={{
                  scale: 1.05,
                  y: -2,
                  z: 20,
                  rotateX: mousePosition.y * -2,
                  rotateY: mousePosition.x * 5,
                  transition: { duration: 0.2 }
                }}
              >
                {/* Advanced 3D glow effect on hover */}
                <AnimatePresence>
                  {hoverItem === item.name && (
                    <motion.div
                      className="absolute inset-0 rounded-md -z-10"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      style={{
                        background: 'radial-gradient(circle, rgba(59,130,246,0.15) 0%, rgba(59,130,246,0) 70%)',
                        boxShadow: 'inset 0 0 10px rgba(59,130,246,0.1), 0 0 15px rgba(59,130,246,0.1)',
                        transform: 'translateZ(-5px)'
                      }}
                    />
                  )}
                </AnimatePresence>

                {/* Icon with pop effect on hover */}
                {item.icon && (
                  <motion.span
                    className="mr-1.5 text-xs"
                    animate={hoverItem === item.name ? { scale: 1.2, rotate: [0, 5, 0, -5, 0] } : {}}
                    transition={{ duration: 0.5 }}
                  >
                    {item.icon}
                  </motion.span>
                )}

                {item.label}

                {/* Enhanced animated indicator for current page */}
                {router.pathname === item.href && (
                  <motion.div
                    className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full"
                    style={{
                      background: 'linear-gradient(90deg, transparent, #60A5FA, #93C5FD, #60A5FA, transparent)',
                      boxShadow: '0 0 8px rgba(59, 130, 246, 0.5)'
                    }}
                    layoutId="navIndicator"
                    initial={{ width: '0%', left: '50%' }}
                    animate={{ width: '100%', left: '0%' }}
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  />
                )}
              </motion.div>
            </Link>
          ))}

          {/* True 3D Sign In button with enhanced cosmic effects */}
          <motion.button
            className="cosmic-btn relative px-5 py-2 rounded-full"
            whileHover={{
              scale: 1.05,
              y: -2,
              z: 20,
              rotateX: mousePosition.y * -5,
              rotateY: mousePosition.x * 10
            }}
            whileTap={{ scale: 0.98, y: -1 }}
          >
            {/* Enhanced sparkle effects */}
            <div className="absolute h-1 w-1 rounded-full bg-white top-1 right-3 opacity-70" style={{ animation: 'twinkle 3s infinite both' }}></div>
            <div className="absolute h-0.5 w-0.5 rounded-full bg-white bottom-1 left-5 opacity-60" style={{ animation: 'twinkle 4s infinite both', animationDelay: '0.5s' }}></div>

            <span className="relative z-10 flex items-center">
              <motion.span
                className="mr-1"
                animate={{ rotate: [0, 15, 0, -15, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                ✨
              </motion.span>
              Sign In
            </span>
          </motion.button>
        </div>

        {/* Enhanced Mobile menu button with animations */}
        <div className="flex md:hidden">
          <motion.button
            whileTap={{ scale: 0.9 }}
            type="button"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="text-white p-3 relative rounded-full"
            aria-expanded={isMobileMenuOpen}
            style={{
              background: isMobileMenuOpen ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
              boxShadow: isMobileMenuOpen ? '0 0 10px rgba(59, 130, 246, 0.2)' : 'none'
            }}
          >
            <span className="sr-only">Open main menu</span>
            <motion.div className="relative w-6 h-5">
              <motion.span
                animate={isMobileMenuOpen ? { rotate: 45, y: 9, width: '100%' } : { rotate: 0, y: 0, width: '100%' }}
                transition={{ duration: 0.3 }}
                className="absolute h-0.5 left-0 right-0"
                style={{
                  backgroundColor: '#60A5FA',
                  top: '0%',
                  boxShadow: '0 0 5px rgba(96, 165, 250, 0.5)'
                }}
              />
              <motion.span
                animate={isMobileMenuOpen ? { opacity: 0 } : { opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="absolute h-0.5 left-0 right-0"
                style={{
                  backgroundColor: '#60A5FA',
                  top: '40%',
                  boxShadow: '0 0 5px rgba(96, 165, 250, 0.5)'
                }}
              />
              <motion.span
                animate={isMobileMenuOpen ? { rotate: -45, y: -9, width: '100%' } : { rotate: 0, y: 0, width: '75%' }}
                transition={{ duration: 0.3 }}
                className="absolute h-0.5 right-0"
                style={{
                  backgroundColor: '#60A5FA',
                  top: '80%',
                  boxShadow: '0 0 5px rgba(96, 165, 250, 0.5)'
                }}
              />
            </motion.div>
          </motion.button>
        </div>
      </div>

      {/* Advanced 3D Mobile menu with enhanced transitions */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0, rotateX: -10 }}
            animate={{ opacity: 1, height: 'auto', rotateX: 0 }}
            exit={{ opacity: 0, height: 0, rotateX: -10 }}
            transition={{ duration: 0.4, ease: "easeInOut" }}
            className="md:hidden overflow-hidden"
            style={{
              backgroundColor: 'rgba(15, 23, 42, 0.97)',
              backdropFilter: 'blur(12px)',
              boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.1), 0 8px 20px rgba(0, 0, 0, 0.2)',
              transformOrigin: 'top',
              perspective: '1000px',
              transformStyle: 'preserve-3d'
            }}
          >
            <motion.div
              className="p-3 flex flex-col gap-1"
              variants={{
                hidden: { opacity: 0 },
                show: {
                  opacity: 1,
                  transition: { staggerChildren: 0.07 }
                }
              }}
              initial="hidden"
              animate="show"
            >
              {navItems.map((item, index) => (
                <motion.div
                  key={item.name}
                  variants={{
                    hidden: { opacity: 0, y: 20 },
                    show: { opacity: 1, y: 0 }
                  }}
                  transition={{ duration: 0.3 }}
                >
                  <Link href={item.href}>
                    <motion.div
                      whileTap={{ scale: 0.95 }}
                      className="block py-3 px-4 rounded-lg transition-colors duration-200 flex items-center"
                      style={{
                        fontSize: '16px',
                        fontWeight: '500',
                        color: router.pathname === item.href ? '#93C5FD' : 'white',
                        backgroundColor: router.pathname === item.href ? 'rgba(37, 99, 235, 0.2)' : 'transparent',
                        cursor: 'pointer',
                        textShadow: '0 1px 2px rgba(0,0,0,0.5)',
                        borderLeft: router.pathname === item.href ? '3px solid #60A5FA' : '3px solid transparent',
                      }}
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      {/* Icon */}
                      {item.icon && (
                        <span className="inline-block w-6 text-center mr-3">
                          {item.icon}
                        </span>
                      )}

                      {/* Label */}
                      {item.label}

                      {/* Decorative star */}
                      {router.pathname === item.href && (
                        <div className="ml-auto text-blue-300 opacity-70">✧</div>
                      )}
                    </motion.div>
                  </Link>
                </motion.div>
              ))}

              {/* Enhanced Mobile sign in button with cosmic effects */}
              <motion.button
                variants={{
                  hidden: { opacity: 0, y: 20, rotateX: -20 },
                  show: { opacity: 1, y: 0, rotateX: 0 }
                }}
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.95 }}
                className="cosmic-btn w-full mt-3 py-3 px-4 rounded-lg flex items-center justify-center"
              >
                <motion.span
                  className="mr-2"
                  animate={{ rotate: [0, 20, 0, -20, 0] }}
                  transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                >
                  ✨
                </motion.span>
                Sign In
              </motion.button>

              {/* Enhanced decorative space elements with proper animation classes */}
              <div className="absolute top-5 right-5 h-1 w-1 rounded-full bg-white opacity-50 star-small"></div>
              <div className="absolute bottom-10 left-10 h-1 w-1 rounded-full bg-blue-300 opacity-40 star-blue" style={{ animationDelay: '1s' }}></div>
              <div className="absolute top-20 left-20 h-0.5 w-0.5 rounded-full bg-white opacity-60 star" style={{ animationDelay: '0.5s' }}></div>
              <div className="absolute bottom-20 right-20 h-0.5 w-0.5 rounded-full bg-white opacity-30 star" style={{ animationDelay: '1.5s' }}></div>

              {/* Additional nebula effect for depth */}
              <div className="absolute inset-0 pointer-events-none nebula-cloud opacity-5"></div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
};
