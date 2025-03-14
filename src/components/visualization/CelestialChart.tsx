import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';

interface PlanetData {
  id: string;
  name: string;
  position: number;
  longitude: number;
  house: number;
  sign: string;
  relationship?: string;
  isRetrograde?: boolean;
}

interface CelestialChartProps {
  chartData: {
    planets: PlanetData[];
    houses: any[];
    ascendant?: number;
  };
  className?: string;
  interactive?: boolean;
  animate?: boolean;
}

const PLANET_COLORS = {
  sun: 0xFFCC00,      // Gold
  moon: 0xDDDDDD,     // Silver
  mercury: 0x66CCCC,  // Light blue-green
  venus: 0xFFCCFF,    // Pink
  mars: 0xFF6666,     // Red
  jupiter: 0xCCCC00,  // Yellow-green
  saturn: 0x999999,   // Gray
  uranus: 0x66FFFF,   // Cyan
  neptune: 0x6666FF,  // Blue
  pluto: 0x660000,    // Dark red
  rahu: 0x993399,     // Purple
  ketu: 0x663300,     // Brown
  default: 0xFFFFFF   // White
};

const SIGN_COLORS = {
  "Aries": 0xFF5555,
  "Taurus": 0x88CC88,
  "Gemini": 0xFFFF88,
  "Cancer": 0x8888FF,
  "Leo": 0xFF8800,
  "Virgo": 0x88CCAA,
  "Libra": 0xFFAAFF,
  "Scorpio": 0x880000,
  "Sagittarius": 0xCC8800,
  "Capricorn": 0x666666,
  "Aquarius": 0x00CCFF,
  "Pisces": 0x88AAFF
};

/**
 * CelestialChart component - Renders an interactive 3D visualization of a birth chart
 */
