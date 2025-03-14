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
