// Types for Docker AI Service

export interface ContainerMetrics {
  cpuUsage: number;
  gpuUsage: number;
  memoryUsage: number;
  timestamp: Date;
}

export interface OptimizationSuggestion {
  type: string;
  message: string;
  priority: 'low' | 'medium' | 'high';
}

export interface BirthTimeCalculationInput {
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

export interface BirthTimeCalculationResult {
  rectifiedTime: string;
  confidence: number;
  explanation: string;
}
