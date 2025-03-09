import React, { useRef, useEffect, useState, useMemo } from 'react';
import * as THREE from 'three';
import PropTypes from 'prop-types';
import { useQuality } from './core/QualityContext';
import WebGLContextHandler from './core/WebGLContextHandler';
import textureManager from './utils/TextureManager';
import PerformanceMonitor from './core/PerformanceMonitor';
import LoadingScreen from './core/LoadingScreen';

/**
 * Enhanced CelestialCanvas component with WebGL error handling,
 * adaptive quality settings, and loading management.
 */
const CelestialCanvas = ({
  enableRotation = true,
  backgroundColor = 0x000011,
  particleCount = 500,
  onReady = null,
  onError = null,
  fallbackContent = null
}) => {
  // Refs for DOM elements and three.js instances
  const canvasRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const animationFrameRef = useRef(null);

  // State for component
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState(null);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [contextLost, setContextLost] = useState(false);
  const [fallbackMode, setFallbackMode] = useState(false);

  // Get quality settings from context
  const quality = useQuality();

  // Controls and handlers
  const contextHandlerRef = useRef(null);
  const performanceMonitorRef = useRef(null);

  // Memoize performance monitor options based on quality settings
  const performanceMonitorOptions = useMemo(() => {
    return {
      targetFps: quality.maxFPS,
      warningThreshold: Math.floor(quality.maxFPS * 0.5),
      criticalThreshold: Math.floor(quality.maxFPS * 0.3),
      onQualitySuggestion: (suggestion) => {
        if (quality.adaptiveQuality) {
          quality.updateQuality(suggestion.suggestions);
        }
      }
    };
  }, [quality]);

  // Setup scene, camera and renderer
  useEffect(() => {
    if (!canvasRef.current) return;

    // Check WebGL support
    if (!quality.webglSupported) {
      setError(new Error('WebGL not supported by your browser'));
      setFallbackMode(true);
      return;
    }

    // Initialize renderer
    try {
      let renderer;

      // Create renderer with quality settings
      renderer = new THREE.WebGLRenderer({
        canvas: canvasRef.current,
        antialias: quality.antialias,
        alpha: true,
        powerPreference: 'high-performance',
        logarithmicDepthBuffer: true
      });

      renderer.setPixelRatio(quality.pixelRatio);
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setClearColor(backgroundColor, 1);
      renderer.outputColorSpace = THREE.SRGBColorSpace;

      rendererRef.current = renderer;

      // Create WebGL context handler
      contextHandlerRef.current = new WebGLContextHandler(renderer);

      // Handle context loss events
      contextHandlerRef.current.on('contextLost', () => {
        setContextLost(true);
        console.warn('WebGL context lost - pausing rendering');

        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
          animationFrameRef.current = null;
        }
      });

      // Handle context restoration events
      contextHandlerRef.current.on('contextRestored', () => {
        setContextLost(false);
        console.info('WebGL context restored - resuming rendering');

        // Restart animation loop
        if (!animationFrameRef.current && sceneRef.current && cameraRef.current) {
          animate();
        }

        // Reload textures if needed
        reloadTextures();
      });

      // Scene and camera setup
      const scene = new THREE.Scene();
      sceneRef.current = scene;

      const camera = new THREE.PerspectiveCamera(
        70,
        window.innerWidth / window.innerHeight,
        0.1,
        2000
      );
      camera.position.z = 5;
      cameraRef.current = camera;

      // Create performance monitor
      performanceMonitorRef.current = new PerformanceMonitor(performanceMonitorOptions);
      performanceMonitorRef.current.start();

      // Start the setup process
      setupScene();

      // Handle window resize
      const handleResize = () => {
        if (!cameraRef.current || !rendererRef.current) return;

        cameraRef.current.aspect = window.innerWidth / window.innerHeight;
        cameraRef.current.updateProjectionMatrix();
        rendererRef.current.setSize(window.innerWidth, window.innerHeight);
      };

      window.addEventListener('resize', handleResize);

      // Cleanup
      return () => {
        window.removeEventListener('resize', handleResize);

        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
        }

        if (performanceMonitorRef.current) {
          performanceMonitorRef.current.stop();
        }

        if (contextHandlerRef.current) {
          contextHandlerRef.current.dispose();
        }

        if (rendererRef.current) {
          rendererRef.current.dispose();
        }

        // Dispose textures
        textureManager.clearCache();
      };
    } catch (err) {
      console.error('Error initializing renderer:', err);
      setError(err);
      setFallbackMode(true);
    }
  }, [backgroundColor, quality, performanceMonitorOptions]);

  // Setup scene with stars and celestial objects
  const setupScene = async () => {
    if (!sceneRef.current || !cameraRef.current) return;

    try {
      setLoadingProgress(10);
      const scene = sceneRef.current;

      // Add ambient light
      const ambientLight = new THREE.AmbientLight(0x404040);
      scene.add(ambientLight);

      // Add point light (sun)
      const pointLight = new THREE.PointLight(0xffffff, 1, 100);
      pointLight.position.set(10, 10, 10);
      scene.add(pointLight);

      setLoadingProgress(30);

      // Add stars (particles)
      await addStarField();

      setLoadingProgress(70);

      // Add celestial objects with textures
      await addCelestialObjects();

      setLoadingProgress(100);

      // Start animation
      animate();

      setIsLoaded(true);

      // Notify parent component that canvas is ready
      if (onReady) {
        onReady();
      }
    } catch (err) {
      console.error('Error setting up scene:', err);
      setError(err);

      // Notify parent component of error
      if (onError) {
        onError(err);
      }
    }
  };

  // Add stars as particles
  const addStarField = async () => {
    if (!sceneRef.current) return;

    const scene = sceneRef.current;

    // Adjust particle count based on quality settings
    const adjustedParticleCount = quality.isLowEndDevice
      ? Math.floor(particleCount * 0.5)
      : particleCount;

    // Create particles
    const vertices = [];
    const sizes = [];
    const colors = [];

    // Star colors
    const starColors = [
      new THREE.Color(0xffffff), // White
      new THREE.Color(0xaaaaff), // Bluish
      new THREE.Color(0xffffaa), // Yellowish
      new THREE.Color(0xffaaaa)  // Reddish
    ];

    for (let i = 0; i < adjustedParticleCount; i++) {
      // Random position
      const x = (Math.random() - 0.5) * 2000;
      const y = (Math.random() - 0.5) * 2000;
      const z = (Math.random() - 0.5) * 2000;

      vertices.push(x, y, z);

      // Random size
      sizes.push(Math.random() * 2 + 0.5);

      // Random color
      const color = starColors[Math.floor(Math.random() * starColors.length)];
      colors.push(color.r, color.g, color.b);
    }

    // Create geometry
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setAttribute('size', new THREE.Float32BufferAttribute(sizes, 1));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    // Load star texture with fallback
    try {
      // Create material
      const starMaterial = new THREE.PointsMaterial({
        size: 1,
        transparent: true,
        opacity: 0.8,
        vertexColors: true,
        sizeAttenuation: true,
      });

      // Register a fallback texture
      textureManager.registerFallback('star', '/textures/star_fallback.png');

      // Load the texture with retry and fallback
      const starTexture = await textureManager.loadTexture('/textures/star.png', {
        category: 'star',
        onProgress: (progress) => {
          setLoadingProgress(30 + progress * 0.1);
        }
      });

      starMaterial.map = starTexture;

      // Create particle system
      const particles = new THREE.Points(geometry, starMaterial);
      particles.name = 'starField';
      scene.add(particles);

    } catch (err) {
      console.error('Error loading star texture:', err);
      // Continue without texture - simple dots
      const simpleMaterial = new THREE.PointsMaterial({
        size: 1,
        vertexColors: true,
      });

      const particles = new THREE.Points(geometry, simpleMaterial);
      particles.name = 'starField';
      scene.add(particles);
    }
  };

  // Add celestial objects (planets, etc.)
  const addCelestialObjects = async () => {
    if (!sceneRef.current) return;

    const scene = sceneRef.current;

    try {
      // Simplified for example - add a sun sphere
      const sunGeometry = new THREE.SphereGeometry(1, 32, 32);

      // Register a fallback texture
      textureManager.registerFallback('sun', '/textures/sun_fallback.jpg');

      // Load the texture with retry and fallback
      const sunTexture = await textureManager.loadTexture('/textures/sun.jpg', {
        category: 'sun',
        onProgress: (progress) => {
          setLoadingProgress(70 + progress * 0.3);
        }
      });

      const sunMaterial = new THREE.MeshStandardMaterial({
        map: sunTexture,
        emissive: 0xffff00,
        emissiveIntensity: 0.5,
        emissiveMap: sunTexture
      });

      const sun = new THREE.Mesh(sunGeometry, sunMaterial);
      sun.name = 'sun';
      scene.add(sun);

    } catch (err) {
      console.error('Error adding celestial objects:', err);

      // Fallback to simple colored sphere
      const sunGeometry = new THREE.SphereGeometry(1, 16, 16);
      const sunMaterial = new THREE.MeshBasicMaterial({ color: 0xffff00 });
      const sun = new THREE.Mesh(sunGeometry, sunMaterial);
      sun.name = 'sun';
      scene.add(sun);
    }
  };

  // Reload textures after context restoration
  const reloadTextures = async () => {
    if (!sceneRef.current) return;

    try {
      const scene = sceneRef.current;

      // Find objects with textures
      scene.traverse((object) => {
        if (object.material && object.material.map) {
          // Force texture update on next render
          object.material.needsUpdate = true;

          if (object.material.map.source) {
            object.material.map.needsUpdate = true;
          }
        }
      });

    } catch (err) {
      console.error('Error reloading textures:', err);
    }
  };

  // Animation loop
  const animate = () => {
    if (!sceneRef.current || !cameraRef.current || !rendererRef.current) return;

    const scene = sceneRef.current;
    const camera = cameraRef.current;
    const renderer = rendererRef.current;

    // Rotate star field
    if (enableRotation) {
      const starField = scene.getObjectByName('starField');
      if (starField) {
        starField.rotation.y += 0.0001;
        starField.rotation.x += 0.00005;
      }

      // Rotate sun
      const sun = scene.getObjectByName('sun');
      if (sun) {
        sun.rotation.y += 0.001;
      }
    }

    // Update performance monitor
    if (performanceMonitorRef.current) {
      performanceMonitorRef.current.update(renderer);
    }

    // Render scene
    renderer.render(scene, camera);

    // Continue animation loop
    animationFrameRef.current = requestAnimationFrame(animate);
  };

  // Handle manual context recovery attempt
  const handleRetry = () => {
    setError(null);

    if (contextLost && contextHandlerRef.current) {
      contextHandlerRef.current.manualRestore();
    } else {
      // Complete restart
      setupScene();
    }
  };

  // Render component
  return (
    <>
      {/* Main canvas */}
      <canvas
        ref={canvasRef}
        className="celestial-canvas"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          display: fallbackMode ? 'none' : 'block',
        }}
      />

      {/* Loading screen */}
      {!isLoaded && !fallbackMode && (
        <LoadingScreen
          isLoading={!isLoaded}
          progress={loadingProgress}
          error={error}
          onRetry={handleRetry}
          message="Loading celestial scene..."
        />
      )}

      {/* Context loss indicator */}
      {contextLost && isLoaded && (
        <div className="context-loss-overlay">
          <div className="context-loss-message">
            <h3>WebGL context lost</h3>
            <p>Attempting to restore...</p>
            <button onClick={handleRetry}>Restore Manually</button>
          </div>
        </div>
      )}

      {/* Fallback content when WebGL not supported */}
      {fallbackMode && (
        <div className="fallback-content">
          {fallbackContent || (
            <div className="fallback-message">
              <h3>3D Visualization Not Available</h3>
              <p>Your device does not support WebGL, which is required for the 3D celestial visualization.</p>
              <p>Please try using a different browser or device.</p>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .context-loss-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background-color: rgba(0, 0, 0, 0.7);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 100;
        }

        .context-loss-message {
          background-color: rgba(30, 41, 59, 0.8);
          border-radius: 8px;
          padding: 20px;
          max-width: 400px;
          text-align: center;
          color: white;
        }

        .context-loss-message h3 {
          margin-top: 0;
          color: #f87171;
        }

        .context-loss-message button {
          background: linear-gradient(90deg, #3b82f6, #8b5cf6);
          border: none;
          color: white;
          padding: 10px 20px;
          border-radius: 4px;
          cursor: pointer;
          margin-top: 10px;
          font-weight: 500;
        }

        .fallback-content {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          display: flex;
          justify-content: center;
          align-items: center;
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        }

        .fallback-message {
          background-color: rgba(30, 41, 59, 0.8);
          border-radius: 8px;
          padding: 20px;
          max-width: 400px;
          text-align: center;
          color: white;
        }

        .fallback-message h3 {
          margin-top: 0;
          color: #60a5fa;
        }
      `}</style>
    </>
  );
};

CelestialCanvas.propTypes = {
  enableRotation: PropTypes.bool,
  backgroundColor: PropTypes.number,
  particleCount: PropTypes.number,
  onReady: PropTypes.func,
  onError: PropTypes.func,
  fallbackContent: PropTypes.node
};

export default CelestialCanvas;
