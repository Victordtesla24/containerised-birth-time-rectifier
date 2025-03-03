import { DockerAIService } from '../DockerAIService';
import { ContainerMetrics } from '../types';

describe('DockerAIService', () => {
  let dockerAIService: DockerAIService;

  beforeEach(() => {
    // Reset environment variables
    delete process.env.DOCKER_AI_AGENT_ENABLED;
    
    // Reset singleton instance
    DockerAIService.resetInstance();
    
    // Create new instance
    dockerAIService = DockerAIService.getInstance();
  });

  afterEach(() => {
    // Clean up service
    DockerAIService.resetInstance();
  });

  describe('Initialization', () => {
    it('should create a singleton instance', () => {
      const instance1 = DockerAIService.getInstance();
      const instance2 = DockerAIService.getInstance();
      expect(instance1).toBe(instance2);
    });

    it('should initialize with Docker AI Agent disabled when env var is not set', () => {
      expect(dockerAIService.isDockerAIEnabled()).toBe(false);
    });
  });

  describe('Container Optimization', () => {
    it('should return empty suggestions when Docker AI Agent is disabled', async () => {
      const suggestions = await dockerAIService.optimizeContainers();
      expect(suggestions).toEqual([]);
    });

    it('should generate optimization suggestions for high CPU usage', async () => {
      // Enable Docker AI Agent
      dockerAIService.setEnabled(true);

      // Mock metrics collection
      jest.spyOn(dockerAIService as any, 'collectMetrics').mockResolvedValue({
        cpuUsage: 90,
        gpuUsage: 50,
        memoryUsage: 60,
        timestamp: new Date()
      });

      const suggestions = await dockerAIService.optimizeContainers();
      expect(suggestions).toHaveLength(1);
      expect(suggestions[0].type).toBe('cpu');
      expect(suggestions[0].priority).toBe('high');
    });

    it('should generate optimization suggestions for high GPU usage', async () => {
      // Enable Docker AI Agent
      dockerAIService.setEnabled(true);

      // Mock metrics collection
      jest.spyOn(dockerAIService as any, 'collectMetrics').mockResolvedValue({
        cpuUsage: 50,
        gpuUsage: 90,
        memoryUsage: 60,
        timestamp: new Date()
      });

      const suggestions = await dockerAIService.optimizeContainers();
      expect(suggestions).toHaveLength(1);
      expect(suggestions[0].type).toBe('gpu');
      expect(suggestions[0].priority).toBe('high');
    });
  });

  describe('Metrics Collection', () => {
    it('should collect and store metrics', async () => {
      // Enable Docker AI Agent
      dockerAIService.setEnabled(true);

      const metrics = await dockerAIService.collectMetrics();
      
      expect(metrics).toHaveProperty('cpuUsage');
      expect(metrics).toHaveProperty('gpuUsage');
      expect(metrics).toHaveProperty('memoryUsage');
      expect(metrics).toHaveProperty('timestamp');
    });

    it('should maintain metrics history within limit', async () => {
      // Enable Docker AI Agent
      dockerAIService.setEnabled(true);
      const maxLength = 100;

      // Add more metrics than the limit
      for (let i = 0; i < maxLength + 10; i++) {
        const metrics: ContainerMetrics = {
          cpuUsage: i,
          gpuUsage: i,
          memoryUsage: i,
          timestamp: new Date()
        };
        (dockerAIService as any).updateMetricsHistory(metrics);
      }

      expect((dockerAIService as any).metricsHistory.length).toBe(maxLength);
      expect((dockerAIService as any).metricsHistory[maxLength - 1].cpuUsage).toBe(maxLength + 9);
    });
  });

  describe('Failure Handling', () => {
    it('should handle container failures when enabled', async () => {
      // Enable Docker AI Agent
      dockerAIService.setEnabled(true);

      const error = new Error('Test error');
      const message = dockerAIService.handleContainerFailure(error);
      
      expect(message).toContain('Container failure detected');
      expect(message).toContain('Test error');
    });

    it('should return disabled message when Docker AI Agent is disabled', async () => {
      const error = new Error('Test error');
      const message = dockerAIService.handleContainerFailure(error);
      expect(message).toBe('Docker AI Agent is disabled');
    });
  });

  describe('Event Emission', () => {
    it('should emit metrics-updated event when metrics are collected', async () => {
      // Enable Docker AI Agent
      dockerAIService.setEnabled(true);

      const metricsPromise = new Promise<void>((resolve) => {
        dockerAIService.once('metrics-updated', (metrics) => {
          expect(metrics).toHaveProperty('cpuUsage');
          expect(metrics).toHaveProperty('gpuUsage');
          expect(metrics).toHaveProperty('memoryUsage');
          expect(metrics).toHaveProperty('timestamp');
          resolve();
        });
      });

      // Wait for metrics event
      await metricsPromise;
    }, 10000); // Increase timeout to 10 seconds
  });
}); 