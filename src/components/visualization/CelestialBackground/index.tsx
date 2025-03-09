import React, { useEffect, useRef, useState, useMemo } from 'react';
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass';
import { SMAAPass } from 'three/examples/jsm/postprocessing/SMAAPass';
import { ProgressiveLoader, QualitySettings } from './ProgressiveLoader';
import { DockerAIService } from '@/services/docker/DockerAIService';
import { logger } from '@/utils/logger';

export interface CelestialLayer {
  texture: string;
  speed: number;
  depth?: number;
  opacity?: number;
  scale?: number;
  rotationSpeed?: number;
  parallaxIntensity?: number;
  glowIntensity?: number;
  glowColor?: string;
  transformZ?: number;
  perspectiveFactor?: number;
}

export interface CelestialBackgroundProps {
  layers?: CelestialLayer[];
  mouseInteraction?: boolean;
  depthEffect?: boolean;
  interactive?: boolean;
  bloomStrength?: number;
  bloomRadius?: number;
  particleCount?: number;
  enableShootingStars?: boolean;
  enableOrbits?: boolean;
  enableNebulaEffects?: boolean;
  quality?: 'low' | 'medium' | 'high';
  perspectiveDepth?: number;
}

export const CelestialBackground: React.FC<CelestialBackgroundProps> = ({
  layers = [
    {
      texture: '/images/backgrounds-2/stars.jpg',
      speed: 0.1,
      depth: -400,
      opacity: 1.0,
      scale: 1.3,
      rotationSpeed: 0.0001,
      parallaxIntensity: 0.05,
      glowIntensity: 0.2,
      glowColor: '#1a4b8c',
      transformZ: -300,
      perspectiveFactor: 0.85
    },
    {
      texture: '/images/backgrounds-2/nebula.jpg',
      speed: 0.2,
      depth: -250,
      opacity: 0.8,
      scale: 1.2,
      rotationSpeed: 0.00015,
      parallaxIntensity: 0.1,
      glowIntensity: 0.3,
      glowColor: '#4a2b7c',
      transformZ: -200,
      perspectiveFactor: 0.9
    },
    {
      texture: '/images/nebulea/blue-nebula.jpg',
      speed: 0.3,
      depth: -150,
      opacity: 0.7,
      scale: 1.1,
      rotationSpeed: 0.0002,
      parallaxIntensity: 0.15,
      glowIntensity: 0.4,
      glowColor: '#2b5a9c',
      transformZ: -100,
      perspectiveFactor: 0.95
    },
    {
      texture: '/images/backgrounds-2/dust.jpg',
      speed: 0.4,
      depth: -75,
      opacity: 0.6,
      scale: 1.0,
      rotationSpeed: 0.00025,
      parallaxIntensity: 0.2,
      glowIntensity: 0.3,
      glowColor: '#5a3b8c',
      transformZ: -50,
      perspectiveFactor: 1.0
    }
  ],
  mouseInteraction = true,
  depthEffect = true,
  interactive = true,
  bloomStrength = 1.8,
  bloomRadius = 0.85,
  particleCount = 1500,
  enableShootingStars = true,
  enableOrbits = true,
  enableNebulaEffects = true,
  quality = 'high',
  perspectiveDepth = 1000
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const layerMeshes = useRef<THREE.Mesh[]>([]);
  const lastMousePosition = useRef({ x: 0, y: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const progressiveLoader = useRef<ProgressiveLoader>(new ProgressiveLoader(logger));
  const dockerAIService = useRef(DockerAIService.getInstance());
  const frameId = useRef<number>(0);

  // Added this ref at the component level to fix ESLint error
  const orbitAnimationRef = useRef<(time: number) => void>(() => {});

  // Define quality settings
  const highQuality: QualitySettings = { size: 2048, mipmap: true, anisotropy: 4 };
  const mediumQuality: QualitySettings = { size: 1024, mipmap: true, anisotropy: 2 };

  const effectComposerRef = useRef<EffectComposer | null>(null);
  const particlesRef = useRef<THREE.Points | null>(null);
  const mousePosition = useRef({ x: 0, y: 0 });

  // Quality settings based on props
  const qualitySettings = useMemo(() => {
    const settings = {
      pixelRatio: 1,
      anisotropy: 1,
      particleMultiplier: 1,
      antialiasing: false
    };

    switch(quality) {
      case 'low':
        settings.pixelRatio = Math.min(window.devicePixelRatio, 1);
        settings.anisotropy = 1;
        settings.particleMultiplier = 0.6;
        settings.antialiasing = false;
        break;
      case 'medium':
        settings.pixelRatio = Math.min(window.devicePixelRatio, 1.5);
        settings.anisotropy = 2;
        settings.particleMultiplier = 1;
        settings.antialiasing = true;
        break;
      case 'high':
        settings.pixelRatio = Math.min(window.devicePixelRatio, 2);
        settings.anisotropy = 4;
        settings.particleMultiplier = 1.5;
        settings.antialiasing = true;
        break;
    }

    return settings;
  }, [quality]);

  // Initialize Three.js scene with enhanced settings
  const initThreeJS = () => {
    const container = containerRef.current;
    if (!container) return;

    // Create scene with fog for depth
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x000030, 0.0015);
    sceneRef.current = scene;

    // Create camera with enhanced perspective
    const camera = new THREE.PerspectiveCamera(
      65,  // Wider FOV for more immersive experience
      window.innerWidth / window.innerHeight,
      0.1,
      perspectiveDepth
    );
    camera.position.z = 350;
    cameraRef.current = camera;

    // Create renderer with advanced settings
    const renderer = new THREE.WebGLRenderer({
      antialias: qualitySettings.antialiasing,
      alpha: true,
      powerPreference: 'high-performance',
      stencil: false,
      depth: true
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(qualitySettings.pixelRatio);
    renderer.setClearColor(0x000025, 1);
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.3;
    // Enable shadow mapping for enhanced light effects
    renderer.shadowMap.enabled = quality !== 'low';
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Initialize enhanced effect composer for post-processing
    const composer = new EffectComposer(renderer);

    // Standard render pass
    const renderPass = new RenderPass(scene, camera);
    composer.addPass(renderPass);

    // Enhanced bloom pass for glow effects
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(window.innerWidth, window.innerHeight),
      bloomStrength,
      bloomRadius,
      0.75
    );
    // Optimized bloom settings
    bloomPass.threshold = 0.15;
    bloomPass.strength = bloomStrength;
    bloomPass.radius = bloomRadius;
    composer.addPass(bloomPass);

    // Advanced color adjustment shader
    const colorShader = {
      uniforms: {
        "tDiffuse": { value: null },
        "saturation": { value: 1.3 },
        "brightness": { value: 1.1 },
        "contrast": { value: 1.1 },
        "time": { value: 0 }
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform float saturation;
        uniform float brightness;
        uniform float contrast;
        uniform float time;
        varying vec2 vUv;

        void main() {
          // Sample the texture
          vec4 color = texture2D(tDiffuse, vUv);

          // Saturation adjustment with enhanced algorithm
          float luminance = dot(color.rgb, vec3(0.2126, 0.7152, 0.0722));
          vec3 saturated = mix(vec3(luminance), color.rgb, saturation);

          // Contrast adjustment
          vec3 contrasted = (saturated - 0.5) * contrast + 0.5;

          // Brightness adjustment
          vec3 bright = contrasted * brightness;

          // Subtle color shifting over time for nebula effects
          if (${enableNebulaEffects ? 'true' : 'false'}) {
            float r = bright.r + sin(time * 0.1) * 0.02;
            float b = bright.b + cos(time * 0.1) * 0.02;
            bright = vec3(r, bright.g, b);
          }

          // Prevent clipping
          bright = clamp(bright, 0.0, 1.0);

          gl_FragColor = vec4(bright, color.a);
        }
      `
    };

    const colorPass = new ShaderPass(colorShader);
    composer.addPass(colorPass);

    // Add SMAA anti-aliasing if quality permits
    if (qualitySettings.antialiasing) {
      const smaaPass = new SMAAPass(window.innerWidth, window.innerHeight);
      composer.addPass(smaaPass);
    }

    effectComposerRef.current = composer;

    // Add enhanced star particles
    addStarParticles(scene);

    // Add cosmic dust particles
    addCosmicDustParticles(scene);

    // Add shooting stars if enabled
    if (enableShootingStars) {
      addShootingStars(scene);
    }

    // Add orbiting planets if enabled
    if (enableOrbits) {
      addOrbitingElements(scene);
    }

    // Add nebula clusters if enabled
    if (enableNebulaEffects) {
      addNebulaEffects(scene);
    }

    return { scene, camera, renderer, composer };
  };

  // Add cosmic dust particles for enhanced depth effect
  const addCosmicDustParticles = (scene: THREE.Scene) => {
    // Create geometry for cosmic dust particles
    const dustCount = Math.floor(particleCount * 0.7); // Use fewer particles than stars
    const dustGeometry = new THREE.BufferGeometry();

    // Create arrays for attributes
    const positions = new Float32Array(dustCount * 3);
    const sizes = new Float32Array(dustCount);
    const colors = new Float32Array(dustCount * 3);
    const rotations = new Float32Array(dustCount);
    const speeds = new Float32Array(dustCount);

    // Color options for dust particles with subtle variations
    const dustColors = [
      new THREE.Color(0x3b82f6).multiplyScalar(0.4), // Blue
      new THREE.Color(0x7c3aed).multiplyScalar(0.3), // Purple
      new THREE.Color(0xf59e0b).multiplyScalar(0.3), // Gold
      new THREE.Color(0x0ea5e9).multiplyScalar(0.3), // Light blue
      new THREE.Color(0x8b5cf6).multiplyScalar(0.3)  // Lavender
    ];

    // Fill arrays with dust particle data
    for (let i = 0; i < dustCount; i++) {
      // Create in spherical distribution for better 3D effect
      const radius = Math.random() * 1500 + 300;
      const theta = Math.random() * Math.PI * 2; // Angle around y-axis
      const phi = Math.acos(2 * Math.random() - 1); // Angle from y-axis

      // Position with true 3D distribution
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta); // x
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta); // y
      positions[i * 3 + 2] = -radius * Math.cos(phi) * 0.7 - 100; // z (behind layers but not too far)

      // Size variation - cosmic dust is smaller than stars
      sizes[i] = Math.random() * 3 + 0.5;

      // Random rotation for particles
      rotations[i] = Math.random() * Math.PI * 2;

      // Movement speed variation
      speeds[i] = Math.random() * 0.2 + 0.05;

      // Random color from palette
      const color = dustColors[Math.floor(Math.random() * dustColors.length)];

      // Apply slight variations to color
      const hsl = { h: 0, s: 0, l: 0 };
      color.getHSL(hsl);

      // Add subtle variations
      hsl.h += (Math.random() - 0.5) * 0.1;
      hsl.s = Math.min(1, Math.max(0, hsl.s + (Math.random() * 0.2 - 0.1)));
      hsl.l = Math.min(0.6, Math.max(0.1, hsl.l + (Math.random() * 0.2 - 0.1)));

      const dustColor = new THREE.Color().setHSL(hsl.h, hsl.s, hsl.l);

      colors[i * 3] = dustColor.r;
      colors[i * 3 + 1] = dustColor.g;
      colors[i * 3 + 2] = dustColor.b;
    }

    // Set attributes
    dustGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    dustGeometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
    dustGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    dustGeometry.setAttribute('rotation', new THREE.BufferAttribute(rotations, 1));
    dustGeometry.setAttribute('speed', new THREE.BufferAttribute(speeds, 1));

    // Custom shader for dust particles with glow and movement
    const dustMaterial = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        pointTexture: { value: new THREE.TextureLoader().load('/images/nebulea/dust_particle.png') }
      },
      vertexShader: `
        attribute float size;
        attribute vec3 color;
        attribute float rotation;
        attribute float speed;

        uniform float time;

        varying vec3 vColor;
        varying float vRotation;

        void main() {
          vColor = color;
          vRotation = rotation + time * speed;

          // Add subtle floating motion
          vec3 pos = position;

          // Unique movement pattern for each particle
          float unique = rotation * 173.13; // Use rotation as unique identifier
          float floatX = sin(time * speed + unique) * 5.0;
          float floatY = cos(time * speed * 0.7 + unique * 3.7) * 5.0;
          float floatZ = sin(time * speed * 0.5 + unique * 2.3) * 2.0;

          pos.x += floatX;
          pos.y += floatY;
          pos.z += floatZ;

          vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);

          // Size attenuation based on distance
          float distanceFactor = 350.0 / -mvPosition.z;
          gl_PointSize = size * distanceFactor * (0.7 + 0.3 * sin(time * 0.5 + unique));

          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform sampler2D pointTexture;

        varying vec3 vColor;
        varying float vRotation;

        void main() {
          // Calculate rotated UV coordinates for point
          float c = cos(vRotation);
          float s = sin(vRotation);
          vec2 rotatedUV = vec2(
            c * (gl_PointCoord.x - 0.5) + s * (gl_PointCoord.y - 0.5) + 0.5,
            c * (gl_PointCoord.y - 0.5) - s * (gl_PointCoord.x - 0.5) + 0.5
          );

          vec4 texColor = texture2D(pointTexture, rotatedUV);

          // Enhance glow at edges
          float distFromCenter = length(gl_PointCoord - vec2(0.5));
          float glowStrength = smoothstep(0.5, 0.0, distFromCenter) * 0.5 + 0.5;

          // Final color with glow effect
          vec3 finalColor = vColor * glowStrength;
          float alpha = texColor.a * (0.7 + 0.3 * glowStrength);

          gl_FragColor = vec4(finalColor, alpha);
        }
      `,
      blending: THREE.AdditiveBlending,
      depthTest: true,
      depthWrite: false,
      transparent: true,
      vertexColors: true
    });

    // Create points system for dust
    const dustParticles = new THREE.Points(dustGeometry, dustMaterial);
    dustParticles.position.z = -200; // Position behind stars
    dustParticles.userData = { type: 'cosmicDust' };
    scene.add(dustParticles);

    // Store reference for animation
    scene.userData.dustParticles = dustParticles;
  };

  // Add enhanced nebula effects for atmospheric depth
  const addNebulaEffects = (scene: THREE.Scene) => {
    // Create several nebula gas clouds with different colors and positions
    const nebulaColors = [
      {
        color: new THREE.Color(0x3b82f6), // Blue
        position: new THREE.Vector3(-500, 300, -700),
        scale: new THREE.Vector3(800, 500, 1),
        rotation: Math.PI * 0.2
      },
      {
        color: new THREE.Color(0x8b5cf6), // Purple
        position: new THREE.Vector3(600, -200, -600),
        scale: new THREE.Vector3(700, 600, 1),
        rotation: -Math.PI * 0.15
      },
      {
        color: new THREE.Color(0xef4444).multiplyScalar(0.6), // Red (dimmed)
        position: new THREE.Vector3(-400, -400, -750),
        scale: new THREE.Vector3(500, 800, 1),
        rotation: Math.PI * 0.1
      }
    ];

    // Create nebula group
    const nebulaGroup = new THREE.Group();
    nebulaGroup.position.z = -400;
    scene.add(nebulaGroup);

    // Create each nebula cloud with shader-based rendering
    nebulaColors.forEach((nebulaData, index) => {
      // Create geometry (simple plane)
      const geometry = new THREE.PlaneGeometry(1, 1, 1, 1);

      // Create shader material for volumetric nebula effect
      const material = new THREE.ShaderMaterial({
        uniforms: {
          time: { value: index * 1000 }, // Different starting time
          color: { value: nebulaData.color },
          resolution: { value: new THREE.Vector2(1024, 1024) }
        },
        vertexShader: `
          varying vec2 vUv;

          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform float time;
          uniform vec3 color;
          uniform vec2 resolution;

          varying vec2 vUv;

          // Simplex noise functions for volumetric effect
          // Noise function based on https://github.com/ashima/webgl-noise
          vec3 mod289(vec3 x) {
            return x - floor(x * (1.0 / 289.0)) * 289.0;
          }

          vec4 mod289(vec4 x) {
            return x - floor(x * (1.0 / 289.0)) * 289.0;
          }

          vec4 permute(vec4 x) {
            return mod289(((x*34.0)+1.0)*x);
          }

          vec4 taylorInvSqrt(vec4 r) {
            return 1.79284291400159 - 0.85373472095314 * r;
          }

          float snoise(vec3 v) {
            const vec2 C = vec2(1.0/6.0, 1.0/3.0);
            const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

            // First corner
            vec3 i  = floor(v + dot(v, C.yyy));
            vec3 x0 = v - i + dot(i, C.xxx);

            // Other corners
            vec3 g = step(x0.yzx, x0.xyz);
            vec3 l = 1.0 - g;
            vec3 i1 = min(g.xyz, l.zxy);
            vec3 i2 = max(g.xyz, l.zxy);

            vec3 x1 = x0 - i1 + C.xxx;
            vec3 x2 = x0 - i2 + C.yyy; // 2.0*C.x = 1/3 = C.y
            vec3 x3 = x0 - D.yyy;      // -1.0+3.0*C.x = -0.5 = -D.y

            // Permutations
            i = mod289(i);
            vec4 p = permute(permute(permute(
                     i.z + vec4(0.0, i1.z, i2.z, 1.0))
                   + i.y + vec4(0.0, i1.y, i2.y, 1.0))
                   + i.x + vec4(0.0, i1.x, i2.x, 1.0));

            // Gradients
            float n_ = 0.142857142857; // 1.0/7.0
            vec3  ns = n_ * D.wyz - D.xzx;

            vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

            vec4 x_ = floor(j * ns.z);
            vec4 y_ = floor(j - 7.0 * x_);

            vec4 x = x_ *ns.x + ns.yyyy;
            vec4 y = y_ *ns.x + ns.yyyy;
            vec4 h = 1.0 - abs(x) - abs(y);

            vec4 b0 = vec4(x.xy, y.xy);
            vec4 b1 = vec4(x.zw, y.zw);

            vec4 s0 = floor(b0)*2.0 + 1.0;
            vec4 s1 = floor(b1)*2.0 + 1.0;
            vec4 sh = -step(h, vec4(0.0));

            vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
            vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;

            vec3 p0 = vec3(a0.xy, h.x);
            vec3 p1 = vec3(a0.zw, h.y);
            vec3 p2 = vec3(a1.xy, h.z);
            vec3 p3 = vec3(a1.zw, h.w);

            // Normalise gradients
            vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
            p0 *= norm.x;
            p1 *= norm.y;
            p2 *= norm.z;
            p3 *= norm.w;

            // Mix final noise value
            vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
            m = m * m;
            return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
          }

          void main() {
            // Center UVs
            vec2 uv = vUv * 2.0 - 1.0;

            // Create radial mask for cloud shape
            float mask = smoothstep(1.0, 0.1, length(uv));

            // Multiple layers of noise for depth
            float noise1 = snoise(vec3(uv * 1.5, time * 0.01)) * 0.5 + 0.5;
            float noise2 = snoise(vec3(uv * 3.0 + 100.0, time * 0.015)) * 0.5 + 0.5;
            float noise3 = snoise(vec3(uv * 5.0 + 300.0, time * 0.005)) * 0.5 + 0.5;

            // Combine noise layers
            float finalNoise = noise1 * 0.6 + noise2 * 0.3 + noise3 * 0.1;

            // Edge enhancement
            finalNoise = smoothstep(0.2, 0.7, finalNoise);

            // Apply radial mask
            finalNoise *= mask;

            // Vignette effect
            float vignette = smoothstep(1.0, 0.3, length(uv));
            finalNoise *= vignette;

            // Apply color with opacity based on noise
            vec3 finalColor = color * finalNoise;

            // Distance falloff for edges
            float edgeFalloff = smoothstep(1.0, 0.6, length(uv));

            gl_FragColor = vec4(finalColor, finalNoise * 0.5 * edgeFalloff);
          }
        `,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        side: THREE.DoubleSide
      });

      // Create mesh and set properties
      const nebula = new THREE.Mesh(geometry, material);
      nebula.position.copy(nebulaData.position);
      nebula.scale.copy(nebulaData.scale);
      nebula.rotation.z = nebulaData.rotation;

      // Add custom animation data
      nebula.userData = {
        pulseFactor: 0.05 + Math.random() * 0.05,
        pulseSpeed: 0.2 + Math.random() * 0.3,
        floatSpeed: 0.1 + Math.random() * 0.2,
        floatAmount: 10 + Math.random() * 20
      };

      nebulaGroup.add(nebula);
    });

    // Store reference for animation
    scene.userData.nebulaGroup = nebulaGroup;
  };

  // Create enhanced star particle system with depth variation and improved twinkling
  const addStarParticles = (scene: THREE.Scene) => {
    const particleGeometry = new THREE.BufferGeometry();
    const actualParticleCount = Math.floor(particleCount * qualitySettings.particleMultiplier);

    // Create arrays for particle attributes
    const positions = new Float32Array(actualParticleCount * 3);
    const sizes = new Float32Array(actualParticleCount);
    const colors = new Float32Array(actualParticleCount * 3);
    const twinkleSpeed = new Float32Array(actualParticleCount); // Custom attribute for varied twinkling
    const twinklePhase = new Float32Array(actualParticleCount); // Initial phase offset for twinkling
    const depths = new Float32Array(actualParticleCount); // Store depth for easier access

    // Enhanced color palette for stars
    const colorOptions = [
      new THREE.Color(0xffffff), // White
      new THREE.Color(0xe0e8ff), // Blueish white
      new THREE.Color(0xffeedd), // Warm white
      new THREE.Color(0xccccff), // Light blue
      new THREE.Color(0xffcccc), // Light red
      new THREE.Color(0xffffcc), // Light yellow
      new THREE.Color(0xe6c8ff)  // Light purple
    ];

    // Create a wider distribution for better depth perception
    for (let i = 0; i < actualParticleCount; i++) {
      // Position with true 3D distribution and depth clustering
      const depth = Math.random();
      const depthFactor = 1 - depth * 0.6; // Closer stars appear brighter
      const radius = Math.random() * 2000 + 500;

      // Create a more realistic 3D distribution
      const theta = Math.random() * Math.PI * 2; // Angle around y-axis
      const phi = Math.acos(2 * Math.random() - 1); // Angle from y-axis

      // Convert spherical to Cartesian coordinates
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta); // x
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta); // y
      positions[i * 3 + 2] = -radius * Math.cos(phi) - 200; // z (behind layers)

      // Store depth for animation purposes
      depths[i] = depth;

      // Size varies with depth - closer stars are larger
      const baseSize = Math.random() * 4 + 1;
      sizes[i] = baseSize * depthFactor;

      // Varied twinkling speeds and phases
      twinkleSpeed[i] = Math.random() * 3 + 0.5; // Random speed multiplier
      twinklePhase[i] = Math.random() * Math.PI * 2; // Random starting phase

      // Enhanced color selection and variation
      const colorIndex = Math.floor(Math.random() * colorOptions.length);
      const color = colorOptions[colorIndex];

      // Apply more sophisticated color variations
      const hsl = { h: 0, s: 0, l: 0 };
      color.getHSL(hsl);

      // More variation for distant stars (environmental storytelling)
      const distanceVariationFactor = 0.1 + (depth * 0.15);

      hsl.h += Math.random() * distanceVariationFactor - (distanceVariationFactor / 2); // Hue variation
      hsl.s = Math.min(1, Math.max(0, hsl.s + (Math.random() * 0.3 - 0.15))); // Saturation variation
      hsl.l = Math.min(1, Math.max(0.3, hsl.l * depthFactor)); // Brightness affected by depth

      const variedColor = new THREE.Color().setHSL(hsl.h, hsl.s, hsl.l);
      colors[i * 3] = variedColor.r;
      colors[i * 3 + 1] = variedColor.g;
      colors[i * 3 + 2] = variedColor.b;
    }

    // Set attributes
    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
    particleGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    particleGeometry.setAttribute('twinkleSpeed', new THREE.BufferAttribute(twinkleSpeed, 1));
    particleGeometry.setAttribute('twinklePhase', new THREE.BufferAttribute(twinklePhase, 1));
    particleGeometry.setAttribute('depth', new THREE.BufferAttribute(depths, 1));

    // Improved star texture with better glow
    const loader = new THREE.TextureLoader();
    const starTexture = loader.load('/images/nebulea/star_particle.png');

    // Enhanced shader material with sophisticated twinkling and glow
    const particleMaterial = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        pointTexture: { value: starTexture },
        cameraPosition: { value: new THREE.Vector3() }
      },
      vertexShader: `
        attribute float size;
        attribute vec3 color;
        attribute float twinkleSpeed;
        attribute float twinklePhase;
        attribute float depth;
        uniform float time;
        uniform vec3 cameraPosition;

        varying vec3 vColor;
        varying float vTwinkle;

        void main() {
          vColor = color;

          // Advanced twinkling algorithm
          float twinkling = sin(time * twinkleSpeed + twinklePhase) * 0.5 + 0.5;
          vTwinkle = twinkling;

          // Calculate parallax based on mouse and camera
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);

          // Sophisticated size calculation based on depth and twinkling
          float sizeVariation = mix(0.8, 1.2, twinkling);
          float distanceFactor = 350.0 / -mvPosition.z;
          float finalSize = size * sizeVariation * distanceFactor;

          // Size limits to prevent stars from becoming too large
          finalSize = clamp(finalSize, 0.5, 12.0);

          gl_PointSize = finalSize;
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform sampler2D pointTexture;
        uniform float time;

        varying vec3 vColor;
        varying float vTwinkle;

        void main() {
          // Sample the texture
          vec4 texColor = texture2D(pointTexture, gl_PointCoord);

          // Enhanced glow effect based on twinkling
          float glowFactor = mix(0.8, 1.5, vTwinkle);
          vec3 glow = vColor * glowFactor;

          // Add subtle color variation over time for a more realistic star
          float r = glow.r * (1.0 + sin(time * 0.1) * 0.05);
          float b = glow.b * (1.0 + cos(time * 0.12) * 0.05);
          vec3 finalColor = vec3(r, glow.g, b);

          // Ensure the core of the star is brighter
          float alpha = texColor.a * vTwinkle;

          gl_FragColor = vec4(finalColor, alpha);
        }
      `,
      blending: THREE.AdditiveBlending,
      depthTest: true,
      depthWrite: false,
      transparent: true,
      vertexColors: true
    });

    const particles = new THREE.Points(particleGeometry, particleMaterial);
    scene.add(particles);
    particlesRef.current = particles;
  };

  // Add enhanced shooting stars with realistic trails for dynamic background
  const addShootingStars = (scene: THREE.Scene) => {
    // Create a shooting star group with 3D positioning
    const shootingStarGroup = new THREE.Group();
    shootingStarGroup.position.z = -300; // Place behind other elements
    scene.add(shootingStarGroup);

    // Create 10-15 shooting stars with staggered animation for more frequent activity
    const shootingStarCount = Math.floor(Math.random() * 5) + 10;

    for (let i = 0; i < shootingStarCount; i++) {
      // Use custom shader for more realistic trail with glow effect
      const shootingStarMaterial = new THREE.ShaderMaterial({
        uniforms: {
          time: { value: 0.0 },
          pointTexture: { value: new THREE.TextureLoader().load('/images/nebulea/star_particle.png') },
          color: { value: new THREE.Color(
            // Random colors with blue/white bias for more realistic space effect
            Math.random() > 0.7 ? 0xffffff :
            Math.random() > 0.5 ? 0xe0e8ff : 0xa0c0ff
          )},
          progress: { value: 0.0 }, // Animation progress
          trailFactor: { value: Math.random() * 0.5 + 0.5 } // Random trail length variation
        },
        vertexShader: `
          attribute float size;
          attribute float alpha;
          uniform float time;
          uniform float progress;
          uniform float trailFactor;

          varying float vAlpha;
          varying vec3 vPosition;

          void main() {
            vAlpha = alpha * (1.0 - progress); // Fade based on progress
            vPosition = position;

            // Calculate trail effect - points further back get smaller
            float pointIndex = position.z; // Use z position to determine position in trail
            float trailEffect = 1.0 - (pointIndex * 0.1 * trailFactor);

            // Size diminishes along trail and with overall progress
            float finalSize = size * trailEffect * (1.0 - progress * 0.5);

            // Add subtle oscillation to trail
            float oscillation = sin(time * 5.0 + pointIndex) * 0.2 * trailEffect;
            vec3 pos = position;
            pos.y += oscillation;

            vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
            gl_PointSize = finalSize * (300.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;
          }
        `,
        fragmentShader: `
          uniform sampler2D pointTexture;
          uniform vec3 color;

          varying float vAlpha;
          varying vec3 vPosition;

          void main() {
            // Sample base texture
            vec4 texColor = texture2D(pointTexture, gl_PointCoord);

            // Create more intense core with radial falloff
            float distFromCenter = length(gl_PointCoord - vec2(0.5));
            float intensity = smoothstep(0.5, 0.0, distFromCenter);

            // Apply color with enhanced intensity at head of shooting star
            vec3 finalColor = mix(color * 0.7, color, intensity * (1.0 - vPosition.z * 0.1));

            // Final color with alpha for trail effect
            gl_FragColor = vec4(finalColor, texColor.a * vAlpha * intensity);
          }
        `,
        blending: THREE.AdditiveBlending,
        depthTest: false,
        transparent: true,
        vertexColors: false
      });

      // Create more detailed trail with points
      const trailLength = Math.floor(Math.random() * 30) + 20; // Longer trails
      const trailGeometry = new THREE.BufferGeometry();

      // Create arrays for trail positions, sizes, and alpha values
      const positions = new Float32Array(trailLength * 3);
      const sizes = new Float32Array(trailLength);
      const alphas = new Float32Array(trailLength);

      // Generate a curved trail with 3D depth
      const curveFactor = (Math.random() - 0.5) * 0.2; // Random curve direction
      const depthFactor = Math.random() * 0.3 + 0.1; // Random depth variation

      for (let j = 0; j < trailLength; j++) {
        // Position along trail - head of meteor at 0, tail stretches back
        const t = j / (trailLength - 1);

        // Curve the trail slightly for more natural appearance
        const curvature = curveFactor * Math.pow(t, 2);

        // Z value represents position in trail (0 = head, increasing = tail)
        positions[j * 3] = -t * 120 * (1 + Math.random() * 0.1); // X decreases along trail (meteor flies right to left)
        positions[j * 3 + 1] = curvature * 40; // Y curves slightly
        positions[j * 3 + 2] = j; // Z used to track position in trail

        // Head is largest, tail gets smaller
        sizes[j] = (1 - t) * (Math.random() * 2 + 6);

        // Head is brightest, tail fades out
        alphas[j] = Math.pow(1 - t, 2) * (1 - Math.random() * 0.2);
      }

      trailGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      trailGeometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
      trailGeometry.setAttribute('alpha', new THREE.BufferAttribute(alphas, 1));

      // Create the enhanced shooting star object
      const shootingStar = new THREE.Points(trailGeometry, shootingStarMaterial);

      // Add better random positioning with depth variation
      const randomAngle = Math.random() * Math.PI * 2;
      const randomDistance = Math.random() * 1000 + 500;
      const randomHeight = Math.random() * 800 - 400;
      const randomDepth = Math.random() * 400 - 600;

      shootingStar.position.set(
        Math.cos(randomAngle) * randomDistance,
        randomHeight,
        randomDepth
      );

      // Random rotation with 3D component for varied trajectories
      shootingStar.rotation.z = Math.random() * Math.PI - Math.PI/2; // Angle of travel
      shootingStar.rotation.x = (Math.random() - 0.5) * 0.2; // Slight tilt in 3D space
      shootingStar.rotation.y = (Math.random() - 0.5) * 0.1; // Slight yaw

      // Initial invisible state
      shootingStar.visible = false;

      // Store initial properties for reuse
      shootingStar.userData = {
        initialPosition: shootingStar.position.clone(),
        initialRotation: {
          x: shootingStar.rotation.x,
          y: shootingStar.rotation.y,
          z: shootingStar.rotation.z
        },
        speed: Math.random() * 400 + 500, // Random speed
        progress: 0,
        material: shootingStarMaterial
      };

      // Add to group
      shootingStarGroup.add(shootingStar);

      // Stagger initial appearances
      setTimeout(() => {
        activateShootingStar(shootingStar, i);
      }, i * 3000 + Math.random() * 7000);
    }

    // Function to animate a shooting star with enhanced visual effects
    const activateShootingStar = (star: THREE.Points, index: number) => {
      if (!sceneRef.current) return;

      // Make star visible
      star.visible = true;

      // Reset position and rotation to initial state
      star.position.copy(star.userData.initialPosition);
      star.rotation.x = star.userData.initialRotation.x;
      star.rotation.y = star.userData.initialRotation.y;
      star.rotation.z = star.userData.initialRotation.z;

      // Reset progress
      star.userData.progress = 0;

      // Apply slight randomization to trajectory for variety
      star.rotation.z += (Math.random() - 0.5) * 0.2;

      // Get material and reset uniforms
      const material = star.material as THREE.ShaderMaterial;
      if (material.uniforms) {
        material.uniforms.progress.value = 0;

        // Occasionally change color for variety
        if (Math.random() > 0.7) {
          material.uniforms.color.value.set(
            Math.random() > 0.5 ? 0xffffff : 0xe0e8ff
          );
        }
      }

      // Animation variables
      const duration = Math.random() * 1.5 + 1.5; // 1.5-3 seconds
      const startTime = performance.now() / 1000;
      const speed = star.userData.speed;

      // Star animation loop with advanced motion
      const animateStar = () => {
        if (!sceneRef.current) return;

        const now = performance.now() / 1000;
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Store progress for shader
        star.userData.progress = progress;

        // Update material time and progress uniforms
        if (material.uniforms) {
          material.uniforms.time.value = now;
          material.uniforms.progress.value = progress;
        }

        // Calculate movement with ease-out for natural trail
        const easedProgress = 1 - Math.pow(1 - progress, 3); // Cubic ease-out
        const distance = easedProgress * speed;

        // Move forward along direction of rotation
        const direction = new THREE.Vector3(1, 0, 0);
        direction.applyEuler(star.rotation);
        star.position.x = star.userData.initialPosition.x + direction.x * distance;
        star.position.y = star.userData.initialPosition.y + direction.y * distance;
        star.position.z = star.userData.initialPosition.z + direction.z * distance;

        // Continue animation until complete
        if (progress < 1) {
          requestAnimationFrame(animateStar);
        } else {
          star.visible = false;

          // Schedule next appearance with varied delay
          const nextDelay = Math.random() * 12000 + 4000;
          setTimeout(() => {
            activateShootingStar(star, index);
          }, nextDelay);
        }
      };

      // Start animation
      requestAnimationFrame(animateStar);
    };

    // Add shooting star manager to scene for reference
    scene.userData.shootingStarGroup = shootingStarGroup;
  };

  // Modified addOrbitingElements to use the ref from component level instead of creating it inside
  const addOrbitingElements = (scene: THREE.Scene) => {
    const planetGroup = new THREE.Group();
    planetGroup.position.z = -350;
    scene.add(planetGroup);

    // Create 2-4 orbiting planets at different distances
    const planetCount = Math.floor(Math.random() * 3) + 2;

    const planetTextures = [
      '/images/planets/gas-giant-blue.png',
      '/images/planets/mars.png',
      '/images/planets/neptune.png',
      '/images/planets/saturn.png'
    ];

    for (let i = 0; i < planetCount; i++) {
      // Create orbit path
      const orbitRadius = 120 + i * 80;
      const orbitPath = new THREE.RingGeometry(orbitRadius - 0.5, orbitRadius + 0.5, 64);
      const orbitMaterial = new THREE.MeshBasicMaterial({
        color: 0x3b82f6,
        transparent: true,
        opacity: 0.1,
        side: THREE.DoubleSide
      });
      const orbit = new THREE.Mesh(orbitPath, orbitMaterial);
      orbit.rotation.x = Math.PI / 2; // Make it horizontal
      planetGroup.add(orbit);

      // Create a planet on this orbit
      const planetSize = 15 - i * 3; // Bigger planets closer to center
      const planetGeometry = new THREE.PlaneGeometry(planetSize, planetSize);

      // Choose a random texture
      const textureIndex = Math.floor(Math.random() * planetTextures.length);
      const texture = new THREE.TextureLoader().load(planetTextures[textureIndex]);

      const planetMaterial = new THREE.MeshBasicMaterial({
        map: texture,
        transparent: true,
        side: THREE.DoubleSide,
      });

      const planet = new THREE.Mesh(planetGeometry, planetMaterial);

      // Position on the orbit
      const angle = Math.random() * Math.PI * 2;
      planet.position.x = Math.cos(angle) * orbitRadius;
      planet.position.y = Math.sin(angle) * orbitRadius;

      // Add to group
      planetGroup.add(planet);

      // Add glow effect
      const glowGeometry = new THREE.PlaneGeometry(planetSize * 1.5, planetSize * 1.5);
      const glowMaterial = new THREE.MeshBasicMaterial({
        map: new THREE.TextureLoader().load('/images/nebulea/glow.png'),
        transparent: true,
        opacity: 0.4,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide,
        depthWrite: false
      });

      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      glow.position.z = -1; // Slightly behind the planet
      planet.add(glow);

      // Animation data in userData
      planet.userData = {
        orbitRadius,
        orbitSpeed: 0.1 / (i + 1), // Further planets move slower
        initialAngle: angle,
        rotationSpeed: 0.005 * (Math.random() * 0.5 + 0.75) // Random rotation speed
      };
    }

    // Add this to animation loop
    const animateOrbits = (time: number) => {
      if (!planetGroup) return;

      // Rotate the entire group slightly for a subtle 3D effect
      planetGroup.rotation.y = Math.sin(time * 0.05) * 0.1;

      // Animate each planet in its orbit
      planetGroup.children.forEach(child => {
        if (child instanceof THREE.Mesh && child.geometry instanceof THREE.PlaneGeometry) {
          const userData = child.userData;

          if (userData.orbitRadius) {
            // Update position on orbit
            const angle = userData.initialAngle + time * userData.orbitSpeed;
            child.position.x = Math.cos(angle) * userData.orbitRadius;
            child.position.y = Math.sin(angle) * userData.orbitRadius;

            // Rotate planet on its axis
            child.rotation.z += userData.rotationSpeed;

            // Make planet face the camera (billboarding)
            if (cameraRef.current) {
              child.lookAt(cameraRef.current.position);
            }
          }
        }
      });
    };

    // Update the ref at component level instead of creating it inside this function
    orbitAnimationRef.current = animateOrbits;

    // Return animation function to be called in main animation loop
    return orbitAnimationRef.current;
  };

  // Create celestial layers with enhanced materials and effects
  const createCelestialLayers = async (scene: THREE.Scene) => {
    // Clear any existing layers
    layerMeshes.current.forEach(mesh => scene.remove(mesh));
    layerMeshes.current = [];

    // Load textures and create meshes for each layer
    for (let i = 0; i < layers.length; i++) {
      const layer = layers[i];
      try {
        // Choose quality based on layer importance
        const quality = i === 0 ? highQuality : mediumQuality;
        const texture = await progressiveLoader.current.loadCelestialTexture(layer.texture, quality);

        // Set texture properties
        texture.wrapS = texture.wrapT = THREE.RepeatWrapping;

        // Create material with enhanced shading
        const material = new THREE.ShaderMaterial({
          uniforms: {
            map: { value: texture },
            opacity: { value: layer.opacity || 1.0 },
            time: { value: 0 },
            depth: { value: layer.depth || -i * 100 },
            parallaxStrength: { value: layer.parallaxIntensity || 0.1 }
          },
          vertexShader: `
            uniform float time;
            uniform float depth;
            uniform float parallaxStrength;
            varying vec2 vUv;

            void main() {
              vUv = uv;

              // Calculate depth-based displacement
              float depthFactor = 1.0 + (depth * 0.001);

              // Apply gentle wave effect
              float waveX = sin(position.y * 0.01 + time * 0.2) * parallaxStrength;
              float waveY = cos(position.x * 0.01 + time * 0.2) * parallaxStrength;

              vec3 pos = position;
              pos.x += waveX * 10.0;
              pos.y += waveY * 10.0;

              gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
            }
          `,
          fragmentShader: `
            uniform sampler2D map;
            uniform float opacity;
            uniform float time;
            varying vec2 vUv;

            void main() {
              // Apply subtle UV distortion for ethereal effect
              vec2 uv = vUv;
              uv.x += sin(uv.y * 10.0 + time * 0.1) * 0.01;
              uv.y += cos(uv.x * 10.0 + time * 0.1) * 0.01;

              vec4 texColor = texture2D(map, uv);

              // Enhance colors
              texColor.rgb *= 1.2;

              // Add subtle shimmer/glow
              float shimmer = sin(uv.x * 100.0 + uv.y * 100.0 + time * 2.0) * 0.03 + 0.97;
              texColor.rgb *= shimmer;

              gl_FragColor = vec4(texColor.rgb, texColor.a * opacity);

              // Additional blend mode effects
              #ifdef ADDITIVE
                gl_FragColor = vec4(texColor.rgb * opacity, 1.0);
              #endif
            }
          `,
          transparent: true,
          side: THREE.DoubleSide,
          blending: THREE.AdditiveBlending,
          depthWrite: false
        });

        // Create geometry with more segments for smoother deformation
        const plane = new THREE.PlaneGeometry(
          2000 * (layer.scale || 1.0),
          2000 * (layer.scale || 1.0),
          32, 32 // More segments for better wave effects
        );

        // Create mesh
        const mesh = new THREE.Mesh(plane, material);
        mesh.position.z = layer.depth || -i * 100;
        mesh.position.x = 0;
        mesh.position.y = 0;
        mesh.renderOrder = 10 - i; // Render further layers first
        mesh.userData = {
          layerIndex: i,
          rotationSpeed: layer.rotationSpeed || 0.0001,
          parallaxIntensity: layer.parallaxIntensity || 0.1
        };

        // Add subtle animation
        mesh.rotation.z = Math.random() * Math.PI * 2; // Random initial rotation

        // Add to scene
        scene.add(mesh);
        layerMeshes.current.push(mesh);

        logger.info(`Created enhanced celestial layer ${i} at depth ${mesh.position.z}`);
      } catch (error) {
        logger.error(`Failed to create celestial layer ${i}:`, error);
      }
    }
  };

  // Enhanced animation function with all new visual and 3D depth effects
  const animate = () => {
    if (!sceneRef.current || !cameraRef.current || !rendererRef.current) return;

    // Update time for shader animations
    const time = performance.now() * 0.001; // Convert to seconds

    // Update layer positions and effects with enhanced parameters
    const scrollY = window.scrollY;
    layerMeshes.current.forEach((mesh, index) => {
      const material = mesh.material as THREE.ShaderMaterial;
      if (material.uniforms) {
        material.uniforms.time.value = time;
      }

      // Get layer properties from userData with enhanced parameters
      const rotationSpeed = mesh.userData.rotationSpeed || 0.0001;
      const parallaxIntensity = mesh.userData.parallaxIntensity || 0.1;
      const layer = layers[index];
      const perspectiveFactor = layer.perspectiveFactor || 1.0;

      // Apply z-depth transformations for true 3D perspective
      if (layer.transformZ !== undefined) {
        const targetZ = layer.depth || -index * 100;
        mesh.position.z += (targetZ - mesh.position.z) * 0.02; // Smooth transition
      }

      // Rotate each layer at its own speed with slight oscillation for more natural movement
      mesh.rotation.z += rotationSpeed * (1 + Math.sin(time * 0.2) * 0.1);

      if (depthEffect) {
        // Apply enhanced depth-based parallax for scrolling with perspective transform
        const parallaxY = scrollY * (layer.speed || 0.1) * perspectiveFactor;
        // Smooth transition for more fluid movement
        mesh.position.y += (parallaxY - mesh.position.y) * 0.05;
      }

      // Apply enhanced mouse-based parallax with true 3D perspective
      if (mouseInteraction) {
        const depth = layer.depth || -index * 100;
        // Enhanced depth factor calculation for more accurate perspective
        const depthFactor = Math.abs(depth) / (300 * perspectiveFactor);

        // Apply advanced mouse parallax with smooth easing and depth-based intensity
        const targetX = mousePosition.current.x * 35 * parallaxIntensity * depthFactor;
        mesh.position.x += (targetX - mesh.position.x) * 0.03;

        // Only apply Y parallax from mouse if scroll parallax is disabled
        if (!depthEffect) {
          const targetY = mousePosition.current.y * 35 * parallaxIntensity * depthFactor;
          mesh.position.y += (targetY - mesh.position.y) * 0.03;
        }

        // Apply subtle scale variation based on perspective and mouse position
        if (index === 0) { // Only for the first (furthest) layer for subtle effect
          const scaleFactor = 1 + (mousePosition.current.x * mousePosition.current.y) * 0.01;
          mesh.scale.x = 1 * scaleFactor;
          mesh.scale.y = 1 * scaleFactor;
        }
      }

      // Apply subtle wave effect for nebula layers
      if (enableNebulaEffects && index > 0) { // Skip stars layer
        // Create gentle ripple effect
        const waveIntensity = 0.0005 * parallaxIntensity;
        const waveX = Math.sin(time * 0.2 + index) * waveIntensity;
        const waveY = Math.cos(time * 0.3 + index * 0.7) * waveIntensity;

        // Apply subtle distortion
        mesh.position.x += Math.sin(time * 0.5) * waveX * 50;
        mesh.position.y += Math.cos(time * 0.4) * waveY * 50;
      }
    });

    // Animate enhanced star particles
    if (particlesRef.current) {
      const particles = particlesRef.current;

      // Apply complex motion to particle system
      particles.rotation.y = time * 0.05;

      // Subtle oscillation for more dynamic feel
      particles.position.x = Math.sin(time * 0.3) * 5;
      particles.position.y = Math.cos(time * 0.2) * 5;

      // Update particle shader uniforms with additional parameters
      const material = particles.material as THREE.ShaderMaterial;
      if (material.uniforms) {
        material.uniforms.time.value = time;

        // Update camera position for advanced distance calculations
        if (material.uniforms.cameraPosition && cameraRef.current) {
          material.uniforms.cameraPosition.value.copy(cameraRef.current.position);
        }
      }

      // Enhanced twinkling effect for star particles
      if (material.uniforms && material.uniforms.time) {
        // Handled by shader now with more sophisticated twinkling
        // No need for manual size adjustments
      } else {
        // Fallback for basic material
        const sizes = particles.geometry.attributes.size as THREE.BufferAttribute;
        const count = sizes.count;

        // Create temporary array for new sizes
        const newSizes = new Float32Array(count);

        for (let i = 0; i < count; i++) {
          const pulseFactor = Math.sin(time * 3 + i * 0.1) * 0.5 + 0.5;
          const originalSize = (i % 5) + 0.5; // Base size varies
          newSizes[i] = originalSize * (0.8 + pulseFactor * 0.4); // Pulsate between 80-120% of size
        }

        // Update buffer with new values
        sizes.copyArray(newSizes);
        sizes.needsUpdate = true;
      }
    }

    // Animate cosmic dust particles with enhanced 3D depth movement
    if (sceneRef.current.userData.dustParticles) {
      const dustParticles = sceneRef.current.userData.dustParticles as THREE.Points;
      const dustMaterial = dustParticles.material as THREE.ShaderMaterial;

      // Update time uniform for dust animation
      if (dustMaterial.uniforms) {
        dustMaterial.uniforms.time.value = time;
      }

      // Apply gentle rotation for enhanced 3D depth effect
      dustParticles.rotation.y = time * 0.03;
      dustParticles.rotation.x = Math.sin(time * 0.05) * 0.01;

      // Add mouse-reactive parallax to dust particles
      if (mouseInteraction) {
        const mouseX = mousePosition.current.x;
        const mouseY = mousePosition.current.y;

        // Dust particles move with more dramatic parallax (deeper in scene)
        const targetX = -mouseX * 30;
        const targetY = -mouseY * 30;

        // Smooth movement with easing
        dustParticles.position.x += (targetX - dustParticles.position.x) * 0.01;
        dustParticles.position.y += (targetY - dustParticles.position.y) * 0.01;
      }
    }

    // Animate nebula effects with authentic volumetric movement
    if (sceneRef.current.userData.nebulaGroup) {
      const nebulaGroup = sceneRef.current.userData.nebulaGroup as THREE.Group;

      // Apply subtle group movement
      nebulaGroup.rotation.z = Math.sin(time * 0.05) * 0.02;

      // Update each nebula cloud individually
      nebulaGroup.children.forEach((child, index) => {
        // Type check to ensure we're working with a Mesh with ShaderMaterial
        if (child.type === 'Mesh') {
          const nebula = child as THREE.Mesh;
          if (nebula.material instanceof THREE.ShaderMaterial) {
            // Update time uniform for fluid animation
            nebula.material.uniforms.time.value = time + index * 100;

            // Get nebula animation properties
            const userData = nebula.userData;

            // Apply breathing animation (scale pulsation)
            const pulseSpeed = userData.pulseSpeed || 0.2;
            const pulseFactor = userData.pulseFactor || 0.05;
            const pulseScale = 1 + Math.sin(time * pulseSpeed) * pulseFactor;

            // Store original scale if not already saved
            if (!userData.originalScale) {
              userData.originalScale = {
                x: nebula.scale.x,
                y: nebula.scale.y
              };
            }

            // Apply scale with pulsation
            nebula.scale.x = userData.originalScale.x * pulseScale;
            nebula.scale.y = userData.originalScale.y * pulseScale;

            // Apply gentle floating motion
            const floatSpeed = userData.floatSpeed || 0.1;
            const floatAmount = userData.floatAmount || 10;
            nebula.position.x += Math.sin(time * floatSpeed + index) * 0.1;
            nebula.position.y += Math.cos(time * floatSpeed * 0.7 + index) * 0.1;

            // Apply mouse-reactive movement with depth-based intensity
            if (mouseInteraction) {
              const parallaxFactor = 0.02 + index * 0.01; // Each nebula has different parallax sensitivity
              const targetX = -mousePosition.current.x * floatAmount * parallaxFactor;
              const targetY = -mousePosition.current.y * floatAmount * parallaxFactor;

              // Smooth interpolation for natural movement
              nebula.position.x += (targetX - nebula.position.x) * 0.003;
              nebula.position.y += (targetY - nebula.position.y) * 0.003;
            }
          }
        }
      });
    }

    // Update custom post-processing effects
    if (effectComposerRef.current) {
      // Update custom shader uniforms
      effectComposerRef.current.passes.forEach(pass => {
        if (pass instanceof ShaderPass && pass.uniforms.time !== undefined) {
          pass.uniforms.time.value = time;
        }
      });

      effectComposerRef.current.render();
    } else {
      rendererRef.current.render(sceneRef.current, cameraRef.current);
    }

    // Add this line if it's not already in your animation loop, to call the orbit animation
    if (enableOrbits && orbitAnimationRef.current) {
      orbitAnimationRef.current(time);
    }

    // Continue animation loop
    frameId.current = requestAnimationFrame(animate);
  };

  // Enhanced mouse movement handler with advanced 3D parallax effects
  const handleMouseMove = (event: MouseEvent) => {
    if (!mouseInteraction || !interactive) return;

    const { clientX, clientY } = event;

    // Calculate normalized mouse position (-1 to 1)
    const mouseX = (clientX / window.innerWidth) * 2 - 1;
    const mouseY = (clientY / window.innerHeight) * 2 - 1;

    // Update stored mouse position with smooth transition and enhanced damping
    mousePosition.current = {
      x: mousePosition.current.x + (mouseX - mousePosition.current.x) * 0.05,
      y: mousePosition.current.y + (mouseY - mousePosition.current.y) * 0.05
    };

    // Advanced 3D camera rotation with perspective adjustment
    if (cameraRef.current) {
      // Create more natural feeling camera movements
      const targetRotationX = mouseY * 0.08; // Increase for more dramatic effect
      const targetRotationY = mouseX * 0.08;

      // Apply smooth easing with cubic bezier-like motion
      const easeFactor = 0.03;
      cameraRef.current.rotation.x += (targetRotationX - cameraRef.current.rotation.x) * easeFactor;
      cameraRef.current.rotation.y += (targetRotationY - cameraRef.current.rotation.y) * easeFactor;

      // Enhanced 3D camera movement with depth perception
      const moveFactor = 15; // Increase for more dramatic movement
      const targetX = mouseX * moveFactor;
      const targetY = mouseY * moveFactor;

      // Apply smooth position transitions with variable speed based on distance
      const posEaseFactor = 0.01 + 0.02 * Math.abs(targetX - cameraRef.current.position.x) / moveFactor;
      cameraRef.current.position.x += (targetX - cameraRef.current.position.x) * posEaseFactor;
      cameraRef.current.position.y += (targetY - cameraRef.current.position.y) * posEaseFactor;

      // Apply subtle camera field of view changes for enhanced depth
      const defaultFOV = 65;
      const fovVariation = 2; // Subtle FOV change for depth effect
      const targetFOV = defaultFOV + (1 - Math.abs(mouseX * mouseY)) * fovVariation;
      cameraRef.current.fov += (targetFOV - cameraRef.current.fov) * 0.05;
      cameraRef.current.updateProjectionMatrix();

      // Enhanced look-at with slight offset for more natural camera behavior
      const lookAtTarget = new THREE.Vector3(
        -mouseX * 5, // Slight offset from center
        -mouseY * 5,
        0
      );
      cameraRef.current.lookAt(lookAtTarget);
    }

    // Apply mouse parallax to particle system for enhanced depth effect
    if (particlesRef.current) {
      const parallaxFactor = 10; // Control intensity of particle parallax
      const targetX = -mouseX * parallaxFactor;
      const targetY = -mouseY * parallaxFactor;

      particlesRef.current.position.x += (targetX - particlesRef.current.position.x) * 0.01;
      particlesRef.current.position.y += (targetY - particlesRef.current.position.y) * 0.01;
    }

    // Track last position for velocity calculations
    lastMousePosition.current = { x: mouseX, y: mouseY };
  };

  // Enhanced resize handler
  const handleResize = () => {
    if (!cameraRef.current || !rendererRef.current) return;

    // Update camera
    cameraRef.current.aspect = window.innerWidth / window.innerHeight;
    cameraRef.current.updateProjectionMatrix();

    // Update renderer
    rendererRef.current.setSize(window.innerWidth, window.innerHeight);

    // Update effect composer
    if (effectComposerRef.current) {
      effectComposerRef.current.setSize(window.innerWidth, window.innerHeight);

      // Update bloom pass resolution
      const passes = effectComposerRef.current.passes;
      for (const pass of passes) {
        if (pass instanceof UnrealBloomPass) {
          pass.resolution.set(window.innerWidth, window.innerHeight);
        }
      }
    }
  };

  // Setup effect
  useEffect(() => {
    // Initialize Three.js
    const threeContext = initThreeJS();
    if (!threeContext) return;

    const { scene } = threeContext;

    // Load celestial layers
    const loadLayers = async () => {
      setIsLoading(true);
      await createCelestialLayers(scene);
      setIsLoading(false);
    };

    loadLayers();

    // Start animation
    frameId.current = requestAnimationFrame(animate);

    // Add event listeners
    if (interactive) {
      window.addEventListener('mousemove', handleMouseMove);
    }
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      cancelAnimationFrame(frameId.current);
      if (rendererRef.current && rendererRef.current.domElement.parentNode) {
        rendererRef.current.domElement.parentNode.removeChild(rendererRef.current.domElement);
      }
      rendererRef.current?.dispose();
      progressiveLoader.current.dispose();
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
    };
  }, [layers, mouseInteraction, depthEffect, interactive]);

  return (
    <div
      ref={containerRef}
      className="fixed top-0 left-0 w-full h-full overflow-hidden -z-10"
      data-testid="celestial-background"
    >
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-70 z-10">
          <div
            data-testid="loading-spinner"
            role="progressbar"
            aria-label="Loading celestial visualization"
            className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white"
          ></div>
        </div>
      )}
    </div>
  );
};
