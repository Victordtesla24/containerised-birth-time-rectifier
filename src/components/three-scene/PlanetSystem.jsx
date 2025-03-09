import React, { useRef, useState, useEffect, useMemo, useCallback, Suspense } from 'react';
import { useFrame } from '@react-three/fiber';
import { useTexture, Float, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { useQuality } from './core/QualityContext';
import { Vector3, Quaternion, Matrix4 } from 'three';
import dynamic from 'next/dynamic';
import textureManager from './utils/TextureManager';

// Simple error boundary component for graceful fallbacks
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Caught error in ErrorBoundary:", error);
    console.error("Component stack:", errorInfo.componentStack);
  }

  render() {
    if (this.state.hasError) {
      // Return fallback UI or null
      return this.props.fallback || null;
    }
    return this.props.children;
  }
}

// Import postprocessing components dynamically with SSR disabled and error handling
const DynamicEffectComposer = dynamic(
  () => import('@react-three/postprocessing')
    .then(mod => {
      if (!mod || !mod.EffectComposer) {
        console.warn('EffectComposer module not fully loaded');
        throw new Error('EffectComposer unavailable');
      }
      return mod.EffectComposer;
    })
    .catch(err => {
      console.error('Failed to load EffectComposer:', err);
      return () => null; // Return empty component on error
    }),
  { ssr: false, suspense: true }
);

const DynamicBloom = dynamic(
  () => import('@react-three/postprocessing')
    .then(mod => {
      if (!mod || !mod.Bloom) {
        console.warn('Bloom module not fully loaded');
        throw new Error('Bloom unavailable');
      }
      return mod.Bloom;
    })
    .catch(err => {
      console.error('Failed to load Bloom:', err);
      return () => null; // Return empty component on error
    }),
  { ssr: false, suspense: true }
);

// Add a utility function for Keplerian orbital mechanics
const calculateKeplerianOrbit = (semiMajorAxis, eccentricity, inclination, longitudeOfAscendingNode, argumentOfPeriapsis, meanAnomaly, centralMass = 1) => {
  // Convert angles from degrees to radians
  inclination = inclination * Math.PI / 180;
  longitudeOfAscendingNode = longitudeOfAscendingNode * Math.PI / 180;
  argumentOfPeriapsis = argumentOfPeriapsis * Math.PI / 180;

  // Calculate eccentric anomaly from mean anomaly using Newton-Raphson method
  let E = meanAnomaly; // Initial guess
  const maxIterations = 10;
  for (let i = 0; i < maxIterations; i++) {
    const deltaE = (E - eccentricity * Math.sin(E) - meanAnomaly) / (1 - eccentricity * Math.cos(E));
    E -= deltaE;
    if (Math.abs(deltaE) < 1e-6) break;
  }

  // Calculate position in orbital plane
  const x = semiMajorAxis * (Math.cos(E) - eccentricity);
  const y = semiMajorAxis * Math.sqrt(1 - eccentricity * eccentricity) * Math.sin(E);

  // Create rotation matrices for orbital orientation
  const rotMatrix = new Matrix4();

  // Rotate by argument of periapsis around Z axis
  const rotPeri = new Matrix4().makeRotationZ(argumentOfPeriapsis);
  rotMatrix.multiply(rotPeri);

  // Rotate by inclination around X axis
  const rotInc = new Matrix4().makeRotationX(inclination);
  rotMatrix.multiply(rotInc);

  // Rotate by longitude of ascending node around Z axis
  const rotNode = new Matrix4().makeRotationZ(longitudeOfAscendingNode);
  rotMatrix.multiply(rotNode);

  // Apply rotation to position
  const position = new Vector3(x, y, 0);
  position.applyMatrix4(rotMatrix);

  return position;
};