const CelestialChart: React.FC<CelestialChartProps> = ({
  chartData,
  className = '',
  interactive = true,
  animate = true
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const frameRef = useRef<number | null>(null);
  const planetMeshesRef = useRef<THREE.Mesh[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current || !chartData || !chartData.planets || chartData.planets.length === 0) {
      setError("Invalid chart data or container reference");
      return;
    }

    // Set up scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111133);
    sceneRef.current = scene;

    // Add ambient light
    const ambientLight = new THREE.AmbientLight(0x404040);
    scene.add(ambientLight);

    // Add directional light
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(5, 5, 5);
    scene.add(directionalLight);

    // Create camera
    const { width, height } = containerRef.current.getBoundingClientRect();
    const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.z = 20;
    cameraRef.current = camera;

    // Create renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Add controls if interactive
    if (interactive) {
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.25;
      controls.enableZoom = true;
      controlsRef.current = controls;
    }

    // Create zodiac circle
    const zodiacRadius = 12;
    const zodiacGeometry = new THREE.TorusGeometry(zodiacRadius, 0.2, 16, 100);
    const zodiacMaterial = new THREE.MeshBasicMaterial({ color: 0x444466 });
    const zodiacRing = new THREE.Mesh(zodiacGeometry, zodiacMaterial);
    zodiacRing.rotation.x = Math.PI / 2;
    scene.add(zodiacRing);

    // Add zodiac signs
    for (let i = 0; i < 12; i++) {
      const angle = (i * 30) * (Math.PI / 180);
      const signPosition = new THREE.Vector3(
        zodiacRadius * Math.cos(angle),
        0,
        zodiacRadius * Math.sin(angle)
      );

      // Create sign indicator
      const signColor = Object.values(SIGN_COLORS)[i];
      const signGeometry = new THREE.SphereGeometry(0.3, 16, 16);
      const signMaterial = new THREE.MeshBasicMaterial({ color: signColor });
      const signMesh = new THREE.Mesh(signGeometry, signMaterial);
      signMesh.position.copy(signPosition);
      scene.add(signMesh);

      // Add sign labels
      const signNames = [
        "Ari", "Tau", "Gem", "Can", "Leo", "Vir",
        "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"
      ];
      const canvas = document.createElement('canvas');
      canvas.width = 128;
      canvas.height = 64;
      const context = canvas.getContext('2d');
      if (context) {
        context.fillStyle = '#FFFFFF';
        context.font = 'Bold 24px Arial';
        context.textAlign = 'center';
        context.fillText(signNames[i], 64, 32);

        const texture = new THREE.CanvasTexture(canvas);
        const labelMaterial = new THREE.SpriteMaterial({ map: texture });
        const sprite = new THREE.Sprite(labelMaterial);
        sprite.position.copy(signPosition).multiplyScalar(1.1);
        sprite.scale.set(2, 1, 1);
        scene.add(sprite);
      }
    }

    // Add planets
    const planetPositions: THREE.Vector3[] = [];
    planetMeshesRef.current = [];

    chartData.planets.forEach((planet, index) => {
      // Calculate position on the circle based on longitude
      const angle = planet.position * (Math.PI / 180);
      const radius = 8 + (index % 3); // Stagger the planets for visibility
      const position = new THREE.Vector3(
        radius * Math.cos(angle),
        0,
        radius * Math.sin(angle)
      );
      planetPositions.push(position);

      // Create planet mesh
      const planetColor = PLANET_COLORS[planet.id as keyof typeof PLANET_COLORS] || PLANET_COLORS.default;
      const planetGeometry = new THREE.SphereGeometry(0.4, 32, 32);
      const planetMaterial = new THREE.MeshStandardMaterial({
        color: planetColor,
        emissive: 0x222222,
        roughness: 0.5,
        metalness: 0.8
      });

      // Color based on relationship with ascendant
      if (planet.relationship === 'friendly') {
        planetMaterial.emissive = new THREE.Color(0x00FF00);
        planetMaterial.emissiveIntensity = 0.5;
      } else if (planet.relationship === 'enemy') {
        planetMaterial.emissive = new THREE.Color(0xFF0000);
        planetMaterial.emissiveIntensity = 0.5;
      }

      const planetMesh = new THREE.Mesh(planetGeometry, planetMaterial);
      planetMesh.position.copy(position);
      planetMesh.userData = { ...planet };
      scene.add(planetMesh);
      planetMeshesRef.current.push(planetMesh);

      // Add planet label
      const canvas = document.createElement('canvas');
      canvas.width = 128;
      canvas.height = 64;
      const context = canvas.getContext('2d');
      if (context) {
        context.fillStyle = '#FFFFFF';
        context.font = 'Bold 20px Arial';
        context.textAlign = 'center';
        context.fillText(planet.name, 64, 32);

        const texture = new THREE.CanvasTexture(canvas);
        const labelMaterial = new THREE.SpriteMaterial({ map: texture });
        const sprite = new THREE.Sprite(labelMaterial);
        sprite.position.copy(position).add(new THREE.Vector3(0, 0.8, 0));
        sprite.scale.set(2, 1, 1);
        scene.add(sprite);
      }
    });

    // Mark ascendant with special indicator
    if (chartData.ascendant !== undefined) {
      const ascAngle = chartData.ascendant * (Math.PI / 180);
      const ascPosition = new THREE.Vector3(
        zodiacRadius * Math.cos(ascAngle),
        0,
        zodiacRadius * Math.sin(ascAngle)
      );

      const ascGeometry = new THREE.ConeGeometry(0.5, 1, 4);
      const ascMaterial = new THREE.MeshBasicMaterial({ color: 0xFFFF00 });
      const ascMesh = new THREE.Mesh(ascGeometry, ascMaterial);
      ascMesh.position.copy(ascPosition);
      ascMesh.lookAt(new THREE.Vector3(0, 0, 0));
      scene.add(ascMesh);

      // Add "ASC" label
      const canvas = document.createElement('canvas');
      canvas.width = 128;
      canvas.height = 64;
      const context = canvas.getContext('2d');
      if (context) {
        context.fillStyle = '#FFFF00';
        context.font = 'Bold 24px Arial';
        context.textAlign = 'center';
        context.fillText('ASC', 64, 32);

        const texture = new THREE.CanvasTexture(canvas);
        const labelMaterial = new THREE.SpriteMaterial({ map: texture });
        const sprite = new THREE.Sprite(labelMaterial);
        sprite.position.copy(ascPosition).multiplyScalar(1.15);
        sprite.scale.set(2, 1, 1);
        scene.add(sprite);
      }
    }

    // Animation loop
    const animate = () => {
      frameRef.current = requestAnimationFrame(animate);

      if (controlsRef.current) {
        controlsRef.current.update();
      }

      renderer.render(scene, camera);
    };

    // Start animation
    animate();
    setIsLoading(false);

    // Handle window resize
    const handleResize = () => {
      if (containerRef.current && cameraRef.current && rendererRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        cameraRef.current.aspect = width / height;
        cameraRef.current.updateProjectionMatrix();
        rendererRef.current.setSize(width, height);
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
      if (rendererRef.current && containerRef.current) {
        containerRef.current.removeChild(rendererRef.current.domElement);
      }
    };
  }, [chartData, interactive, animate]);

  if (error) {
    return (
      <div className={`celestial-chart-error ${className}`}>
        <div className="bg-red-800 bg-opacity-50 p-4 rounded-lg">
          <p className="text-red-200">Error: {error}</p>
        </div>
      </div>
    );
  }

  if (isLoading || !chartData) {
    return (
      <div className={`celestial-chart-loading ${className}`}>
        <div className="flex items-center justify-center h-64 bg-indigo-800 bg-opacity-50 rounded-lg">
          <p className="text-indigo-200">Loading 3D chart...</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`celestial-chart relative ${className}`}
      style={{ width: '100%', height: '400px' }}
    />
  );
};

export default CelestialChart;
