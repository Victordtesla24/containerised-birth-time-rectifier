import React from 'react';
import Head from 'next/head';
import Link from 'next/link';

/**
 * Layout component for consistent page structure
 * 
 * @param {Object} props
 * @param {React.ReactNode} props.children - Page content
 * @param {string} props.title - Page title
 * @returns {JSX.Element}
 */
const Layout = ({ children, title = 'Birth Time Rectifier - AI-Powered Vedic Astrology' }) => {
  return (
    <div className="layout min-h-screen bg-indigo-950 text-white flex flex-col">
      <Head>
        <title>{title}</title>
        <meta name="description" content="AI-powered birth time rectification tool using Vedic astrology principles" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <header className="relative z-10 bg-indigo-900 bg-opacity-70 shadow-md">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/">
            <div className="logo flex items-center space-x-2 cursor-pointer">
              <div className="text-2xl">✨</div>
              <div className="font-bold text-xl text-white">Birth Time Rectifier</div>
            </div>
          </Link>
          
          <nav className="hidden md:flex space-x-6">
            <Link href="/">
              <div className="nav-link text-indigo-200 hover:text-white transition">Home</div>
            </Link>
            <Link href="/birth-details">
              <div className="nav-link text-indigo-200 hover:text-white transition">New Analysis</div>
            </Link>
          </nav>
          
          <div className="md:hidden">
            {/* Mobile menu button would go here */}
            <button className="text-white focus:outline-none">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7" />
              </svg>
            </button>
          </div>
        </div>
      </header>
      
      <main className="flex-grow">
        {children}
      </main>
      
      <footer className="relative z-10 bg-indigo-900 bg-opacity-70 py-6">
        <div className="container mx-auto px-4 text-center text-indigo-200 text-sm">
          <p>&copy; {new Date().getFullYear()} Birth Time Rectifier. All rights reserved.</p>
          <p className="mt-2">Built with AI-powered astrological algorithms and Vedic principles.</p>
        </div>
      </footer>
    </div>
  );
};

export default Layout; 