// Optimized planet component with LOD and enhanced rendering
const Planet = ({
  position,
  size,
  textureUrl,
  normalMapUrl = null,
  bumpMapUrl = null,
  specularMapUrl = null,
  // Keplerian orbital elements
  semiMajorAxis = 30,       // Semi-major axis in AU
  eccentricity = 0.0167,    // Orbital eccentricity
  inclination = 0,          // Inclination in degrees
  ascendingNode = 0,        // Longitude of ascending node in degrees
  argOfPeriapsis = 0,       // Argument of periapsis in degrees
  orbitalPeriod = 365.25,   // Orbital period in Earth days
  rotationPeriod = 24,      // Rotation period in hours
  axialTilt = 23.44,        // Axial tilt in degrees
  glowColor = '#4060ff',
  glowIntensity = 0.6,
  ringTexture = null,
  ringSize = [0, 0],
  atmosphereColor = null,
  mousePosition
}) => {
  // Get quality settings from context to optimize rendering
  const { qualityLevel } = useQuality();

  // Convert to Three.js units and time scales with slower, more natural timing
  const scaledSemiMajorAxis = semiMajorAxis * 5; // Scale for visualization
  const scaledOrbitalPeriod = orbitalPeriod * 0.00005; // Slower orbital speed (half the original)
  const scaledRotationPeriod = rotationPeriod * 0.005; // Slower rotation (half the original)

  // Refs for the planet and its orbit
  const planetRef = useRef();
  const orbitRef = useRef();
  const materialRef = useRef();
  const timeRef = useRef(Math.random() * 1000); // Random start time for variation

  // Adaptive geometry detail based on quality level and size
  const sphereDetail = useMemo(() => {
    // Base detail level on quality setting
    let baseDetail = qualityLevel === 'low' ? 32 :
                    qualityLevel === 'medium' ? 48 : 64;

    // Adjust detail based on planet size (smaller planets need fewer polygons)
    const sizeScale = Math.min(1, Math.max(0.5, size / 2.0));
    return Math.max(16, Math.round(baseDetail * sizeScale));
  }, [qualityLevel, size]);

  // Create a fallback texture
  const createFallbackTexture = useCallback((color = '#6090FF') => {
    const canvas = document.createElement('canvas');
    canvas.width = 2;
    canvas.height = 2;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, 2, 2);
    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    return texture;
  }, []);

  // Fallback textures
  const fallbackMap = useMemo(() => createFallbackTexture('#7A5C3D'), [createFallbackTexture]);
  const fallbackNormalMap = useMemo(() => createFallbackTexture('#8080FF'), [createFallbackTexture]);
  const fallbackBumpMap = useMemo(() => createFallbackTexture('#808080'), [createFallbackTexture]);
  const fallbackSpecularMap = useMemo(() => createFallbackTexture('#FFFFFF'), [createFallbackTexture]);

  // Create state hooks for textures
  const [diffuseMap, setDiffuseMap] = useState(fallbackMap);
  const [normalMap, setNormalMap] = useState(fallbackNormalMap);
  const [bumpMap, setBumpMap] = useState(fallbackBumpMap);
  const [specularMap, setSpecularMap] = useState(fallbackSpecularMap);

  // Load textures using THREE.TextureLoader with proper error handling
  useEffect(() => {
    // Create texture loader with error handling
    const textureLoader = new THREE.TextureLoader();
    textureLoader.crossOrigin = '';

    // Set up error handling and loading for each texture
    const loadTexture = (url, fallback, setTexture) => {
      if (!url) {
        setTexture(fallback);
        return;
      }

      try {
        textureLoader.load(
          url,
          // Success callback
          (texture) => {
            texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
            texture.encoding = THREE.sRGBEncoding;

            // Apply anisotropic filtering based on quality level
            const anisotropy = qualityLevel === 'low' ? 1 :
                              qualityLevel === 'medium' ? 4 : 16;
            texture.anisotropy = anisotropy;

            // Generate mipmaps based on quality
            texture.generateMipmaps = qualityLevel !== 'low';

            // Set appropriate filter modes based on quality
            if (qualityLevel === 'low') {
              texture.minFilter = THREE.LinearFilter;
              texture.magFilter = THREE.LinearFilter;
            } else {
              texture.minFilter = THREE.LinearMipmapLinearFilter;
              texture.magFilter = THREE.LinearFilter;
            }

            setTexture(texture);
          },
          // Progress callback
          undefined,
          // Error callback
          (error) => {
            console.warn(`Error loading texture ${url}:`, error);
            setTexture(fallback); // Use fallback texture on error
          }
        );
      } catch (err) {
        console.error(`Exception while loading texture ${url}:`, err);
        setTexture(fallback); // Use fallback texture on exception
      }
    };

    // Load all textures with proper error handling
    loadTexture(textureUrl, fallbackMap, setDiffuseMap);

    // Only load normal/bump maps on medium or higher quality
    if (qualityLevel !== 'low') {
      loadTexture(normalMapUrl, fallbackNormalMap, setNormalMap);
      loadTexture(bumpMapUrl, fallbackBumpMap, setBumpMap);
    }
    loadTexture(specularMapUrl, fallbackSpecularMap, setSpecularMap);

    // Cleanup function
    return () => {
      // No need to dispose of fallback textures as they're shared
    };
  }, [textureUrl, normalMapUrl, bumpMapUrl, specularMapUrl,
      fallbackMap, fallbackNormalMap, fallbackBumpMap, fallbackSpecularMap, qualityLevel]);

  // Combine all textures into a single object for ease of use
  const textures = useMemo(() => ({
    map: diffuseMap,
    normalMap: qualityLevel !== 'low' ? normalMap : null,
    bumpMap: qualityLevel !== 'low' ? bumpMap : null,
    specularMap: specularMap
  }), [diffuseMap, normalMap, bumpMap, specularMap, qualityLevel]);

  // Proper texture optimization
  useEffect(() => {
    Object.values(textures).forEach(texture => {
      if (texture) {
        // Normal maps should use linear encoding
        if (texture === normalMap) {
          texture.encoding = THREE.LinearEncoding;
        }
      }
    });

    // Return cleanup function
    return () => {
      // No need to dispose textures here as they're managed by state
    };
  }, [textures, normalMap]);

  // Adaptive orbit detail based on quality
  const orbitSegments = useMemo(() => {
    return qualityLevel === 'low' ? 64 :
           qualityLevel === 'medium' ? 96 : 128;
  }, [qualityLevel]);

  // Create points for elliptical orbit visualization with adaptive detail
  const orbitPoints = useMemo(() => {
    const points = [];

    for (let i = 0; i < orbitSegments; i++) {
      const meanAnomaly = (i / orbitSegments) * Math.PI * 2;
      const position = calculateKeplerianOrbit(
        scaledSemiMajorAxis,
        eccentricity,
        inclination,
        ascendingNode,
        argOfPeriapsis,
        meanAnomaly
      );
      points.push(position);
    }

    // Close the loop
    points.push(points[0].clone());

    return points;
  }, [scaledSemiMajorAxis, eccentricity, inclination, ascendingNode, argOfPeriapsis, orbitSegments]);

  // Animate planet using physically accurate orbital mechanics with performance optimizations
  useFrame((state, delta) => {
    if (planetRef.current) {
      // Update time reference
      timeRef.current += delta;

      // Calculate orbital position based on time
      const meanAnomaly = (timeRef.current / scaledOrbitalPeriod) % (Math.PI * 2);
      const position = calculateKeplerianOrbit(
        scaledSemiMajorAxis,
        eccentricity,
        inclination,
        ascendingNode,
        argOfPeriapsis,
        meanAnomaly
      );

      // Update planet position
      planetRef.current.position.set(position.x, position.y, position.z);

      // Update planet rotation with proper axial tilt
      const rotationQuat = new Quaternion().setFromAxisAngle(
        new Vector3(0, 0, 1),
        axialTilt * Math.PI / 180
      );
      planetRef.current.quaternion.copy(rotationQuat);

      // Apply rotation around tilted axis
      planetRef.current.rotateOnAxis(
        new Vector3(0, 1, 0),
        delta / scaledRotationPeriod
      );

      // Only apply subtle wobble on high quality settings
      if (qualityLevel !== 'low') {
        const wobbleX = Math.sin(timeRef.current * 0.3) * 0.01;
        const wobbleY = Math.cos(timeRef.current * 0.5) * 0.01;
        planetRef.current.rotation.x += wobbleX;
        planetRef.current.rotation.z += wobbleY;
      }

      // Interactive parallax effect with mouse position - enhanced effect
      if (mousePosition) {
        const parallaxFactor = qualityLevel === 'low' ? 0.00005 :
                              qualityLevel === 'medium' ? 0.0001 : 0.00015;
        const targetX = mousePosition.x * parallaxFactor;
        const targetY = mousePosition.y * parallaxFactor;
        planetRef.current.position.x += targetX;
        planetRef.current.position.y += targetY;
      }
    }
  });

  // Enhanced atmosphere rendering with improved visual quality
  const atmosphereOpacity = useMemo(() => {
    return qualityLevel === 'low' ? 0.15 :
           qualityLevel === 'medium' ? 0.2 : 0.25;
  }, [qualityLevel]);

  // Only render the orbit line for medium and high quality to improve performance
  const showOrbit = qualityLevel !== 'low';

  return (
    <group>
      {/* Elliptical orbit path - only shown on medium+ quality */}
      {showOrbit && (
        <line ref={orbitRef}>
          <bufferGeometry attach="geometry">
            <bufferAttribute
              attachObject={['attributes', 'position']}
              array={new Float32Array(orbitPoints.flatMap(p => [p.x, p.y, p.z]))}
              count={orbitPoints.length}
              itemSize={3}
            />
          </bufferGeometry>
          <lineBasicMaterial
            attach="material"
            color="#334466"
            opacity={0.3}
            transparent
            blending={THREE.AdditiveBlending}
          />
        </line>
      )}

      {/* Planet mesh with physically-based materials */}
      <group ref={planetRef} position={position}>
        <mesh castShadow receiveShadow>
          <sphereGeometry args={[size, sphereDetail, sphereDetail]} />
          <meshPhysicalMaterial
            ref={materialRef}
            map={textures.map}
            normalMap={textures.normalMap || null}
            bumpMap={textures.bumpMap || null}
            roughnessMap={textures.specularMap || null}
            roughness={0.7}
            metalness={0.2}
            clearcoat={0.15}
            clearcoatRoughness={0.3}
          />
        </mesh>

        {/* Atmosphere if specified - enhanced visual quality */}
        {atmosphereColor && (
          <mesh>
            <sphereGeometry args={[size * 1.05, sphereDetail/2, sphereDetail/2]} />
            <meshBasicMaterial
              color={atmosphereColor}
              transparent
              opacity={atmosphereOpacity}
              side={THREE.BackSide}
              blending={THREE.AdditiveBlending}
              depthWrite={false}
            />
          </mesh>
        )}

        {/* Planet rings if specified - improved detail */}
        {ringTexture && ringSize[0] > 0 && (
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <ringGeometry args={[
              ringSize[0] * size,
              ringSize[1] * size,
              qualityLevel === 'low' ? 32 : qualityLevel === 'medium' ? 64 : 96
            ]} />
            <meshBasicMaterial
              map={textures.specularMap}
              transparent
              opacity={0.9}
              side={THREE.DoubleSide}
            />
          </mesh>
        )}

        {/* Glow effect with improved quality */}
        <mesh>
          <sphereGeometry args={[
            size * 1.1,
            qualityLevel === 'low' ? 16 : qualityLevel === 'medium' ? 24 : 32
          ]} />
          <meshBasicMaterial
            color={glowColor}
            transparent
            opacity={glowIntensity}
            side={THREE.BackSide}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
      </group>
    </group>
  );
};

