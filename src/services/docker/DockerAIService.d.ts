import { EventEmitter } from 'events';
import { ContainerMetrics, OptimizationSuggestion, BirthTimeCalculationInput, BirthTimeCalculationResult } from './types';

export declare class DockerAIService extends EventEmitter {
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

  // Add the calculateBirthTime method
  public calculateBirthTime(input: BirthTimeCalculationInput): Promise<BirthTimeCalculationResult>;
}

declare const instance: DockerAIService;
export default instance;
