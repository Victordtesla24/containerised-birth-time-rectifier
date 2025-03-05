import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

interface NavItem {
  name: string;
  href: string;
  label: string;
}

export const CelestialNavbar: React.FC = () => {
  const router = useRouter();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Navigation items
  const navItems: NavItem[] = [
    { name: 'home', href: '/', label: 'Home' },
    { name: 'analysis', href: '/birth-time-analysis', label: 'Start Analysis' },
    { name: 'about', href: '/about', label: 'About' },
    { name: 'faq', href: '/faq', label: 'FAQ' },
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

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 ${isScrolled ? 'py-2' : 'py-4'} transition-all duration-300 ${isScrolled ? 'bg-slate-900/90' : 'bg-transparent'}`}
      style={{
        boxShadow: isScrolled ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none'
      }}
    >
      <div className="max-w-7xl mx-auto px-4 flex items-center justify-between">
        {/* Logo */}
        <Link href="/">
          <div className="flex items-center cursor-pointer">
            <span className="w-8 h-8 mr-2 relative flex items-center justify-center"
              style={{
                backgroundColor: '#3B82F6',
                borderRadius: '50%'
              }}
            >
              <div className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center">
                <div className="w-1 h-1 rounded-full"
                  style={{ backgroundColor: '#60A5FA' }}
                ></div>
              </div>
            </span>
            <span className="text-xl font-bold text-white"
              style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}
            >
              Birth Time Rectification
            </span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-8">
          {navItems.map((item) => (
            <Link
              key={item.name}
              href={item.href}
            >
              <div
                className="relative px-1 py-2 text-sm font-medium transition-colors duration-200"
                style={{
                  color: router.pathname === item.href ? '#93C5FD' : '#E5E7EB',
                  textShadow: '0 1px 2px rgba(0,0,0,0.5)',
                  cursor: 'pointer'
                }}
              >
                {item.label}
                {router.pathname === item.href && (
                  <div
                    className="absolute bottom-0 left-0 right-0 h-0.5"
                    style={{ backgroundColor: '#60A5FA' }}
                  />
                )}
              </div>
            </Link>
          ))}

          <button
            className="transition-all duration-200 hover:translate-y-[-2px]"
            style={{
              padding: '8px 16px',
              borderRadius: '9999px',
              background: 'linear-gradient(to right, #2563EB, #4F46E5)',
              color: 'white',
              fontSize: '14px',
              fontWeight: '500',
              boxShadow: '0 4px 6px -1px rgba(37, 99, 235, 0.3)',
              border: 'none',
              cursor: 'pointer',
              textShadow: '0 1px 2px rgba(0,0,0,0.5)'
            }}
          >
            Sign In
          </button>
        </div>

        {/* Mobile menu button */}
        <div className="flex md:hidden">
          <button
            type="button"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="text-white p-2"
            aria-expanded={isMobileMenuOpen}
          >
            <span className="sr-only">Open main menu</span>
            <div className="relative w-6 h-6">
              <span
                className={`absolute w-6 h-0.5 transition-all duration-300 ${isMobileMenuOpen ? 'rotate-45 translate-y-0' : 'translate-y-2'}`}
                style={{ backgroundColor: '#60A5FA' }}
              />
              <span
                className={`absolute w-6 h-0.5 transition-opacity duration-300 ${isMobileMenuOpen ? 'opacity-0' : 'opacity-100'}`}
                style={{ backgroundColor: '#60A5FA' }}
              />
              <span
                className={`absolute w-6 h-0.5 transition-all duration-300 ${isMobileMenuOpen ? '-rotate-45 translate-y-0' : 'translate-y-4'}`}
                style={{ backgroundColor: '#60A5FA' }}
              />
            </div>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <div
        className={`md:hidden transition-all duration-300 bg-slate-900/95 ${isMobileMenuOpen ? 'max-h-screen opacity-100' : 'max-h-0 opacity-0 overflow-hidden'}`}
      >
        <div className="p-3 flex flex-col gap-1">
          {navItems.map((item) => (
            <Link
              key={item.name}
              href={item.href}
            >
              <div
                className="block py-3 px-3 rounded-lg transition-colors duration-200"
                style={{
                  fontSize: '16px',
                  fontWeight: '500',
                  color: router.pathname === item.href ? '#93C5FD' : 'white',
                  backgroundColor: router.pathname === item.href ? 'rgba(37, 99, 235, 0.2)' : 'transparent',
                  cursor: 'pointer',
                  textShadow: '0 1px 2px rgba(0,0,0,0.5)'
                }}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                {item.label}
              </div>
            </Link>
          ))}
          <button className="w-full mt-3 py-3 px-4 rounded-lg transition-colors duration-200"
            style={{
              background: 'linear-gradient(to right, #2563EB, #4F46E5)',
              color: 'white',
              fontWeight: '500',
              border: 'none',
              cursor: 'pointer',
              textShadow: '0 1px 2px rgba(0,0,0,0.5)'
            }}
          >
            Sign In
          </button>
        </div>
      </div>
    </nav>
  );
};
