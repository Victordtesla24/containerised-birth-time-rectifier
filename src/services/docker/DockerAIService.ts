import { EventEmitter } from 'events';
import { ContainerMetrics, OptimizationSuggestion } from './types';

// Add interface for birth time calculation
interface BirthTimeCalculationInput {
  date: string;
  time: string;
  place: string;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  timezone: string;
  name: string;
}

interface BirthTimeCalculationResult {
  rectifiedTime: string;
  confidence: number;
  explanation: string;
}

/**
 * DockerAIService - Singleton service for Docker container optimization and monitoring
 */
export class DockerAIService extends EventEmitter {
  private static instance: DockerAIService | null = null;
  private metricsHistory: ContainerMetrics[] = [];
  private readonly maxHistoryLength = 100;
  private isEnabled: boolean;
  private metricsInterval: NodeJS.Timeout | null = null;

  private constructor() {
    super();
    this.isEnabled = process.env.DOCKER_AI_AGENT_ENABLED === 'true';
    if (this.isEnabled) {
      this.initializeMetricsCollection();
    }
  }

  /**
   * Get the singleton instance of DockerAIService
   */
  public static getInstance(): DockerAIService {
    if (!DockerAIService.instance) {
      DockerAIService.instance = new DockerAIService();
    }
    return DockerAIService.instance;
  }

  /**
   * Reset the singleton instance (for testing purposes)
   */
  public static resetInstance(): void {
    if (DockerAIService.instance) {
      DockerAIService.instance.dispose();
      DockerAIService.instance = null;
    }
  }

  private initializeMetricsCollection(): void {
    if (!this.isEnabled) return;

    this.metricsInterval = setInterval(async () => {
      try {
        const metrics = await this.collectMetrics();
        this.updateMetricsHistory(metrics);
        this.emit('metrics-updated', metrics);
      } catch (error) {
        console.error('Failed to collect metrics:', error);
      }
    }, 1000); // Collect metrics every second for testing
  }

  private updateMetricsHistory(metrics: ContainerMetrics): void {
    this.metricsHistory.push(metrics);
    if (this.metricsHistory.length > this.maxHistoryLength) {
      this.metricsHistory.shift();
    }
  }

  public dispose(): void {
    if (this.metricsInterval) {
      clearInterval(this.metricsInterval);
      this.metricsInterval = null;
    }
    this.removeAllListeners();
    this.metricsHistory = [];
  }

  public async collectMetrics(): Promise<ContainerMetrics> {
    if (!this.isEnabled) {
      return {
        cpuUsage: 0,
        gpuUsage: 0,
        memoryUsage: 0,
        timestamp: new Date()
      };
    }

    // Simulate metrics collection for now
    return {
      cpuUsage: Math.random() * 100,
      gpuUsage: Math.random() * 100,
      memoryUsage: Math.random() * 100,
      timestamp: new Date()
    };
  }

  public async optimizeContainers(): Promise<OptimizationSuggestion[]> {
    if (!this.isEnabled) {
      return [];
    }

    const metrics = await this.collectMetrics();
    const suggestions: OptimizationSuggestion[] = [];

    if (metrics.cpuUsage > 80) {
      suggestions.push({
        type: 'cpu',
        message: 'High CPU usage detected. Consider scaling horizontally.',
        priority: 'high'
      });
    }

    if (metrics.gpuUsage > 80) {
      suggestions.push({
        type: 'gpu',
        message: 'High GPU usage detected. Consider reducing texture quality.',
        priority: 'high'
      });
    }

    return suggestions;
  }

  public handleContainerFailure(error: Error): string {
    if (!this.isEnabled) {
      return 'Docker AI Agent is disabled';
    }
    return `Container failure detected: ${error.message}`;
  }

  public isDockerAIEnabled(): boolean {
    return this.isEnabled;
  }

  public setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
    if (this.isEnabled) {
      this.initializeMetricsCollection();
    } else if (this.metricsInterval) {
      clearInterval(this.metricsInterval);
      this.metricsInterval = null;
    }
  }

  // Add the calculateBirthTime method
  public async calculateBirthTime(input: BirthTimeCalculationInput): Promise<BirthTimeCalculationResult> {
    if (!this.isEnabled) {
      throw new Error('Docker AI Agent is disabled - Cannot calculate birth time');
    }

    try {
      // Get the API URL from environment variables or use default
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // Call the real AI service API endpoint for birth time calculation
      const response = await fetch(`${apiUrl}/api/chart/rectify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          birthDetails: {
            birthDate: input.date,
            birthTime: input.time,
            birthCity: input.place,
            latitude: input.coordinates.latitude,
            longitude: input.coordinates.longitude,
            timezone: input.timezone,
            name: input.name
          }
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`AI service responded with ${response.status}: ${errorText}`);
      }

      const data = await response.json();

      return {
        rectifiedTime: data.suggestedTime || data.rectifiedTime,
        confidence: data.confidence || 0,
        explanation: data.explanation || 'Birth time calculated based on astrological analysis.'
      };
    } catch (error) {
      console.error('Error calculating birth time:', error);
      throw error;
    }
  }
}

// Export the singleton instance as default
const instance = DockerAIService.getInstance();
export default instance;
