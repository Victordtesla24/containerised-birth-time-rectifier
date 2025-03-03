export interface ContainerMetrics {
  cpuUsage: number;
  gpuUsage: number;
  memoryUsage: number;
  timestamp: Date;
}

export interface OptimizationSuggestion {
  type: 'cpu' | 'memory' | 'gpu';
  message: string;
  priority: 'high' | 'medium' | 'low';
} 