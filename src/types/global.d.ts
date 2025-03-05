// Type declarations for missing types
/// <reference types="node" />
/// <reference types="react" />
/// <reference types="react-dom" />
/// <reference types="next" />

declare namespace NodeJS {
  interface ProcessEnv {
    NODE_ENV: 'development' | 'production' | 'test';
    NEXT_PUBLIC_API_URL?: string;
  }
}

// Extend JSX namespace if needed
declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
