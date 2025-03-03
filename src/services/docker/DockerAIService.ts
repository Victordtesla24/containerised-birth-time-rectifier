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

  public static getInstance(): DockerAIService {
    if (!DockerAIService.instance) {
      DockerAIService.instance = new DockerAIService();
    }
    return DockerAIService.instance;
  }

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
      return {
        rectifiedTime: input.time, // Return the input time if AI is disabled
        confidence: 0,
        explanation: 'Docker AI Agent is disabled'
      };
    }

    try {
      // In a real implementation, this would call the AI service API
      // For now, return a simple mock result
      return {
        rectifiedTime: '14:30',
        confidence: 0.85,
        explanation: 'Birth time calculated based on planetary positions.'
      };
    } catch (error) {
      console.error('Error calculating birth time:', error);
      throw error;
    }
  }
}

export default DockerAIService.getInstance(); 