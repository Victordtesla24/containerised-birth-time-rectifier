// Type declarations for local modules

declare module '@/services/docker/DockerAIService' {
  export interface AIResponse {
    message: string;
    confidence: number;
    [key: string]: any;
  }

  export interface AIProcessOptions {
    model?: string;
    temperature?: number;
    maxTokens?: number;
    [key: string]: any;
  }

  export class DockerAIService {
    constructor(options?: any);
    processRequest(prompt: string, options?: AIProcessOptions): Promise<AIResponse>;
    getStatus(): Promise<{ status: string; message: string }>;

    // Add missing methods
    static getInstance(): DockerAIService;
    isDockerAIEnabled(): boolean;
    on(event: string, callback: Function): void;
    removeListener(event: string, callback: Function): void;
    optimizeContainers(): Promise<void>;
  }
}

declare module '@/utils/logger' {
  export interface LogOptions {
    level?: 'info' | 'warn' | 'error' | 'debug';
    timestamp?: boolean;
    context?: string;
    [key: string]: any;
  }

  export interface Logger {
    info(message: string, options?: LogOptions): void;
    warn(message: string, options?: LogOptions): void;
    error(message: string | Error, options?: LogOptions): void;
    debug(message: string, options?: LogOptions): void;
  }

  export const logger: Logger;
}

declare module '@/services/docker/types' {
  export interface ContainerMetrics {
    cpu: number;
    memory: number;
    network: {
      rx: number;
      tx: number;
    };
    [key: string]: any;
  }
}

declare module '@/components/common/CelestialBody' {
  import * as React from 'react';

  export interface CelestialBodyProps {
    src: string;
    alt?: string;
    size?: 'small' | 'medium' | 'large' | string;
    glowIntensity?: number;
    glowColor?: string;
    rotationSpeed?: number;
    opacity?: number;
    fallbackColor?: string;
    children?: React.ReactNode;
    className?: string;
    type?: string;
    rotate?: boolean;
    glow?: boolean;
  }

  export const CelestialBody: React.FC<CelestialBodyProps>;
}

declare module '@/utils/planetImages' {
  export function getPlanetImagePath(planetName: string): string;
  export function getPlanetFallbackColor(planetName: string): string;
  export function getPlanetGlowColor(planetName: string): string;
}

declare module '@/components/visualization/canvas' {
  import * as React from 'react';

  export interface CelestialBackgroundProps {
    layers?: any[];
    mouseInteraction?: boolean;
    depthEffect?: boolean;
    interactive?: boolean;
    bloomStrength?: number;
    bloomRadius?: number;
    particleCount?: number;
    enableShootingStars?: boolean;
    enableOrbits?: boolean;
    enableNebulaEffects?: boolean;
    quality?: 'low' | 'medium' | 'high';
    perspectiveDepth?: number;
  }

  export const CelestialBackground: React.FC<CelestialBackgroundProps>;
}
