import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

export default function Navbar() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  const isActive = (path: string) => {
    return router.pathname === path || router.pathname.startsWith(path);
  };

  return (
    <nav className="bg-gray-800 text-white fixed top-0 left-0 right-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link href="/">
              <span className="text-xl font-bold cursor-pointer">Birth Time Rectifier</span>
            </Link>
          </div>

          {/* Desktop menu */}
          <div className="hidden md:block">
            <div className="flex items-center space-x-4">
              <Link href="/birth-time-rectifier">
                <span className={`px-3 py-2 rounded-md text-sm font-medium cursor-pointer ${
                  isActive('/birth-time-rectifier') && !isActive('/birth-time-rectifier/questionnaire') && !isActive('/birth-time-rectifier/analysis') && !isActive('/birth-time-rectifier/settings')
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}>
                  Birth Details
                </span>
              </Link>
              <Link href="/birth-time-rectifier/questionnaire">
                <span className={`px-3 py-2 rounded-md text-sm font-medium cursor-pointer ${
                  isActive('/birth-time-rectifier/questionnaire')
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}>
                  Questionnaire
                </span>
              </Link>
              <Link href="/birth-time-rectifier/analysis">
                <span className={`px-3 py-2 rounded-md text-sm font-medium cursor-pointer ${
                  isActive('/birth-time-rectifier/analysis')
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}>
                  Analysis
                </span>
              </Link>
              
              {/* Settings dropdown */}
              <div className="relative">
                <button
                  onClick={toggleMenu}
                  className={`px-3 py-2 rounded-md text-sm font-medium cursor-pointer flex items-center ${
                    isActive('/birth-time-rectifier/settings')
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  Settings
                  <svg
                    className={`ml-1 h-4 w-4 transition-transform transform ${isOpen ? 'rotate-180' : 'rotate-0'}`}
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
                
                {isOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-10">
                    <Link href="/birth-time-rectifier/settings/preferences">
                      <span className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer">
                        Preferences
                      </span>
                    </Link>
                    <Link href="/birth-time-rectifier/settings/account">
                      <span className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer">
                        Account
                      </span>
                    </Link>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={toggleMenu}
              className="text-gray-400 hover:text-white focus:outline-none focus:text-white"
            >
              <svg
                className="h-6 w-6"
                stroke="currentColor"
                fill="none"
                viewBox="0 0 24 24"
              >
                {isOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 6h16M4 12h16M4 18h16"
                  />
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
            <Link href="/birth-time-rectifier">
              <span className={`block px-3 py-2 rounded-md text-base font-medium cursor-pointer ${
                isActive('/birth-time-rectifier') && !isActive('/birth-time-rectifier/questionnaire') && !isActive('/birth-time-rectifier/analysis') && !isActive('/birth-time-rectifier/settings')
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}>
                Birth Details
              </span>
            </Link>
            <Link href="/birth-time-rectifier/questionnaire">
              <span className={`block px-3 py-2 rounded-md text-base font-medium cursor-pointer ${
                isActive('/birth-time-rectifier/questionnaire')
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}>
                Questionnaire
              </span>
            </Link>
            <Link href="/birth-time-rectifier/analysis">
              <span className={`block px-3 py-2 rounded-md text-base font-medium cursor-pointer ${
                isActive('/birth-time-rectifier/analysis')
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}>
                Analysis
              </span>
            </Link>
            <Link href="/birth-time-rectifier/settings/preferences">
              <span className={`block px-3 py-2 rounded-md text-base font-medium cursor-pointer ${
                isActive('/birth-time-rectifier/settings/preferences')
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}>
                Preferences
              </span>
            </Link>
            <Link href="/birth-time-rectifier/settings/account">
              <span className={`block px-3 py-2 rounded-md text-base font-medium cursor-pointer ${
                isActive('/birth-time-rectifier/settings/account')
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}>
                Account
              </span>
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
} 