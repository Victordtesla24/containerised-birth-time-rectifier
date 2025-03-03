import * as THREE from 'three';
import { DockerAIService } from '@/services/docker/DockerAIService';
import { ContainerMetrics } from '@/services/docker/types';

// Custom logger interface that matches our needs
interface CustomLogger {
  error: (message: string, ...args: any[]) => void;
  warn: (message: string, ...args: any[]) => void;
  info: (message: string, ...args: any[]) => void;
  debug: (message: string, ...args: any[]) => void;
}

export interface QualitySettings {
  size: number;
  mipmap: boolean;
  anisotropy: number;
}

interface TextureCache {
  texture: THREE.Texture;
  quality: QualitySettings;
  lastUsed: number;
}

export class ProgressiveLoader {
  private textureLoader: THREE.TextureLoader;
  private textureCache: Map<string, Map<string, THREE.Texture>>;
  private dockerAIService: DockerAIService;
  private currentQuality: QualitySettings;
  private logger: CustomLogger;

  constructor(logger: CustomLogger) {
    this.textureLoader = new THREE.TextureLoader();
    this.textureCache = new Map();
    this.dockerAIService = DockerAIService.getInstance();
    this.currentQuality = {
      size: 2048,
      mipmap: true,
      anisotropy: 4
    };
    this.logger = logger;

    // Subscribe to Docker AI metrics updates
    if (this.dockerAIService.isDockerAIEnabled()) {
      this.dockerAIService.on('metrics-updated', this.adjustResourceUsage.bind(this));
    }
  }

  private async adjustResourceUsage(metrics: ContainerMetrics): Promise<void> {
    try {
      if ('error' in metrics) {
        throw new Error('Resource monitoring failed');
      }

      if (metrics.gpuUsage > 80) {
        this.currentQuality = {
          size: 1024,
          mipmap: false,
          anisotropy: 1
        };
      } else if (metrics.gpuUsage > 60) {
        this.currentQuality = {
          size: 1024,
          mipmap: true,
          anisotropy: 2
        };
      } else {
        this.currentQuality = {
          size: 2048,
          mipmap: true,
          anisotropy: 4
        };
      }
    } catch (error) {
      this.logger.error('Failed to adjust resource usage:', error);
    }
  }

  public async loadCelestialTexture(
    url: string,
    quality: QualitySettings = this.currentQuality
  ): Promise<THREE.Texture> {
    const qualityKey = `${quality.size}-${quality.mipmap}-${quality.anisotropy}`;
    
    // Check cache first
    if (!this.textureCache.has(url)) {
      this.textureCache.set(url, new Map());
    }
    const urlCache = this.textureCache.get(url)!;
    
    if (urlCache.has(qualityKey)) {
      return urlCache.get(qualityKey)!;
    }

    try {
      const texture = await new Promise<THREE.Texture>((resolve, reject) => {
        this.textureLoader.load(
          url,
          (texture) => {
            texture.generateMipmaps = quality.mipmap;
            texture.anisotropy = quality.anisotropy;
            resolve(texture);
          },
          undefined,
          (error) => reject(error)
        );
      });

      urlCache.set(qualityKey, texture);
      return texture;
    } catch (error) {
      this.logger.error('Texture loading failed:', error);
      return this.createFallbackTexture();
    }
  }

  private createFallbackTexture(): THREE.Texture {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = 64;
      canvas.height = 64;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        throw new Error('Could not get 2D context');
      }
      ctx.fillStyle = '#444444';
      ctx.fillRect(0, 0, 64, 64);
      return new THREE.CanvasTexture(canvas);
    } catch (error) {
      this.logger.error('Failed to create fallback texture:', error);
      // Return a basic texture if canvas creation fails
      return new THREE.Texture();
    }
  }

  public dispose(): void {
    this.textureCache.forEach((qualityMap) => {
      qualityMap.forEach((texture) => texture.dispose());
    });
    this.textureCache.clear();
    if (this.dockerAIService.isDockerAIEnabled()) {
      this.dockerAIService.removeListener('metrics-updated', this.adjustResourceUsage.bind(this));
    }
  }
}

class ResourceMonitor {
  private lastCheck: number = 0;
  private readonly CHECK_INTERVAL = 5000; // 5 seconds
  private dockerAIService: DockerAIService;
  private logger: CustomLogger;

  constructor(logger: CustomLogger) {
    this.dockerAIService = DockerAIService.getInstance();
    this.logger = logger;
  }

  public async checkResources(): Promise<void> {
    const now = Date.now();
    if (now - this.lastCheck < this.CHECK_INTERVAL) {
      return;
    }

    this.lastCheck = now;
    try {
      const metrics = await this.dockerAIService.optimizeContainers();
      // Resource monitoring logic will be implemented here
      // based on Docker AI Agent's capabilities
    } catch (error) {
      this.logger.error('Failed to check resources:', error);
    }
  }
}
