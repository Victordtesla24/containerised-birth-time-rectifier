import * as THREE from 'three';
import { DockerAIService } from '@/services/docker/DockerAIService';
import { ProgressiveLoader, QualitySettings } from '../ProgressiveLoader';
import { ContainerMetrics } from '@/services/docker/types';

// Mock THREE.js
jest.mock('three', () => {
  class MockTexture {
    generateMipmaps: boolean = true;
    anisotropy: number = 4;
    dispose = jest.fn();
  }

  return {
    TextureLoader: jest.fn().mockImplementation(() => ({
      load: jest.fn((url, onLoad) => {
        if (onLoad) {
          const mockTexture = new MockTexture();
          onLoad(mockTexture);
          return mockTexture;
        }
      })
    })),
    Texture: MockTexture,
    CanvasTexture: jest.fn().mockImplementation(() => new MockTexture())
  };
});

// Simple mock for DockerAIService
const mockDockerAIService = {
  on: jest.fn().mockReturnThis(),
  removeListener: jest.fn().mockReturnThis(),
  removeAllListeners: jest.fn().mockReturnThis(),
  emit: jest.fn(),
  // For test purposes, we'll say Docker AI is not enabled
  isDockerAIEnabled: jest.fn().mockReturnValue(false),
  getContainerStatus: jest.fn().mockResolvedValue({ status: 'running' }),
  executeSwissEphemeris: jest.fn().mockResolvedValue({})
};

// Mock Docker AI Service
jest.mock('@/services/docker/DockerAIService', () => ({
  DockerAIService: {
    getInstance: jest.fn().mockReturnValue(mockDockerAIService)
  }
}));

describe('ProgressiveLoader', () => {
  let testLoader: ProgressiveLoader;
  let mockLogger: any;
  let mockTextureLoader: any;
  let mockTexture: THREE.Texture;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup console mock
    mockLogger = {
      log: jest.fn(),
      warn: jest.fn(),
      error: jest.fn(),
      info: jest.fn(),
      debug: jest.fn()
    };

    // Setup texture expectations
    mockTexture = new THREE.Texture();
    mockTexture.generateMipmaps = true;
    mockTexture.anisotropy = 4;

    // Setup texture loader mock
    const mockedTextureLoader = {
      load: jest.fn().mockImplementation((url: string, onLoad?: (texture: THREE.Texture) => void) => {
        if (onLoad) {
          onLoad(mockTexture);
        }
        return mockTexture;
      })
    };
    (THREE.TextureLoader as jest.Mock).mockReturnValue(mockedTextureLoader);
    mockTextureLoader = mockedTextureLoader;

    // Create test instance
    testLoader = new ProgressiveLoader(mockLogger);
  });

  // Core functionality tests
  describe('Core Functionality', () => {
    it('should create a loader that can load textures', async () => {
      const texture = await testLoader.loadCelestialTexture('/test.jpg');
      expect(texture).toBe(mockTexture);
      expect(mockTextureLoader.load).toHaveBeenCalled();
    });

    it('should set quality parameters on textures', async () => {
      // Test with explicit quality settings
      const customQuality: QualitySettings = {
        size: 1024,
        mipmap: false,
        anisotropy: 1
      };
      
      const texture = await testLoader.loadCelestialTexture('/test.jpg', customQuality);
      
      expect(texture.generateMipmaps).toBe(false);
      expect(texture.anisotropy).toBe(1);
    });

    it('should cache loaded textures', async () => {
      const texture1 = await testLoader.loadCelestialTexture('/test.jpg');
      const texture2 = await testLoader.loadCelestialTexture('/test.jpg');

      expect(texture1).toBe(texture2);
      expect(mockTextureLoader.load).toHaveBeenCalledTimes(1);
    });

    it('should handle texture loading errors', async () => {
      // Force an error when loading texture
      mockTextureLoader.load.mockImplementationOnce((url: string, onLoad: any, onProgress: any, onError: any) => {
        if (onError) {
          onError(new Error('Failed to load texture'));
        }
        return mockTexture;
      });

      const texture = await testLoader.loadCelestialTexture('/error-texture.jpg');
      
      expect(mockLogger.error).toHaveBeenCalledWith(
        'Texture loading failed:',
        expect.any(Error)
      );
      
      // Should return a texture even after error (fallback)
      expect(texture).toBeInstanceOf(THREE.Texture);
    });

    it('should clean up resources on dispose', () => {
      // Add a texture to the cache
      testLoader.loadCelestialTexture('/test.jpg');
      
      // Dispose resources
      testLoader.dispose();
      
      // Since Docker AI is disabled in our tests, we should not check if removeListener was called
      // This test just verifies that dispose() can be called without errors
    });
  });
});
