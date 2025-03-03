import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

export default function Navbar() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  return (
    <nav className="bg-primary-800 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="flex-shrink-0">
              <span className="text-xl font-bold">Birth Time Rectifier</span>
            </Link>
            <div className="hidden md:block">
              <div className="ml-10 flex items-baseline space-x-4">
                <Link href="/" className={`px-3 py-2 rounded-md text-sm font-medium ${router.pathname === '/' ? 'bg-primary-900' : 'hover:bg-primary-700'}`}>
                  Home
                </Link>
                <Link href="/birth-details" className={`px-3 py-2 rounded-md text-sm font-medium ${router.pathname.startsWith('/birth-details') ? 'bg-primary-900' : 'hover:bg-primary-700'}`}>
                  Birth Details
                </Link>
                <Link href="/about" className={`px-3 py-2 rounded-md text-sm font-medium ${router.pathname === '/about' ? 'bg-primary-900' : 'hover:bg-primary-700'}`}>
                  About
                </Link>
              </div>
            </div>
          </div>
          
          {/* Mobile menu button */}
          <div className="md:hidden">
            <button 
              onClick={toggleMenu}
              className="inline-flex items-center justify-center p-2 rounded-md text-white hover:bg-primary-700 focus:outline-none"
            >
              <svg 
                className="h-6 w-6" 
                xmlns="http://www.w3.org/2000/svg" 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                {isOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {isOpen && (
        <div className="md:hidden">
          <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3">
            <Link href="/" className={`block px-3 py-2 rounded-md text-base font-medium ${router.pathname === '/' ? 'bg-primary-900' : 'hover:bg-primary-700'}`}>
              Home
            </Link>
            <Link href="/birth-details" className={`block px-3 py-2 rounded-md text-base font-medium ${router.pathname.startsWith('/birth-details') ? 'bg-primary-900' : 'hover:bg-primary-700'}`}>
              Birth Details
            </Link>
            <Link href="/about" className={`block px-3 py-2 rounded-md text-base font-medium ${router.pathname === '/about' ? 'bg-primary-900' : 'hover:bg-primary-700'}`}>
              About
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
} 