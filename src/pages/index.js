import React, { useEffect, useRef, useState, Suspense } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import dynamic from 'next/dynamic';

// Import the 3D scene components with dynamic import (no SSR) to prevent hydration errors
const CelestialCanvas = dynamic(
  () => import('../components/three-scene/CelestialCanvas'),
  { ssr: false, suspense: true }
);

export default function Home() {
  const [scrollY, setScrollY] = useState(0);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [imagesLoaded, setImagesLoaded] = useState(false);
  const [pageLoaded, setPageLoaded] = useState(false);

  // Handle scroll and mouse movement for 3D effects
  useEffect(() => {
    const handleScroll = () => {
      setScrollY(window.scrollY);
    };

    const handleMouseMove = (e) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 2; // -1 to 1
      const y = (e.clientY / window.innerHeight - 0.5) * 2; // -1 to 1
      setMousePosition({ x, y });
    };

    window.addEventListener('scroll', handleScroll);
    window.addEventListener('mousemove', handleMouseMove);

    // Set page as loaded
    setPageLoaded(true);

    // Force hide loading screen after 5 seconds as a fallback
    const forceLoadTimer = setTimeout(() => {
      setImagesLoaded(true);
      console.log("Force loading complete after timeout");
    }, 5000);

    // Check when all images are loaded
    const imageElements = document.querySelectorAll('img');
    let loadedCount = 0;

    const imageLoaded = () => {
      loadedCount++;
      console.log(`Image loaded: ${loadedCount}/${imageElements.length}`);
      if (loadedCount === imageElements.length) {
        console.log("All images loaded naturally");
        clearTimeout(forceLoadTimer); // Clear the timeout if images load naturally
        setImagesLoaded(true);
      }
    };

    imageElements.forEach(img => {
      if (img.complete) {
        imageLoaded();
      } else {
        img.addEventListener('load', imageLoaded);
      }
    });

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('mousemove', handleMouseMove);
      clearTimeout(forceLoadTimer);
      imageElements.forEach(img => {
        img.removeEventListener('load', imageLoaded);
      });
    };
  }, []);

  return (
    <div className="cosmic-scene">
      <Head>
        <title>Birth Time Rectification | Cosmic Analysis</title>
        <meta name="description" content="Advanced birth time rectification using cosmic patterns" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* 3D Background Scene */}
      {pageLoaded && (
        <Suspense fallback={null}>
          <CelestialCanvas mousePosition={mousePosition} scrollY={scrollY} />
        </Suspense>
      )}

      {/* Loading overlay */}
      {!imagesLoaded && (
        <div className="loading-overlay">
          <div className="loader"></div>
          <p>Entering the cosmic gateway...</p>
        </div>
      )}

      {/* Content container */}
      <div className="content-container">
        <main>
          <div
            className="hero-content"
            style={{
              transform: `translateY(${scrollY * -0.2}px) translateZ(60px) rotateX(${mousePosition.y * -5}deg) rotateY(${mousePosition.x * 5}deg)`
            }}
          >
            <h1>Birth Time Rectification</h1>
            <p>Discover your precise birth time through advanced cosmic pattern analysis</p>

            <div className="buttons-container">
              <Link href="/birth-time-analysis">
                <button className="cosmic-button primary" data-testid="get-started-button">
                  Begin Your Journey
                </button>
              </Link>
              <Link href="/about">
                <button className="cosmic-button secondary">
                  Learn More
                </button>
              </Link>
            </div>
          </div>

          <div className="features-section">
            <h2>Celestial Analysis Features</h2>
            <div className="features-grid">
              <div
                className="feature-card"
                style={{
                  transform: `translateZ(40px) rotateX(${mousePosition.y * -2}deg) rotateY(${mousePosition.x * 2}deg)`,
                  transitionDelay: '0.1s'
                }}
              >
                <div className="feature-icon planet-icon-1"></div>
                <h3>Planetary Positions</h3>
                <p>Analyze exact positions of celestial bodies at your birth moment</p>
              </div>

              <div
                className="feature-card"
                style={{
                  transform: `translateZ(40px) rotateX(${mousePosition.y * -2}deg) rotateY(${mousePosition.x * 2}deg)`,
                  transitionDelay: '0.2s'
                }}
              >
                <div className="feature-icon planet-icon-2"></div>
                <h3>Cosmic Patterns</h3>
                <p>Identify unique cosmic patterns that reveal your true birth time</p>
              </div>

              <div
                className="feature-card"
                style={{
                  transform: `translateZ(40px) rotateX(${mousePosition.y * -2}deg) rotateY(${mousePosition.x * 2}deg)`,
                  transitionDelay: '0.3s'
                }}
              >
                <div className="feature-icon planet-icon-3"></div>
                <h3>Astrological Insights</h3>
                <p>Gain profound insights through rectified birth time analysis</p>
              </div>
            </div>
          </div>
        </main>

        <footer>
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

        .loading-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background-color: #000;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          z-index: 1000;
          color: white;
          font-family: 'Arial', sans-serif;
        }

        .loader {
          border: 3px solid #0f172a;
          border-top: 3px solid #60a5fa;
          border-radius: 50%;
          width: 50px;
          height: 50px;
          animation: spin 1s linear infinite;
          margin-bottom: 20px;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .content-container {
          position: relative;
          z-index: 10;
          color: white;
          font-family: 'Arial', sans-serif;
          padding-top: 10vh;
          transform-style: preserve-3d;
        }

        main {
          min-height: 100vh;
        }

        .hero-content {
          text-align: center;
          padding: 0 20px;
          max-width: 800px;
          margin: 0 auto;
          transform-style: preserve-3d;
          transition: transform 0.3s ease-out;
        }

        h1 {
          font-size: 4rem;
          margin-bottom: 1rem;
          background: linear-gradient(90deg, #60a5fa, #a78bfa, #60a5fa);
          background-size: 200% auto;
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
          animation: gradientText 6s linear infinite;
          text-shadow: 0 0 20px rgba(96, 165, 250, 0.5);
        }

        @keyframes gradientText {
          0% { background-position: 0% center; }
          100% { background-position: 200% center; }
        }

        .hero-content p {
          font-size: 1.5rem;
          color: #a5b4fc;
          margin-bottom: 2rem;
          line-height: 1.5;
        }

        .buttons-container {
          display: flex;
          justify-content: center;
          gap: 20px;
          margin-top: 30px;
        }

        .cosmic-button {
          padding: 12px 24px;
          border-radius: 30px;
          font-size: 1rem;
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

        .secondary {
          background: rgba(15, 23, 42, 0.6);
          color: #a5b4fc;
          border: 1px solid rgba(96, 165, 250, 0.3);
          backdrop-filter: blur(10px);
        }

        .secondary:hover {
          background: rgba(30, 41, 59, 0.8);
          transform: translateY(-3px);
          box-shadow: 0 4px 15px rgba(96, 165, 250, 0.3);
          color: #bfdbfe;
        }

        .features-section {
          padding: 100px 20px;
          text-align: center;
          max-width: 1200px;
          margin: 0 auto;
        }

        .features-section h2 {
          font-size: 2.5rem;
          margin-bottom: 3rem;
          color: #bfdbfe;
        }

        .features-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 30px;
          justify-content: center;
        }

        .feature-card {
          background: rgba(15, 23, 42, 0.6);
          border-radius: 15px;
          padding: 30px;
          backdrop-filter: blur(10px);
          border: 1px solid rgba(96, 165, 250, 0.2);
          transition: all 0.3s ease;
          transform-style: preserve-3d;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        }

        .feature-card:hover {
          border-color: rgba(96, 165, 250, 0.5);
          box-shadow: 0 15px 35px rgba(0, 0, 0, 0.3), 0 0 15px rgba(96, 165, 250, 0.3);
          transform: translateY(-10px) translateZ(50px) !important;
        }

        .feature-icon {
          width: 80px;
          height: 80px;
          border-radius: 50%;
          margin: 0 auto 20px;
          background-size: cover;
          background-position: center;
          box-shadow: 0 0 20px rgba(96, 165, 250, 0.4);
        }

        .planet-icon-1 {
          background-image: url('/images/planets/mars/mars.jpg');
        }

        .planet-icon-2 {
          background-image: url('/images/planets/venus/venus.png');
        }

        .planet-icon-3 {
          background-image: url('/images/planets/moon/moon-1.jpg');
        }

        .feature-card h3 {
          font-size: 1.5rem;
          margin-bottom: 15px;
          color: #93c5fd;
        }

        .feature-card p {
          color: #bfdbfe;
          line-height: 1.6;
        }

        footer {
          padding: 40px 20px;
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
        }

        .footer-links {
          display: flex;
          gap: 20px;
        }

        .footer-links a {
          color: #94a3b8;
          text-decoration: none;
          transition: color 0.3s ease;
        }

        .footer-links a:hover {
          color: #60a5fa;
        }

        /* Responsive design */
        @media (max-width: 768px) {
          h1 {
            font-size: 2.5rem;
          }

          .hero-content p {
            font-size: 1.1rem;
          }

          .buttons-container {
            flex-direction: column;
            align-items: center;
          }

          .cosmic-button {
            width: 100%;
            max-width: 300px;
            margin-bottom: 10px;
          }

          .features-grid {
            grid-template-columns: 1fr;
          }

          .footer-content {
            flex-direction: column;
            text-align: center;
            gap: 20px;
          }
        }

        .planet-icon-1, .planet-icon-2, .planet-icon-3 {
          transition: transform 0.3s ease;
        }

        .feature-card:hover .planet-icon-1,
        .feature-card:hover .planet-icon-2,
        .feature-card:hover .planet-icon-3 {
          transform: scale(1.1);
        }
      `}</style>
    </div>
  );
}
