#!/bin/bash

# Fix TypeScript issues in the project
echo "🔨 Fixing TypeScript issues..."

# Create types directory if it doesn't exist
mkdir -p src/types

# Create three-extensions.d.ts file
cat > src/types/three-extensions.d.ts << 'EOF'
// Type declarations for Three.js extensions

declare module 'three/examples/jsm/postprocessing/EffectComposer' {
  import { WebGLRenderer, WebGLRenderTarget, Texture, Scene, Camera } from 'three';

  export class EffectComposer {
    constructor(renderer: WebGLRenderer, renderTarget?: WebGLRenderTarget);
    renderTarget1: WebGLRenderTarget;
    renderTarget2: WebGLRenderTarget;
    writeBuffer: WebGLRenderTarget;
    readBuffer: WebGLRenderTarget;
    passes: Pass[];
    copyPass: ShaderPass;

    swapBuffers(): void;
    addPass(pass: Pass): void;
    insertPass(pass: Pass, index: number): void;
    removePass(pass: Pass): void;
    isLastEnabledPass(passIndex: number): boolean;
    render(deltaTime?: number): void;
    reset(renderTarget?: WebGLRenderTarget): void;
    setSize(width: number, height: number): void;
    setPixelRatio(pixelRatio: number): void;
  }

  export class Pass {
    enabled: boolean;
    needsSwap: boolean;
    clear: boolean;
    renderToScreen: boolean;

    setSize(width: number, height: number): void;
    render(renderer: WebGLRenderer, writeBuffer: WebGLRenderTarget, readBuffer: WebGLRenderTarget, deltaTime: number, maskActive: boolean): void;
  }
}

declare module 'three/examples/jsm/postprocessing/RenderPass' {
  import { Scene, Camera, Material } from 'three';
  import { Pass } from 'three/examples/jsm/postprocessing/EffectComposer';

  export class RenderPass extends Pass {
    constructor(scene: Scene, camera: Camera, overrideMaterial?: Material, clearColor?: number, clearAlpha?: number);
    scene: Scene;
    camera: Camera;
    overrideMaterial: Material | null;
    clearColor: number | null;
    clearAlpha: number | null;
    clearDepth: boolean;
  }
}

declare module 'three/examples/jsm/postprocessing/ShaderPass' {
  import { ShaderMaterial, WebGLRenderer, WebGLRenderTarget } from 'three';
  import { Pass } from 'three/examples/jsm/postprocessing/EffectComposer';

  export class ShaderPass extends Pass {
    constructor(shader: object, textureID?: string);
    textureID: string;
    uniforms: { [key: string]: { value: any } };
    material: ShaderMaterial;
    fsQuad: object;
  }
}

declare module 'three/examples/jsm/postprocessing/UnrealBloomPass' {
  import { Vector2, WebGLRenderTarget, Color } from 'three';
  import { Pass } from 'three/examples/jsm/postprocessing/EffectComposer';

  export class UnrealBloomPass extends Pass {
    constructor(resolution: Vector2, strength: number, radius: number, threshold: number);
    resolution: Vector2;
    strength: number;
    radius: number;
    threshold: number;
    clearColor: Color;
    renderTargetsHorizontal: WebGLRenderTarget[];
    renderTargetsVertical: WebGLRenderTarget[];
    nMips: number;
    renderTargetBright: WebGLRenderTarget;

    dispose(): void;
  }
}

declare module 'three/examples/jsm/postprocessing/SMAAPass' {
  import { Vector2, WebGLRenderTarget } from 'three';
  import { Pass } from 'three/examples/jsm/postprocessing/EffectComposer';

  export class SMAAPass extends Pass {
    constructor(width: number, height: number);
    edgesRT: WebGLRenderTarget;
    weightsRT: WebGLRenderTarget;

    dispose(): void;
  }
}
EOF

# Create module-declarations.d.ts file
cat > src/types/module-declarations.d.ts << 'EOF'
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
  }

  export const CelestialBody: React.FC<CelestialBodyProps>;
}

declare module '@/utils/planetImages' {
  export function getPlanetImagePath(planetName: string): string;
  export function getPlanetFallbackColor(planetName: string): string;
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
EOF

# Create a React import fix script to convert all default imports to namespace imports
cat > src/types/custom-react-types.d.ts << 'EOF'
// React override types
/// <reference types="react" />

// Use namespace import * as React from 'react' instead of default import
declare module 'react' {
  export = React;
  export as namespace React;
}
EOF

# Update the index.d.ts file to include references
echo "/// <reference path=\"./three-extensions.d.ts\" />
/// <reference path=\"./module-declarations.d.ts\" />
/// <reference path=\"./custom-react-types.d.ts\" />

$(cat src/types/index.d.ts)" > src/types/index.d.ts.new
mv src/types/index.d.ts.new src/types/index.d.ts

echo "✅ TypeScript declarations have been updated."
echo "🔄 To fix React imports in your components, use: import * as React from 'react';"
echo "🛠️ Run the TypeScript checker again with: npx tsc --noEmit"