// Special Saturn component with realistic rings
const SaturnWithRings = ({
  position,
  size,
  textureUrl,
  orbitRadius,
  orbitSpeed,
  rotationSpeed,
  tilt = 0,
  glowColor = '#d0b080',
  glowIntensity = 0.6,
  ringColor = '#e0c080',
  ringOpacity = 0.8,
  mousePosition
}) => {
  const planetRef = useRef();
  const ringRef = useRef();
  const orbitRef = useRef();
  const glowRef = useRef();
  const time = useRef(Math.random() * 100);

  // Create fallback texture
  const createFallbackTexture = useCallback((color = '#d0b080') => {
    const canvas = document.createElement('canvas');
    canvas.width = 2;
    canvas.height = 2;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, 2, 2);
    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    return texture;
  }, []);

  // Create a fallback texture for Saturn
  const fallbackTexture = useMemo(() => createFallbackTexture('#d0b080'), [createFallbackTexture]);

  // Create state hook for texture
  const [saturnTexture, setSaturnTexture] = useState(fallbackTexture);

  // Load texture using THREE.TextureLoader with proper error handling
  useEffect(() => {
    if (!textureUrl) {
      console.warn('No texture URL provided for Saturn');
      setSaturnTexture(fallbackTexture);
      return;
    }

    // Create texture loader with error handling
    const textureLoader = new THREE.TextureLoader();
    textureLoader.crossOrigin = '';

    // Cancel variable to prevent state updates after unmount
    let isMounted = true;

    // Load the texture with error handling
    try {
      console.log(`Loading Saturn texture from: ${textureUrl}`);

      textureLoader.load(
        textureUrl,
        // Success callback
        (texture) => {
          if (!isMounted) return;

          texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
          texture.anisotropy = 16;
          texture.encoding = THREE.sRGBEncoding;
          setSaturnTexture(texture);
          console.log(`Successfully loaded: ${textureUrl}`);
        },
        // Progress callback
        undefined,
        // Error callback
        (error) => {
          if (!isMounted) return;

          console.warn(`Error loading texture ${textureUrl}:`, error);
          setSaturnTexture(fallbackTexture); // Use fallback texture on error
        }
      );
    } catch (err) {
      if (!isMounted) return;

      console.error(`Exception while loading texture ${textureUrl}:`, err);
      setSaturnTexture(fallbackTexture); // Use fallback texture on exception
    }

    // Cleanup function
    return () => {
      isMounted = false;
    };
  }, [textureUrl, fallbackTexture]);

  // Create enhanced ring texture
  const ringTexture = useMemo(() => {
    // Create a canvas to generate the ring texture
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 128;
    const context = canvas.getContext('2d');

    // Create ring gradient with more realistic colors and bands
    const gradient = context.createLinearGradient(0, 0, 1024, 0);

    // Add more color stops for rings with gaps and varying colors
    gradient.addColorStop(0.0, 'rgba(160, 140, 105, 0.1)');
    gradient.addColorStop(0.2, 'rgba(200, 180, 120, 0.7)');
    gradient.addColorStop(0.3, 'rgba(180, 160, 100, 0.4)');
    gradient.addColorStop(0.4, 'rgba(210, 190, 130, 0.8)');
    gradient.addColorStop(0.5, 'rgba(160, 140, 90, 0.3)');  // Cassini Division (gap)
    gradient.addColorStop(0.6, 'rgba(180, 160, 100, 0.7)');
    gradient.addColorStop(0.7, 'rgba(210, 190, 130, 0.6)');
    gradient.addColorStop(0.8, 'rgba(200, 180, 120, 0.7)');
    gradient.addColorStop(0.9, 'rgba(180, 160, 100, 0.3)');
    gradient.addColorStop(1.0, 'rgba(160, 140, 90, 0.05)');

    context.fillStyle = gradient;
    context.fillRect(0, 0, 1024, 128);

    // Add noise to the rings for more detail and particle simulation
    for (let i = 0; i < 15000; i++) {
      const x = Math.random() * 1024;
      const y = Math.random() * 128;
      const radius = Math.random() * 1 + 0.5;

      // Vary particle brightness and size based on position in ring
      const ringPosition = x / 1024;
      let alpha = Math.random() * 0.4;

      // Make particles in the Cassini Division (gap) more sparse
      if (ringPosition > 0.45 && ringPosition < 0.55) {
        if (Math.random() > 0.3) continue;
        alpha *= 0.5;
      }

      context.beginPath();
      context.arc(x, y, radius, 0, Math.PI * 2);
      context.fillStyle = `rgba(255, 255, 255, ${alpha})`;
      context.fill();
    }

    // Create three.js texture
    const ringTex = new THREE.CanvasTexture(canvas);
    ringTex.wrapS = THREE.RepeatWrapping;
    ringTex.repeat.x = 3;
    ringTex.anisotropy = 16;

    return ringTex;
  }, []);

  // Calculate planet position on orbit with realistic physics
  useFrame((state, delta) => {
    if (planetRef.current) {
      // Update time for animation
      time.current += delta * orbitSpeed;

      // Calculate orbital position with slight eccentricity
      const eccentricity = 0.06;
      const angle = time.current;
      const distance = orbitRadius * (1 - eccentricity * Math.cos(angle));
      const x = Math.cos(angle) * distance;
      const z = Math.sin(angle) * distance * 0.92; // Slightly elliptical orbit

      // Update planet position on orbit
      planetRef.current.position.x = x;
      planetRef.current.position.z = z;

      // Rotate planet around its axis with realistic wobble
      planetRef.current.rotation.y += delta * rotationSpeed;
      planetRef.current.rotation.x = Math.sin(time.current * 0.1) * 0.01 + tilt;

      // Ring follows planet with proper physics
      if (ringRef.current) {
        ringRef.current.position.x = x;
        ringRef.current.position.z = z;

        // Slow rotation of rings
        ringRef.current.rotation.z += delta * rotationSpeed * 0.01;
      }

      // Glow follows planet
      if (glowRef.current) {
        glowRef.current.position.x = x;
        glowRef.current.position.z = z;
      }

      // Add subtle movement based on mouse position for interactive parallax
      if (mousePosition) {
        const parallaxFactor = 0.001;
        planetRef.current.position.x += mousePosition.x * parallaxFactor;
        planetRef.current.position.y += mousePosition.y * parallaxFactor;

        if (ringRef.current) {
          ringRef.current.position.x += mousePosition.x * parallaxFactor;
          ringRef.current.position.y += mousePosition.y * parallaxFactor;
        }

        if (glowRef.current) {
          glowRef.current.position.x += mousePosition.x * parallaxFactor;
          glowRef.current.position.y += mousePosition.y * parallaxFactor;
        }
      }
    }
  });

  return (
    <group>
      {/* Draw orbit path */}
      <line ref={orbitRef}>
        <bufferGeometry attach="geometry" />
        <lineBasicMaterial attach="material" color="#aaaaaa" transparent opacity={0.3} />
      </line>

      {/* Subtle glow effect */}
      <sprite ref={glowRef}>
        <spriteMaterial
          attach="material"
          map={null}
          color={glowColor}
          transparent
          opacity={glowIntensity}
          blending={THREE.AdditiveBlending}
        />
      </sprite>

      {/* Saturn planet mesh */}
      <mesh ref={planetRef} castShadow receiveShadow>
        <sphereGeometry args={[size, 64, 48]} />
        <meshStandardMaterial
          map={saturnTexture}
          bumpScale={0.05}
          roughness={0.8}
          metalness={0.1}
        />
      </mesh>

      {/* Saturn rings */}
      <mesh ref={ringRef} rotation={[Math.PI / 2 + tilt, 0, 0]} receiveShadow>
        <ringGeometry args={[size * 1.4, size * 2.5, 128]} />
        <meshStandardMaterial
          map={ringTexture}
          color={ringColor}
          transparent
          opacity={ringOpacity}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
};

