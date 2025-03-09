import React, { useEffect, useRef, useState, Suspense } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import dynamic from 'next/dynamic';

// Import the 3D scene components with dynamic import (no SSR) to prevent hydration errors
const CelestialCanvas = dynamic(
  () => import('../components/three-scene/CelestialCanvas'),
  { ssr: false, suspense: true }
);

export default function About() {
  const [scrollY, setScrollY] = useState(0);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [pageLoaded, setPageLoaded] = useState(false);

  // Handle scroll and mouse movement for 3D effects
  useEffect(() => {
    const handleScroll = () => {
      setScrollY(window.scrollY);
    };

    // Handle mouse movement for 3D effect
    const handleMouseMove = (e) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 2; // -1 to 1
      const y = (e.clientY / window.innerHeight - 0.5) * 2; // -1 to 1
      setMousePosition({ x, y });
    };

    window.addEventListener('scroll', handleScroll);
    window.addEventListener('mousemove', handleMouseMove);

    // Set page as loaded
    setPageLoaded(true);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  return (
    <div className="cosmic-scene">
      <Head>
        <title>About | Birth Time Rectification</title>
        <meta name="description" content="Learn about our advanced birth time rectification methods" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* 3D Background Scene */}
      {pageLoaded && (
        <Suspense fallback={null}>
          <CelestialCanvas mousePosition={mousePosition} scrollY={scrollY} />
        </Suspense>
      )}

      {/* Content container */}
      <div className="content-container">
        <header className="cosmic-header">
          <div className="logo">
            <Link href="/">
              <span className="logo-text">Birth Time Rectifier</span>
            </Link>
          </div>
          <nav>
            <Link href="/">
              <span className="nav-link">Home</span>
            </Link>
            <Link href="/birth-time-analysis">
              <span className="nav-link">Analysis</span>
            </Link>
          </nav>
        </header>

        <main>
          <div
            className="about-container"
            style={{
              transform: `translateZ(30px) rotateX(${mousePosition.y * -2}deg) rotateY(${mousePosition.x * 2}deg)`
            }}
          >
            <h1>About Birth Time Rectification</h1>

            <div className="about-content">
              <div className="about-section">
                <h2>Our Approach</h2>
                <p>Birth Time Rectification uses advanced celestial algorithms and pattern recognition to determine your precise birth time when it is unknown or uncertain. Our system analyzes planetary positions, aspects, and transits to identify the most likely time of birth based on life events and personal characteristics.</p>
              </div>

              <div className="planet-divider">
                <div className="planet-icon"></div>
              </div>

              <div className="about-section">
                <h2>Why Birth Time Matters</h2>
                <p>Your exact birth time determines critical elements of your astrological chart, including your Ascendant (Rising sign), house cusps, and the precise positioning of planets in houses. Even a difference of a few minutes can significantly alter these positions and their interpretation.</p>
              </div>

              <div className="planet-divider">
                <div className="planet-icon-alt"></div>
              </div>

              <div className="about-section">
                <h2>Our Technology</h2>
                <p>We combine traditional astrological techniques with modern computational methods and machine learning to analyze thousands of potential birth times and identify the most accurate match. Our algorithms have been refined through extensive testing and validation against known birth times.</p>
              </div>
            </div>

            <div className="cta-container">
              <Link href="/birth-time-analysis">
                <button className="cosmic-button primary">
                  Begin Your Analysis
                </button>
              </Link>
            </div>
          </div>
        </main>

        <footer className="cosmic-footer">
          <div className="footer-content">
            <p>© 2025 Birth Time Rectification | All Cosmic Rights Reserved</p>
            <div className="footer-links">
              <Link href="/privacy">Privacy Policy</Link>
              <Link href="/terms">Terms of Service</Link>
              <Link href="/contact">Contact</Link>
            </div>
          </div>
        </footer>
      </div>

      <style jsx>{`
        .cosmic-scene {
          perspective: 1000px;
          transform-style: preserve-3d;
          overflow-x: hidden;
          min-height: 100vh;
          background-color: #000000;
        }

        .content-container {
          position: relative;
          z-index: 10;
          color: white;
          font-family: 'Arial', sans-serif;
          transform-style: preserve-3d;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
        }

        .cosmic-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px;
          background: rgba(15, 23, 42, 0.6);
          backdrop-filter: blur(10px);
        }

        .logo-text {
          font-size: 1.5rem;
          font-weight: bold;
          background: linear-gradient(90deg, #60a5fa, #a78bfa);
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
          cursor: pointer;
        }

        nav {
          display: flex;
          gap: 20px;
        }

        .nav-link {
          color: #a5b4fc;
          transition: color 0.3s ease;
          cursor: pointer;
        }

        .nav-link:hover {
          color: #60a5fa;
        }

        main {
          flex: 1;
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 60px 20px;
        }

        .about-container {
          background: rgba(15, 23, 42, 0.7);
          border-radius: 15px;
          padding: 40px;
          backdrop-filter: blur(10px);
          border: 1px solid rgba(96, 165, 250, 0.2);
          width: 100%;
          max-width: 800px;
          box-shadow: 0 15px 35px rgba(0, 0, 0, 0.3);
          transform-style: preserve-3d;
          transition: transform 0.3s ease;
        }

        h1 {
          font-size: 2.5rem;
          margin-bottom: 2rem;
          background: linear-gradient(90deg, #60a5fa, #a78bfa, #60a5fa);
          background-size: 200% auto;
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
          text-align: center;
        }

        .about-content {
          display: flex;
          flex-direction: column;
          gap: 30px;
        }

        .about-section {
          padding: 20px;
          border-radius: 10px;
          background: rgba(30, 41, 59, 0.4);
          border: 1px solid rgba(96, 165, 250, 0.1);
          transform-style: preserve-3d;
          transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .about-section:hover {
          transform: translateY(-5px) translateZ(10px);
          box-shadow: 0 10px 25px rgba(96, 165, 250, 0.2);
          border-color: rgba(96, 165, 250, 0.3);
        }

        h2 {
          font-size: 1.5rem;
          margin-bottom: 1rem;
          color: #93c5fd;
        }

        p {
          color: #bfdbfe;
          line-height: 1.7;
          font-size: 1.1rem;
        }

        .planet-divider {
          display: flex;
          justify-content: center;
          align-items: center;
          position: relative;
          height: 60px;
        }

        .planet-divider::before,
        .planet-divider::after {
          content: '';
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(96, 165, 250, 0.5), transparent);
          flex: 1;
        }

        .planet-icon {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background-image: url('/images/planets/saturn/saturn-2.jpg');
          background-size: cover;
          margin: 0 15px;
          box-shadow: 0 0 15px rgba(96, 165, 250, 0.5);
        }

        .planet-icon-alt {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background-image: url('/images/planets/mars/mars-3.jpg');
          background-size: cover;
          margin: 0 15px;
          box-shadow: 0 0 15px rgba(96, 165, 250, 0.5);
        }

        .cta-container {
          margin-top: 40px;
          display: flex;
          justify-content: center;
        }

        .cosmic-button {
          padding: 12px 28px;
          border-radius: 30px;
          font-size: 1.1rem;
          font-weight: bold;
          border: none;
          cursor: pointer;
          transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
          position: relative;
          overflow: hidden;
        }

        .cosmic-button::before {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
          transition: left 0.7s ease;
        }

        .cosmic-button:hover::before {
          left: 100%;
        }

        .primary {
          background: linear-gradient(90deg, #3b82f6, #8b5cf6);
          color: white;
          box-shadow: 0 4px 15px rgba(59, 130, 246, 0.5);
        }

        .primary:hover {
          transform: translateY(-3px) scale(1.05);
          box-shadow: 0 8px 25px rgba(59, 130, 246, 0.6);
        }

        .cosmic-footer {
          padding: 30px 20px;
          background: rgba(2, 6, 23, 0.8);
          backdrop-filter: blur(10px);
        }

        .footer-content {
          max-width: 1200px;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
        }

        .footer-content p {
          color: #94a3b8;
          font-size: 0.9rem;
        }

        .footer-links {
          display: flex;
          gap: 20px;
        }

        .footer-links a {
          color: #94a3b8;
          text-decoration: none;
          transition: color 0.3s ease;
          font-size: 0.9rem;
        }

        .footer-links a:hover {
          color: #60a5fa;
        }

        /* Responsive design */
        @media (max-width: 768px) {
          h1 {
            font-size: 2rem;
          }

          main {
            padding: 40px 15px;
          }

          .about-container {
            padding: 25px;
          }

          .footer-content {
            flex-direction: column;
            text-align: center;
            gap: 20px;
          }
        }
      `}</style>
    </div>
  );
}
