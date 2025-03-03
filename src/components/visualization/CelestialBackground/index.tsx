import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { ProgressiveLoader, QualitySettings } from './ProgressiveLoader';
import { DockerAIService } from '@/services/docker/DockerAIService';
import { logger } from '@/utils/logger';

export interface CelestialLayer {
  texture: string;
  speed: number;
  depth?: number;
  opacity?: number;
  scale?: number;
}

export interface CelestialBackgroundProps {
  layers?: CelestialLayer[];
  mouseInteraction?: boolean;
  depthEffect?: boolean;
  interactive?: boolean;
}

export const CelestialBackground: React.FC<CelestialBackgroundProps> = ({
  layers = [
    { texture: '/textures/stars.jpg', speed: 0.1, depth: -300, opacity: 1.0, scale: 1.2 },
    { texture: '/textures/nebula.jpg', speed: 0.2, depth: -200, opacity: 0.8, scale: 1.1 },
    { texture: '/textures/galaxies.jpg', speed: 0.3, depth: -100, opacity: 0.7, scale: 1.0 },
    { texture: '/textures/dust.jpg', speed: 0.4, depth: -50, opacity: 0.5, scale: 0.9 }
  ],
  mouseInteraction = true,
  depthEffect = true,
  interactive = true
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
  
  // Define quality settings
  const highQuality: QualitySettings = { size: 2048, mipmap: true, anisotropy: 4 };
  const mediumQuality: QualitySettings = { size: 1024, mipmap: true, anisotropy: 2 };
  
  // Initialize Three.js scene
  const initThreeJS = () => {
    const container = containerRef.current;
    if (!container) return;
    
    // Create scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    
    // Create camera
    const camera = new THREE.PerspectiveCamera(
      75, 
      window.innerWidth / window.innerHeight, 
      0.1, 
      1000
    );
    camera.position.z = 300;
    cameraRef.current = camera;
    
    // Create renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setClearColor(0x000020, 1);
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;
    
    return { scene, camera, renderer };
  };
  
  // Create celestial layers
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
        
        // Create material
        const material = new THREE.MeshBasicMaterial({
          map: texture,
          transparent: true,
          opacity: layer.opacity || 1.0,
          depthWrite: false,
          side: THREE.DoubleSide,
          blending: THREE.AdditiveBlending
        });
        
        // Create geometry
        const plane = new THREE.PlaneGeometry(
          2000 * (layer.scale || 1.0), 
          2000 * (layer.scale || 1.0)
        );
        
        // Create mesh
        const mesh = new THREE.Mesh(plane, material);
        mesh.position.z = layer.depth || -i * 100;
        mesh.position.x = 0;
        mesh.position.y = 0;
        mesh.renderOrder = 10 - i; // Render further layers first
        
        // Add subtle animation
        mesh.rotation.z = Math.random() * Math.PI * 2; // Random initial rotation
        
        // Add to scene
        scene.add(mesh);
        layerMeshes.current.push(mesh);
        
        logger.info(`Created celestial layer ${i} at depth ${mesh.position.z}`);
      } catch (error) {
        logger.error(`Failed to create celestial layer ${i}:`, error);
      }
    }
  };
  
  // Animation function
  const animate = () => {
    if (!sceneRef.current || !cameraRef.current || !rendererRef.current) return;
    
    // Update layer positions based on scroll
    const scrollY = window.scrollY;
    layerMeshes.current.forEach((mesh, index) => {
      if (depthEffect) {
        // Apply depth-based parallax
        const layer = layers[index];
        const parallaxY = scrollY * (layer.speed || 0.1);
        mesh.position.y = parallaxY;
      }
    });
    
    // Render scene
    rendererRef.current.render(sceneRef.current, cameraRef.current);
    
    // Continue animation loop
    frameId.current = requestAnimationFrame(animate);
  };
  
  // Handle mouse movement
  const handleMouseMove = (event: MouseEvent) => {
    if (!mouseInteraction || !interactive) return;
    
    const { clientX, clientY } = event;
    
    // Calculate normalized mouse position (-1 to 1)
    const mouseX = (clientX / window.innerWidth) * 2 - 1;
    const mouseY = (clientY / window.innerHeight) * 2 - 1;
    
    // Smoothly rotate camera slightly based on mouse position
    if (cameraRef.current) {
      const targetRotationX = mouseY * 0.05;
      const targetRotationY = mouseX * 0.05;
      
      cameraRef.current.rotation.x += (targetRotationX - cameraRef.current.rotation.x) * 0.05;
      cameraRef.current.rotation.y += (targetRotationY - cameraRef.current.rotation.y) * 0.05;
    }
    
    // Apply parallax effect to each layer based on its depth
    layerMeshes.current.forEach((mesh, index) => {
      const layer = layers[index];
      const depth = layer.depth || -index * 100;
      const parallaxFactor = (300 + depth) / 600; // Normalize based on depth
      
      mesh.position.x = -mouseX * 20 * parallaxFactor;
      if (!depthEffect) {
        // Only apply Y parallax here if not using scroll-based Y parallax
        mesh.position.y = mouseY * 20 * parallaxFactor;
      }
    });
    
    // Update last mouse position
    lastMousePosition.current = { x: mouseX, y: mouseY };
  };
  
  // Handle resize
  const handleResize = () => {
    if (!cameraRef.current || !rendererRef.current) return;
    
    // Update camera
    cameraRef.current.aspect = window.innerWidth / window.innerHeight;
    cameraRef.current.updateProjectionMatrix();
    
    // Update renderer
    rendererRef.current.setSize(window.innerWidth, window.innerHeight);
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