// Scientific solar constants
const SOLAR_RADIUS = 695700; // km
const SOLAR_ROTATION_PERIOD = 25.38; // days at equator
const SOLAR_SURFACE_TEMP = 5778; // K
const SOLAR_TEMPERATURE_TO_RGB = {
  4000: new THREE.Color('#f7e2c4'),
  5000: new THREE.Color('#fff4e8'),
  6000: new THREE.Color('#ffffff'),
  7000: new THREE.Color('#f8f8ff'),
  9000: new THREE.Color('#e6ebff')
};

// Scientifically enhanced sun with accurate solar phenomena
const EnhancedSun = ({ size, mousePosition, qualityLevel = 'high' }) => {
  const sunRef = useRef();
  const coronaRef = useRef();
  const chromosphereRef = useRef();
  const photosphereRef = useRef();
  const prominencesRef = useRef();
  const time = useRef(0);
  const [effectsReady, setEffectsReady] = useState(false);

  // Check if postprocessing modules are available - more robust checking
  useEffect(() => {
    const checkPostprocessingAvailable = async () => {
      try {
        // Safely check if modules can be loaded
        const postprocessingModule = await import('@react-three/postprocessing');

        if (postprocessingModule &&
            typeof postprocessingModule.EffectComposer === 'function' &&
            typeof postprocessingModule.Bloom === 'function') {
          console.log('Postprocessing modules successfully loaded');
          setEffectsReady(true);
        } else {
          console.warn('Postprocessing modules not completely available');
          setEffectsReady(false);
        }
      } catch (error) {
        console.error('Error checking postprocessing availability:', error);
        setEffectsReady(false);
      }
    };

    const checkTimeout = setTimeout(() => {
      // Only check if not low quality (where we don't use effects)
      if (qualityLevel !== 'low') {
        checkPostprocessingAvailable();
      } else {
        setEffectsReady(false);
      }
    }, 100); // Small delay to ensure component is fully mounted

    return () => clearTimeout(checkTimeout);
  }, [qualityLevel]);

  // State to hold textures
  const [sunTextures, setSunTextures] = useState({
    baseTexture: null,
    chromaticTexture: null,
    normalMap: null,
    spotsTexture: null
  });

  // Configure texture scale based on quality
  const textureScale = qualityLevel === 'low' ? '2k' :
                      qualityLevel === 'medium' ? '4k' : '8k';

  // Load textures using our advanced TextureManager
  useEffect(() => {
    const loadSunTextures = async () => {
      try {
        // Try alternative texture paths
        const texturePaths = [
          `/images/planets/sun/sun_surface.jpg`,    // Try main path first
          `/images/sun/surface.jpg`,                // Fallback 1
          `/textures/sun/sun_surface_${textureScale}.jpg` // Fallback 2
        ];

        const chromaticPaths = [
          `/images/planets/sun/sun_chromatic.jpg`,
          `/images/sun/chromatic.jpg`,
          `/textures/sun/sun_chromatic_${textureScale}.jpg`
        ];

        const normalPaths = [
          `/images/planets/sun/sun_normal.jpg`,
          `/images/sun/normal.jpg`,
          `/textures/sun/sun_normal_${textureScale}.jpg`
        ];

        const spotsPaths = [
          `/images/planets/sun/sun_spots.jpg`,
          `/images/sun/spots.jpg`,
          `/textures/sun/sun_spots_${textureScale}.jpg`
        ];

        // Create appropriate texture quality settings based on quality level
        const anisotropy = qualityLevel === 'low' ? 1 :
                          qualityLevel === 'medium' ? 4 : 8;

        const textureSize = qualityLevel === 'low' ? 64 :
                           qualityLevel === 'medium' ? 128 : 256;

        // Create fallback textures first
        const fallbackBase = textureManager.createFallbackTexture('#FF9D00', textureSize);
        const fallbackChromatic = textureManager.createFallbackTexture('#FFFF00', textureSize);
        const fallbackNormal = textureManager.createFallbackTexture('#8080FF', textureSize);
        const fallbackSpots = textureManager.createFallbackTexture('#803000', textureSize);

        // Set initial fallback textures
        setSunTextures({
          baseTexture: fallbackBase,
          chromaticTexture: fallbackChromatic,
          normalMap: fallbackNormal,
          spotsTexture: fallbackSpots
        });

        // Try to load real textures with fallbacks
        let baseTexture, chromaticTexture, normalMap, spotsTexture;

        // Try each path for base texture
        for (let path of texturePaths) {
          try {
            baseTexture = await textureManager.loadTexture(path, {
              textureType: 'sun',
              fallbackColor: '#FF9D00',
              quality: qualityLevel,
              anisotropy,
              size: textureSize,
              detail: qualityLevel === 'low' ? 0.5 : 1.0,
              cacheKey: 'sun-surface'
            });
            if (baseTexture !== fallbackBase) break; // If we got a real texture, stop trying
          } catch (e) {
            console.log(`Failed to load texture from ${path}, trying next...`);
          }
        }

        // Try each path for chromatic texture
        for (let path of chromaticPaths) {
          try {
            chromaticTexture = await textureManager.loadTexture(path, {
              textureType: 'sun',
              fallbackColor: '#FFFF00',
              quality: qualityLevel,
              anisotropy,
              size: textureSize,
              detail: qualityLevel === 'low' ? 0.5 : 1.0,
              cacheKey: 'sun-chromatic'
            });
            if (chromaticTexture !== fallbackChromatic) break;
          } catch (e) {
            console.log(`Failed to load texture from ${path}, trying next...`);
          }
        }

        // Try each path for normal map
        for (let path of normalPaths) {
          try {
            normalMap = await textureManager.loadTexture(path, {
              textureType: 'normal',
              fallbackColor: '#8080FF',
              quality: qualityLevel,
              anisotropy,
              size: textureSize,
              detail: qualityLevel === 'low' ? 0.5 : 1.0,
              isNormalMap: true,
              cacheKey: 'sun-normal'
            });
            if (normalMap !== fallbackNormal) break;
          } catch (e) {
            console.log(`Failed to load texture from ${path}, trying next...`);
          }
        }

        // Try each path for spots texture
        for (let path of spotsPaths) {
          try {
            spotsTexture = await textureManager.loadTexture(path, {
              textureType: 'basic',
              fallbackColor: '#803000',
              quality: qualityLevel,
              anisotropy,
              size: textureSize,
              detail: qualityLevel === 'low' ? 0.5 : 1.0,
              cacheKey: 'sun-spots'
            });
            if (spotsTexture !== fallbackSpots) break;
          } catch (e) {
            console.log(`Failed to load texture from ${path}, trying next...`);
          }
        }

        // Update state with loaded textures (using fallbacks if needed)
        setSunTextures({
          baseTexture: baseTexture || fallbackBase,
          chromaticTexture: chromaticTexture || fallbackChromatic,
          normalMap: normalMap || fallbackNormal,
          spotsTexture: spotsTexture || fallbackSpots
        });

        console.log("Sun textures loaded (or fallbacks created)");
      } catch (error) {
        console.error("Error loading sun textures:", error);
      }
    };

    // Load textures
    loadSunTextures();

    // Cleanup function
    return () => {
      // Clean up textures when component unmounts
      textureManager.disposeTexture('sun-surface');
      textureManager.disposeTexture('sun-chromatic');
      textureManager.disposeTexture('sun-normal');
      textureManager.disposeTexture('sun-spots');
    };
  }, [qualityLevel, textureScale]);

  // Calculate sun resolution based on quality
  const sunResolution = qualityLevel === 'low' ? 64 :
                      qualityLevel === 'medium' ? 128 :
                      qualityLevel === 'high' ? 192 : 256;

  // Detail factor for scientific accuracy
  const detailFactor = qualityLevel === 'low' ? 0.5 :
                      qualityLevel === 'medium' ? 0.75 : 1.0;

  // Apply scientific solar rotation (differential by latitude)
  const sunRotationPeriod = SOLAR_ROTATION_PERIOD; // Days

  // Scientifically accurate photosphere material (the visible surface)
  const photosphereMaterial = useMemo(() => {
    // Create default textures for the shader
    const defaultTexture = new THREE.Texture();

    return new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        baseTexture: { value: sunTextures.baseTexture || defaultTexture },
        chromaticTexture: { value: sunTextures.chromaticTexture || defaultTexture },
        normalMap: { value: sunTextures.normalMap || defaultTexture },
        spotsTexture: { value: sunTextures.spotsTexture || defaultTexture },
        sunRadius: { value: size },
        detailLevel: { value: detailFactor },
        rotationPeriod: { value: sunRotationPeriod }
      },
      vertexShader: `
        varying vec2 vUv;
        varying vec3 vNormal;
        varying vec3 vViewPosition;

        void main() {
          vUv = uv;
          vNormal = normalize(normalMatrix * normal);
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          vViewPosition = -mvPosition.xyz;
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform float time;
        uniform sampler2D baseTexture;
        uniform sampler2D chromaticTexture;
        uniform sampler2D normalMap;
        uniform sampler2D spotsTexture;
        uniform float sunRadius;
        uniform float detailLevel;
        uniform float rotationPeriod;

        varying vec2 vUv;
        varying vec3 vNormal;
        varying vec3 vViewPosition;

        // Scientific sun features

        // Color temperature conversion (approximation of blackbody radiation)
        vec3 tempToRGB(float temp) {
          // Approximated blackbody radiation model
          float t = temp / 100.0;
          vec3 color;

          if (t <= 66.0) {
            color.r = 1.0;
            color.g = 0.39008157876901960784 * log(t) - 0.63184144378862745098;
          } else {
            color.r = 1.29293618606274509804 * pow(t - 60.0, -0.1332047592);
            color.g = 1.12989086089529411765 * pow(t - 60.0, -0.0755148492);
          }

          if (t >= 66.0) {
            color.b = 1.0;
          } else if (t <= 19.0) {
            color.b = 0.0;
          } else {
            color.b = 0.54320678911019607843 * log(t - 10.0) - 1.19625408914;
          }

          return clamp(color, 0.0, 1.0);
        }

        // Scientifically accurate limb darkening based on Eddington approximation
        float limbDarkening(float cosTheta) {
          // Eddington approximation for solar limb darkening
          return 0.5 + 0.5 * cosTheta;
        }

        // Differential rotation by latitude (scientific sun feature)
        vec2 differentialRotation(vec2 uv, float time) {
          // Convert UV to spherical coordinates
          float lat = (uv.y - 0.5) * 3.14159; // -pi/2 to pi/2

          // 25 days at equator, up to 35 days at poles (scientifically accurate)
          float period = rotationPeriod * (1.0 + 0.2 * abs(sin(lat)));

          // Calculate rotation angle
          float angle = time / (period * 24.0 * 60.0 * 60.0) * 2.0 * 3.14159;

          // Rotate UV
          vec2 rotated;
          rotated.x = uv.x + angle / (2.0 * 3.14159);
          rotated.y = uv.y;

          // Wrap around
          rotated.x = fract(rotated.x);

          return rotated;
        }

        void main() {
          // Apply differential rotation to UVs
          vec2 rotatedUv = differentialRotation(vUv, time);

          // Sample textures with scientific differential rotation
          vec4 baseColor = texture2D(baseTexture, rotatedUv);
          vec4 chromaticColor = texture2D(chromaticTexture, rotatedUv);
          vec3 normalValue = texture2D(normalMap, rotatedUv).rgb * 2.0 - 1.0;
          float spots = texture2D(spotsTexture, rotatedUv).r;

          // Calculate view angle for limb darkening
          float cosTheta = dot(normalize(vViewPosition), vNormal);
          float limbEffect = limbDarkening(cosTheta);

          // Sunspots are cooler (3000-4500K vs 5778K surface)
          float localTemp = mix(5778.0, 4000.0, spots * 0.7);
          vec3 tempColor = tempToRGB(localTemp);

          // Chromatic aberration at edges (scientific dispersive effect)
          float edgeFactor = 1.0 - abs(cosTheta);
          vec3 finalColor = mix(baseColor.rgb, chromaticColor.rgb, edgeFactor * 0.5);

          // Apply temperature-based color and limb darkening
          finalColor *= tempColor * limbEffect;

          // Apply faculae (bright regions near sunspots) - scientific feature
          float faculae = max(0.0, spots - 0.3) * 2.0;
          finalColor += vec3(1.0, 0.7, 0.3) * faculae * 0.3;

          // Apply granulation detail (convection cells) based on detail level
          if (detailLevel > 0.5) {
            vec2 granuleUv = vUv * 50.0 * detailLevel;
            float granulation = fract(sin(dot(floor(granuleUv), vec2(12.9898, 78.233))) * 43758.5453);
            finalColor += (granulation - 0.5) * 0.05 * detailLevel;
          }

          gl_FragColor = vec4(finalColor, 1.0);
        }
      `,
      extensions: {
        derivatives: true
      }
    });
  }, [sunTextures, size, detailFactor, sunRotationPeriod]);

  // Scientifically accurate chromosphere material (the sun's lower atmosphere)
  const chromosphereMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        baseColor: { value: new THREE.Color('#ff4500') },
        edgeColor: { value: new THREE.Color('#ff7746') },
      },
      vertexShader: `
        varying vec2 vUv;
        varying vec3 vNormal;
        varying vec3 vViewPosition;

        void main() {
          vUv = uv;
          vNormal = normalize(normalMatrix * normal);
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          vViewPosition = -mvPosition.xyz;
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform float time;
        uniform vec3 baseColor;
        uniform vec3 edgeColor;

        varying vec2 vUv;
        varying vec3 vNormal;
        varying vec3 vViewPosition;

        // Fast simplex-like noise
        float noise(vec2 p) {
          return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
        }

        float mod289(float x){return x - floor(x * (1.0 / 289.0)) * 289.0;}
        vec4 mod289(vec4 x){return x - floor(x * (1.0 / 289.0)) * 289.0;}
        vec4 perm(vec4 x){return mod289(((x * 34.0) + 1.0) * x);}

        // Improved noise for more natural chromosphere movement
        float snoise(vec3 p){
          vec3 a = floor(p);
          vec3 d = p - a;
          d = d * d * (3.0 - 2.0 * d);

          vec4 b = a.xxyy + vec4(0.0, 1.0, 0.0, 1.0);
          vec4 k1 = perm(b.xyxy);
          vec4 k2 = perm(k1.xyxy + b.zzww);

          vec4 c = k2 + a.zzzz;
          vec4 k3 = perm(c);
          vec4 k4 = perm(c + 1.0);

          vec4 o1 = fract(k3 * (1.0 / 41.0));
          vec4 o2 = fract(k4 * (1.0 / 41.0));

          vec4 o3 = o2 * d.z + o1 * (1.0 - d.z);
          vec2 o4 = o3.yw * d.x + o3.xz * (1.0 - d.x);

          return o4.y * d.y + o4.x * (1.0 - d.y);
        }

        void main() {
          // Chromosphere is more visible at the edges (scientific)
          float viewFactor = pow(1.0 - abs(dot(normalize(vViewPosition), vNormal)), 2.0);

          // Dynamic spicule/filament generation (scientific solar feature)
          float n1 = snoise(vec3(vUv * 5.0, time * 0.1));
          float n2 = snoise(vec3(vUv * 10.0, time * 0.2 + 10.0));
          float n3 = snoise(vec3(vUv * 20.0, time * 0.05 + 20.0));

          // Combine noise for spicules
          float spicules = n1 * 0.5 + n2 * 0.3 + n3 * 0.2;

          // Enhance edges where spicules are more visible (scientific)
          float spiculeVisibility = viewFactor * (0.4 + spicules * 0.6);

          // Temperature gradients from base to edge (scientific)
          vec3 color = mix(baseColor, edgeColor, spicules);

          // Final opacity follows scientific visibility pattern of chromosphere
          float opacity = viewFactor * spiculeVisibility * 0.8;

          gl_FragColor = vec4(color, opacity);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.BackSide
    });
  }, []);

  // Create scientifically accurate corona material
  const coronaMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        innerColor: { value: new THREE.Color('#ffb366') },
        outerColor: { value: new THREE.Color('#86cdfc') }
      },
      vertexShader: `
        varying vec2 vUv;
        varying vec3 vNormal;
        varying vec3 vWorldPosition;

        void main() {
          vUv = uv;
          vNormal = normalize(normalMatrix * normal);
          vec4 worldPos = modelMatrix * vec4(position, 1.0);
          vWorldPosition = worldPos.xyz;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float time;
        uniform vec3 innerColor;
        uniform vec3 outerColor;

        varying vec2 vUv;
        varying vec3 vNormal;
        varying vec3 vWorldPosition;

        // Scientific coronal density function
        float coronalDensity(float r) {
          // Based on scientific models of coronal density fall-off
          // r is distance from sun center in solar radii
          return pow(r, -6.0);
        }

        float mod289(float x){return x - floor(x * (1.0 / 289.0)) * 289.0;}
        vec4 mod289(vec4 x){return x - floor(x * (1.0 / 289.0)) * 289.0;}
        vec4 perm(vec4 x){return mod289(((x * 34.0) + 1.0) * x);}

        // Improved noise for coronal features
        float snoise(vec3 p){
          vec3 a = floor(p);
          vec3 d = p - a;
          d = d * d * (3.0 - 2.0 * d);

          vec4 b = a.xxyy + vec4(0.0, 1.0, 0.0, 1.0);
          vec4 k1 = perm(b.xyxy);
          vec4 k2 = perm(k1.xyxy + b.zzww);

          vec4 c = k2 + a.zzzz;
          vec4 k3 = perm(c);
          vec4 k4 = perm(c + 1.0);

          vec4 o1 = fract(k3 * (1.0 / 41.0));
          vec4 o2 = fract(k4 * (1.0 / 41.0));

          vec4 o3 = o2 * d.z + o1 * (1.0 - d.z);
          vec2 o4 = o3.yw * d.x + o3.xz * (1.0 - d.x);

          return o4.y * d.y + o4.x * (1.0 - d.y);
        }

        void main() {
          // Calculate view ray for corona
          vec3 viewDirection = normalize(cameraPosition - vWorldPosition);
          float viewDot = abs(dot(vNormal, viewDirection));

          // Apply scientific Fresnel effect for corona
          float fresnel = pow(1.0 - viewDot, 4.0);

          // Distance from center in normalized units (1.0 = surface)
          float dist = length(vUv - vec2(0.5, 0.5)) * 2.0;

          // Scientific coronal density model
          float density = coronalDensity(max(1.0, dist));

          // Coronal magnetic field effects (scientifically based)
          float n1 = snoise(vec3(vUv * 2.0, time * 0.05));
          float n2 = snoise(vec3(vUv * 5.0, time * 0.1 + 10.0));

          // Combine for realistic coronal loops
          float coronalLoops = n1 * 0.6 + n2 * 0.4;

          // Modulate corona by magnetic activities
          float final = fresnel * density * (0.5 + coronalLoops * 0.5);

          // Scientific transition from inner to outer corona color
          vec3 color = mix(innerColor, outerColor, min(1.0, dist - 1.0));

          // Apply opacity based on scientific coronal models
          float opacity = final * 0.3 * (1.0 - smoothstep(0.0, 2.0, dist));

          gl_FragColor = vec4(color, opacity);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.BackSide
    });
  }, []);

  // Create solar prominence generator
  const createScientificProminence = (group, sunSize) => {
    // Scientific properties of solar prominences
    const baseRadius = sunSize * 0.98;
    const prominenceHeight = sunSize * (0.1 + Math.random() * 0.25); // 10-35% of sun radius (realistic)
    const filamentWidth = prominenceHeight * (0.03 + Math.random() * 0.02); // Scientific proportion

    // Random position on sun (scientific latitude distribution)
    // Prominences are more common at mid-latitudes (scientific)
    const latitudeBias = 0.3 + Math.random() * 0.4; // 30-70% from equator
    const latitude = (Math.random() > 0.5 ? 1 : -1) * latitudeBias * Math.PI/2;
    const longitude = Math.random() * Math.PI * 2;

    // Scientific prominence shape
    const points = [];
    const pointCount = 24;
    const arcSpan = (0.1 + Math.random() * 0.3) * Math.PI; // Scientific span of prominences

    // Create scientific arc shape
    for (let i = 0; i < pointCount; i++) {
      const t = i / (pointCount - 1);
      const angle = longitude + (t - 0.5) * arcSpan;

      // Scientific prominence height profile (loop shape)
      const heightProfile = Math.sin(t * Math.PI);
      const distance = baseRadius + heightProfile * prominenceHeight;

      // Calculate 3D position
      const x = Math.cos(angle) * Math.cos(latitude) * distance;
      const y = Math.sin(latitude) * distance;
      const z = Math.sin(angle) * Math.cos(latitude) * distance;

      points.push(new THREE.Vector3(x, y, z));
    }

    // Create scientific curve
    const curve = new THREE.CatmullRomCurve3(points);
    const geometry = new THREE.TubeGeometry(curve, 48, filamentWidth, 8, false);

    // Scientific prominences material (plasma at 60,000K)
    const material = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        baseColor: { value: new THREE.Color('#ff4500') }, // Scientific prominence color
      },
      vertexShader: `
        varying vec2 vUv;
        varying float vDistance;

        void main() {
          vUv = uv;
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          vDistance = -mvPosition.z;
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform float time;
        uniform vec3 baseColor;
        varying vec2 vUv;
        varying float vDistance;

        // Scientific plasma noise
        float noise(vec2 p) {
          return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
        }

        void main() {
          // Scientific plasma flow speed
          float timeScale = time * 2.0;

          // Multi-scale noise for realistic plasma dynamics
          float n1 = noise(vec2(vUv.x * 10.0 + timeScale * 0.05, vUv.y * 5.0));
          float n2 = noise(vec2(vUv.x * 20.0 - timeScale * 0.03, vUv.y * 15.0));

          // Combined plasma dynamics (scientific)
          float plasma = mix(n1, n2, 0.5);

          // Scientific gradient along prominence
          float gradient = smoothstep(0.0, 0.3, vUv.x) * smoothstep(1.0, 0.7, vUv.x);

          // Prominence color with plasma variation (scientific)
          vec3 color = baseColor + vec3(0.2, 0.1, 0.0) * plasma;

          // Prominence opacity based on scientific models
          float opacity = gradient * (0.7 + plasma * 0.3);

          gl_FragColor = vec4(color, opacity);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide
    });

    const prominence = new THREE.Mesh(geometry, material);
    group.add(prominence);
    return prominence;
  };

  // Initialize prominences with scientific distribution
  useEffect(() => {
    if (!prominencesRef.current) return;

    // Clear any existing prominences
    while (prominencesRef.current.children.length > 0) {
      const child = prominencesRef.current.children[0];
      prominencesRef.current.remove(child);
      if (child.geometry) child.geometry.dispose();
      if (child.material) child.material.dispose();
    }

    // Scientific number of prominences based on solar activity
    const prominence_count = qualityLevel === 'low' ? 2 :
                            qualityLevel === 'medium' ? 4 : 6;

    // Create scientifically distributed prominences
    for (let i = 0; i < prominence_count; i++) {
      createScientificProminence(prominencesRef.current, size);
    }

    return () => {
      // Clean up all prominences
      if (prominencesRef.current) {
        while (prominencesRef.current.children.length > 0) {
          const child = prominencesRef.current.children[0];
          prominencesRef.current.remove(child);
          if (child.geometry) child.geometry.dispose();
          if (child.material) child.material.dispose();
        }
      }
    };
  }, [size, qualityLevel]);

  // Update shader uniforms when textures change
  useEffect(() => {
    if (photosphereMaterial && photosphereMaterial.uniforms) {
      photosphereMaterial.uniforms.baseTexture.value = sunTextures.baseTexture;
      photosphereMaterial.uniforms.chromaticTexture.value = sunTextures.chromaticTexture;
      photosphereMaterial.uniforms.normalMap.value = sunTextures.normalMap;
      photosphereMaterial.uniforms.spotsTexture.value = sunTextures.spotsTexture;
    }
  }, [sunTextures, photosphereMaterial]);

  // Scientific solar animation
  useFrame((state, delta) => {
    // Accumulate time (slower on lower quality)
    const timeScale = qualityLevel === 'low' ? 0.2 :
                     qualityLevel === 'medium' ? 0.3 : 0.4;
    time.current += delta * timeScale;

    // Update all shader material time uniforms
    const materials = [photosphereMaterial, chromosphereMaterial, coronaMaterial];
    materials.forEach(material => {
      if (material && material.uniforms && material.uniforms.time) {
        material.uniforms.time.value = time.current;
      }
    });

    // Update prominence materials
    if (prominencesRef.current) {
      prominencesRef.current.children.forEach(prominence => {
        if (prominence.material && prominence.material.uniforms) {
          prominence.material.uniforms.time.value = time.current;
        }
      });
    }

    // Scientific differential rotation (sun rotates faster at equator)
    if (sunRef.current) {
      // Base rotation
      sunRef.current.rotation.y = time.current * 0.02;

      // Scientific oscillation (based on real solar dynamics)
      const oscX = Math.sin(time.current * 0.1) * 0.001;
      const oscZ = Math.cos(time.current * 0.15) * 0.001;
      sunRef.current.rotation.x = oscX;
      sunRef.current.rotation.z = oscZ;
    }

    // Smooth corona movement
      if (coronaRef.current) {
      coronaRef.current.rotation.y = time.current * 0.005;

      // Asymmetrical movement based on solar magnetic field (scientific)
      coronaRef.current.rotation.x = Math.sin(time.current * 0.1) * 0.01;
      coronaRef.current.rotation.z = Math.cos(time.current * 0.08) * 0.01;
    }

    // Apply mouse movement for parallax effect
    if (mousePosition && sunRef.current) {
      // Target parallax position
      const parallaxFactor = 0.0004;
      const targetX = mousePosition.x * parallaxFactor;
      const targetY = mousePosition.y * parallaxFactor;

      // Apply to all sun components with synchronized movement
      [sunRef, coronaRef, chromosphereRef, prominencesRef].forEach(ref => {
        if (ref.current) {
          // Smooth interpolation for natural feel
          ref.current.position.x += (targetX - ref.current.position.x) * 0.05;
          ref.current.position.y += (targetY - ref.current.position.y) * 0.05;
        }
      });
    }

    // Scientific solar cycle - update prominences occasionally
    if (prominencesRef.current && Math.random() < 0.001) {
      // Remove one random prominence
      if (prominencesRef.current.children.length > 0) {
        const index = Math.floor(Math.random() * prominencesRef.current.children.length);
        const prominence = prominencesRef.current.children[index];
        prominencesRef.current.remove(prominence);
        prominence.geometry.dispose();
        prominence.material.dispose();
      }

      // Add a new prominence
      createScientificProminence(prominencesRef.current, size);
    }
  });

  // Apply the appropriate detail based on quality
  const sphereDetail = qualityLevel === 'low' ? 64 :
                      qualityLevel === 'medium' ? 128 : 192;

  // Corona scale based on quality
  const coronaScale = qualityLevel === 'low' ? 2.0 :
                     qualityLevel === 'medium' ? 3.0 : 4.0;

  return (
    <group>
      {/* Photosphere - visible surface */}
      <mesh ref={sunRef} position={[0, 0, -5]}>
        <sphereGeometry args={[size, sphereDetail, sphereDetail]} />
        <primitive object={photosphereMaterial} attach="material" />

        {/* Scientific point light with accurate solar spectrum */}
        <pointLight
          intensity={1.2}
          distance={200}
          color="#fff4e8"
          decay={2}
        />
      </mesh>

      {/* Chromosphere - lower atmosphere */}
      <mesh ref={chromosphereRef} position={[0, 0, -5]}>
        <sphereGeometry args={[size * 1.01, sphereDetail / 2, sphereDetail / 2]} />
        <primitive object={chromosphereMaterial} attach="material" />
      </mesh>

      {/* Scientific solar prominences */}
      <group ref={prominencesRef} position={[0, 0, -5]} />

      {/* Corona - extended atmosphere */}
      <mesh ref={coronaRef} position={[0, 0, -5]}>
        <sphereGeometry args={[size * coronaScale, sphereDetail / 2, sphereDetail / 2]} />
        <primitive object={coronaMaterial} attach="material" />
      </mesh>

      {/* Post-processing effects - only rendered when modules are confirmed available */}
      {effectsReady && (
        <Suspense fallback={null}>
          <DynamicEffectComposer>
            <DynamicBloom
              intensity={0.4}
              luminanceThreshold={0.9}
              luminanceSmoothing={0.9}
              radius={0.6}
            />
          </DynamicEffectComposer>
        </Suspense>
      )}
    </group>
  );
};

// Main component with a system of planets
const PlanetSystem = ({ scrollY, mousePosition }) => {
  // Get quality settings from context
  const { qualityLevel, planetDetail, textureQuality } = useQuality();

  // Create orbital paths for visual reference with adaptive detail based on quality
  const createOrbitPath = useCallback((radius, color = "#223355") => {
    // Adjust segment count based on quality
    const segments = qualityLevel === 'low' ? 64 :
                    qualityLevel === 'medium' ? 96 : 128;

  return (
      <mesh position={[0, 0, -8]} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[radius, radius + 0.05, segments]} />
        <meshBasicMaterial
          color={color}
          transparent={true}
          opacity={0.25}
          side={THREE.DoubleSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    );
  }, [qualityLevel]);

  return (
    <group position={[0, 0, -8]}>
      {/* Orbital paths for visual reference with better visibility */}
      {createOrbitPath(15, "#334466")}
      {createOrbitPath(20, "#334466")}
      {createOrbitPath(25, "#334466")}
      {createOrbitPath(30, "#334466")}
      {createOrbitPath(38, "#334466")}

      {/* Sun at the center with improved size and settings */}
      <EnhancedSun
        size={5}
        mousePosition={mousePosition}
        qualityLevel={qualityLevel}
      />

      {/* Mercury with accurate Keplerian parameters */}
      <Planet
        position={[0, 0, 0]}
        size={0.38}
        textureUrl="/images/planets/mercury/mercury-4k.jpg"
        bumpMapUrl="/images/planets/mercury/mercury-bump.jpg"
        semiMajorAxis={3.9}
        eccentricity={0.2056}
        inclination={7.0}
        ascendingNode={48.33}
        argOfPeriapsis={29.12}
        orbitalPeriod={87.97}
        rotationPeriod={1407.6}
        axialTilt={0.034}
        glowColor="#a0a0a0"
        glowIntensity={0.05}
        mousePosition={mousePosition}
      />

      {/* Venus with accurate Keplerian parameters */}
      <Planet
        position={[0, 0, 0]}
        size={0.95}
        textureUrl="/images/planets/venus/venus-4k.jpg"
        semiMajorAxis={7.2}
        eccentricity={0.0068}
        inclination={3.39}
        ascendingNode={76.68}
        argOfPeriapsis={54.85}
        orbitalPeriod={224.7}
        rotationPeriod={-5832.5}  // Negative for retrograde rotation
        axialTilt={177.4}         // Almost upside down
        glowColor="#e0c080"
        glowIntensity={0.1}
        atmosphereColor="#f0e0c0"
        mousePosition={mousePosition}
      />

      {/* Earth with accurate Keplerian parameters */}
      <Planet
        position={[0, 0, 0]}
        size={1.0}
        textureUrl="/images/planets/earth/earth-4k.jpg"
        normalMapUrl="/images/planets/earth/earth-normal.jpg"
        specularMapUrl="/images/planets/earth/earth-specular.jpg"
        semiMajorAxis={10}
        eccentricity={0.0167}
        inclination={0.0}        // Reference plane
        ascendingNode={-11.26}
        argOfPeriapsis={114.20}
        orbitalPeriod={365.25}
        rotationPeriod={23.93}
        axialTilt={23.44}
        glowColor="#5599ff"
        glowIntensity={0.12}
        atmosphereColor="#88aaff"
        mousePosition={mousePosition}
      />

      {/* Mars with accurate Keplerian parameters */}
      <Planet
        position={[0, 0, 0]}
        size={0.53}
        textureUrl="/images/planets/mars/mars-4k.jpg"
        semiMajorAxis={15.2}
        eccentricity={0.0934}
        inclination={1.85}
        ascendingNode={49.57}
        argOfPeriapsis={286.50}
        orbitalPeriod={686.98}
        rotationPeriod={24.62}
        axialTilt={25.19}
        glowColor="#ff6040"
        glowIntensity={0.08}
        atmosphereColor="#ffb090"
        mousePosition={mousePosition}
      />

      {/* Jupiter with accurate Keplerian parameters */}
      <Planet
        position={[0, 0, 0]}
        size={2.5}
        textureUrl="/images/planets/jupiter/jupiter-4k.jpg"
        semiMajorAxis={26}
        eccentricity={0.0489}
        inclination={1.31}
        ascendingNode={100.55}
        argOfPeriapsis={273.87}
        orbitalPeriod={4332.59}
        rotationPeriod={9.93}
        axialTilt={3.13}
        glowColor="#d0c080"
        glowIntensity={0.1}
        mousePosition={mousePosition}
      />

      {/* Saturn with accurate Keplerian parameters and rings */}
      <SaturnWithRings
        position={[0, 0, 0]}
        size={2.2}
        textureUrl="/images/planets/saturn/saturn-4k.jpg"
        semiMajorAxis={38}
        eccentricity={0.0565}
        inclination={2.49}
        ascendingNode={113.67}
        argOfPeriapsis={339.39}
        orbitalPeriod={10759.22}
        rotationPeriod={10.66}
        axialTilt={26.73}
        glowColor="#d0b080"
        glowIntensity={0.08}
        mousePosition={mousePosition}
      />
    </group>
  );
};

export default PlanetSystem;
