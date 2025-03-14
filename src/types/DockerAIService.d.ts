import { EventEmitter } from 'events';

// Define the input interface for birth time calculation
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

// Define the result interface for birth time calculation
interface BirthTimeCalculationResult {
  rectifiedTime: string;
  confidence: number;
  explanation: string;
}

// Declare the module for the Docker AI Service
declare module '@/services/docker/DockerAIService' {
  interface ContainerMetrics {
    cpuUsage: number;
    gpuUsage: number;
    memoryUsage: number;
    timestamp: Date;
  }

  interface OptimizationSuggestion {
    type: string;
    message: string;
    priority: 'low' | 'medium' | 'high';
  }

  export class DockerAIService extends EventEmitter {
    private static instance: DockerAIService | null;
    private metricsHistory: ContainerMetrics[];
    private readonly maxHistoryLength: number;
    private isEnabled: boolean;
    private metricsInterval: NodeJS.Timeout | null;

    private constructor();

    public static getInstance(): DockerAIService;
    public static resetInstance(): void;

    private initializeMetricsCollection(): void;
    private updateMetricsHistory(metrics: ContainerMetrics): void;

    public dispose(): void;
    public collectMetrics(): Promise<ContainerMetrics>;
    public optimizeContainers(): Promise<OptimizationSuggestion[]>;
    public handleContainerFailure(error: Error): string;
    public isDockerAIEnabled(): boolean;
    public setEnabled(enabled: boolean): void;

    // Add the calculateBirthTime method that was missing
    public calculateBirthTime(input: BirthTimeCalculationInput): Promise<BirthTimeCalculationResult>;
  }

  const instance: DockerAIService;
  export default instance;
}
