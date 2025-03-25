/**
 * Type definitions for environment variables
 */

declare namespace NodeJS {
  interface ProcessEnv {
    // Frontend environment variables
    NEXT_PUBLIC_API_URL?: string;
    NEXT_PUBLIC_API_SERVICE_URL?: string;
    NEXT_PUBLIC_WS_URL?: string;
    NODE_ENV?: 'development' | 'production' | 'test';

    // Backend environment variables (used in SSR)
    API_URL?: string;
    API_SERVICE_URL?: string;
    WS_URL?: string;
  }
}
