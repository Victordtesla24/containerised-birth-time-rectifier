import React, { useState } from 'react';
import Head from 'next/head';
import dynamic from 'next/dynamic';

// Import with dynamic to ensure client-side only rendering
const DynamicCelestialCanvas = dynamic(
  () => import('../components/three-scene/CelestialCanvas'),
  { ssr: false }
);

/**
 * WebGL Test Page
 * Used to verify WebGL rendering, error handling, and adaptive quality
 */
export default function WebGLTestPage() {
  const [isLoaded, setIsLoaded] = useState(false);
  const [canvasError, setCanvasError] = useState(null);

  // Handle canvas ready event
  const handleCanvasReady = () => {
    setIsLoaded(true);
    console.log('CelestialCanvas is ready');
  };

  // Handle canvas error event
  const handleCanvasError = (error) => {
    setCanvasError(error);
    console.error('CelestialCanvas error:', error);
  };

  return (
    <div className="webgl-test-page">
      <Head>
        <title>WebGL Test | Birth Time Rectifier</title>
      </Head>

      <main>
        <div className="info-panel">
          <h1>WebGL Rendering Test</h1>
          <p>Testing WebGL error handling, adaptive quality, and performance monitoring</p>

          <div className="status">
            <h2>Canvas Status:</h2>
            <div className={`status-indicator ${isLoaded ? 'success' : canvasError ? 'error' : 'loading'}`}>
              {isLoaded ? 'Ready' : canvasError ? 'Error' : 'Loading...'}
            </div>

            {canvasError && (
              <div className="error-details">
                <h3>Error Details:</h3>
                <pre>{canvasError.message || 'Unknown error'}</pre>
              </div>
            )}
          </div>
        </div>

        <div className="canvas-container">
          <DynamicCelestialCanvas
            enableRotation={true}
            particleCount={1000}
            onReady={handleCanvasReady}
            onError={handleCanvasError}
          />
        </div>
      </main>

      <style jsx>{`
        .webgl-test-page {
          width: 100%;
          min-height: 100vh;
          color: white;
        }

        main {
          position: relative;
          width: 100%;
          min-height: 100vh;
          z-index: 1;
        }

        .info-panel {
          position: absolute;
          top: 20px;
          left: 20px;
          max-width: 400px;
          background-color: rgba(15, 23, 42, 0.8);
          backdrop-filter: blur(10px);
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
          border: 1px solid rgba(96, 165, 250, 0.2);
          z-index: 10;
        }

        h1 {
          margin-top: 0;
          font-size: 24px;
          margin-bottom: 8px;
          background: linear-gradient(90deg, #60a5fa, #a78bfa);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        p {
          margin-bottom: 20px;
          font-size: 16px;
          line-height: 1.5;
          color: #cbd5e1;
        }

        .status {
          background-color: rgba(30, 41, 59, 0.5);
          border-radius: 8px;
          padding: 15px;
        }

        h2 {
          font-size: 18px;
          margin-top: 0;
          margin-bottom: 10px;
        }

        .status-indicator {
          display: inline-block;
          padding: 5px 12px;
          border-radius: 20px;
          font-weight: 600;
          font-size: 14px;
        }

        .status-indicator.loading {
          background-color: #3b82f6;
          color: white;
        }

        .status-indicator.success {
          background-color: #10b981;
          color: white;
        }

        .status-indicator.error {
          background-color: #ef4444;
          color: white;
        }

        .error-details {
          margin-top: 15px;
          padding: 10px;
          background-color: rgba(239, 68, 68, 0.1);
          border-radius: 6px;
          border-left: 3px solid #ef4444;
        }

        .error-details h3 {
          margin: 0 0 10px 0;
          font-size: 16px;
          color: #ef4444;
        }

        pre {
          font-family: monospace;
          white-space: pre-wrap;
          word-break: break-all;
          font-size: 12px;
          color: #cbd5e1;
          max-height: 150px;
          overflow-y: auto;
        }

        .canvas-container {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100vh;
        }
      `}</style>
    </div>
  );
}
