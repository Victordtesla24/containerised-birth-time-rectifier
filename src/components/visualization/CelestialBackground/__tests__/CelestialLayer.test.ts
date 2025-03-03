import * as THREE from 'three';
import { CelestialLayer } from '../CelestialLayer';
import { ProgressiveLoader } from '../ProgressiveLoader';
import { CelestialLayerConfig } from '../types';

jest.mock('three');
jest.mock('../ProgressiveLoader');

describe('CelestialLayer', () => {
  let mockScene: THREE.Scene;
  let mockLoader: jest.Mocked<ProgressiveLoader>;
  let mockConfig: CelestialLayerConfig;

  beforeEach(() => {
    // Mock Three.js classes with proper type casting
    (THREE.PlaneGeometry as unknown as jest.Mock).mockImplementation(() => ({
      dispose: jest.fn(),
    }));

    (THREE.ShaderMaterial as unknown as jest.Mock).mockImplementation(() => ({
      uniforms: {
        time: { value: 0 },
        texture: { value: null },
        opacity: { value: 1.0 },
        parallaxOffset: { value: new THREE.Vector2() },
      },
      dispose: jest.fn(),
    }));

    (THREE.Mesh as unknown as jest.Mock).mockImplementation(() => ({
      position: {
        set: jest.fn(),
        x: 0,
        y: 0,
        z: 0,
      },
      geometry: {
        dispose: jest.fn(),
      },
      material: {
        dispose: jest.fn(),
        uniforms: {
          time: { value: 0 },
          texture: { value: null },
          opacity: { value: 1.0 },
          parallaxOffset: { value: new THREE.Vector2() },
        },
      },
      removeFromParent: jest.fn(),
    }));

    // Mock scene
    mockScene = {
      add: jest.fn(),
    } as unknown as THREE.Scene;

    // Mock loader with proper typing
    mockLoader = {
      loadCelestialTexture: jest.fn().mockResolvedValue(new THREE.Texture()),
    } as unknown as jest.Mocked<ProgressiveLoader>;

    // Mock config
    mockConfig = {
      depth: 0,
      content: 'stars',
      parallaxFactor: 0.1,
      position: { x: 0, y: 0, z: 0 },
      loader: mockLoader,
      scene: mockScene,
    };
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('creates a celestial layer with correct configuration', () => {
    const layer = new CelestialLayer(mockConfig);
    expect(mockScene.add).toHaveBeenCalled();
  });

  it('loads texture on initialization', () => {
    const layer = new CelestialLayer(mockConfig);
    expect(mockLoader.loadCelestialTexture).toHaveBeenCalled();
  });

  it('updates position based on scroll', () => {
    const layer = new CelestialLayer(mockConfig);
    const scrollPosition = 100;
    layer.updatePosition(scrollPosition);

    // Get the mesh from the private field using type assertion
    const mesh = (layer as any).mesh;
    expect(mesh.position.set).toHaveBeenCalled();
  });

  it('handles quality changes', () => {
    const layer = new CelestialLayer(mockConfig);
    layer.setQuality('low');
    expect(mockLoader.loadCelestialTexture).toHaveBeenCalledTimes(2);
  });

  it('disposes resources properly', () => {
    const layer = new CelestialLayer(mockConfig);
    layer.dispose();

    // Get the mesh from the private field using type assertion
    const mesh = (layer as any).mesh;
    expect(mesh.geometry.dispose).toHaveBeenCalled();
    expect(mesh.material.dispose).toHaveBeenCalled();
    expect(mesh.removeFromParent).toHaveBeenCalled();
  });

  it('handles texture loading errors gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    mockLoader.loadCelestialTexture = jest.fn().mockRejectedValue(new Error('Load failed'));

    const layer = new CelestialLayer(mockConfig);
    await new Promise(resolve => setTimeout(resolve, 0)); // Wait for async operations

    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it('updates shader uniforms on position change', () => {
    const layer = new CelestialLayer(mockConfig);
    const scrollPosition = 100;
    layer.updatePosition(scrollPosition);

    // Get the material from the private field using type assertion
    const material = (layer as any).material;
    expect(material.uniforms.time.value).toBeDefined();
    expect(material.uniforms.parallaxOffset.value).toBeDefined();
  });

  it('maintains initial position reference', () => {
    const layer = new CelestialLayer(mockConfig);
    const scrollPosition = 100;
    layer.updatePosition(scrollPosition);
    layer.updatePosition(0);

    // Get the mesh from the private field using type assertion
    const mesh = (layer as any).mesh;
    expect(mesh.position.set).toHaveBeenCalledWith(0, 0, 0);
  });

  it('skips quality update if same quality requested', () => {
    const layer = new CelestialLayer(mockConfig);
    const initialCalls = mockLoader.loadCelestialTexture.mock.calls.length;
    layer.setQuality('high'); // Default is already high
    expect(mockLoader.loadCelestialTexture).toHaveBeenCalledTimes(initialCalls);
  });
}); 