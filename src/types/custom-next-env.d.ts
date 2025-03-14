/// <reference types="next" />
/// <reference types="next/image-types/global" />
/// <reference path="./three-extensions.d.ts" />
/// <reference path="./module-declarations.d.ts" />

// React 18 JSX namespace augmentation
declare namespace React {
  // Add missing React 18 types if needed
  interface CSSProperties {
    [key: `--${string}`]: string | number;
  }
}

// Ensure the JSX namespace is correctly set up
declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
