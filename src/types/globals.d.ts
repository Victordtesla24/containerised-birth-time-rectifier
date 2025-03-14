// Global type declarations

// DockerAIService types
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

declare module '@/services/docker/DockerAIService' {
  import { EventEmitter } from 'events';

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

    private constructor();

    public static getInstance(): DockerAIService;
    public static resetInstance(): void;

    public dispose(): void;
    public collectMetrics(): Promise<ContainerMetrics>;
    public optimizeContainers(): Promise<OptimizationSuggestion[]>;
    public handleContainerFailure(error: Error): string;
    public isDockerAIEnabled(): boolean;
    public setEnabled(enabled: boolean): void;

    // Add the calculateBirthTime method
    public calculateBirthTime(input: BirthTimeCalculationInput): Promise<BirthTimeCalculationResult>;
  }

  const instance: DockerAIService;
  export default instance;
}

// Iron Session types
declare module 'iron-session/next' {
  import { NextApiHandler, NextApiRequest } from 'next';
  import { GetServerSidePropsContext, GetServerSidePropsResult } from 'next';

  export interface IronSessionOptions {
    cookieName: string;
    password: string;
    cookieOptions?: {
      secure?: boolean;
      httpOnly?: boolean;
      sameSite?: 'strict' | 'lax' | 'none';
      path?: string;
      domain?: string;
      maxAge?: number;
    };
  }

  export function withIronSessionApiRoute<T>(
    handler: NextApiHandler<T>,
    options: IronSessionOptions
  ): NextApiHandler<T>;

  export function withIronSessionSsr<
    P extends { [key: string]: unknown } = { [key: string]: unknown },
  >(
    handler: (
      context: GetServerSidePropsContext,
    ) => GetServerSidePropsResult<P> | Promise<GetServerSidePropsResult<P>>,
    options: IronSessionOptions,
  ): (
    context: GetServerSidePropsContext,
  ) => Promise<GetServerSidePropsResult<P>>;
}

// Extend NextApiRequest with session property
declare module 'next' {
  interface NextApiRequest {
    session: {
      [key: string]: any;
      chartData?: any;
      birthDetails?: any;
      questionnaireData?: any;
      save(): Promise<void>;
      destroy(): Promise<void>;
    };
  }
}
