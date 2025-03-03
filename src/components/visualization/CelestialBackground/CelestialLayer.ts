import * as THREE from 'three';
import { ProgressiveLoader } from './ProgressiveLoader';
import { CelestialLayerConfig, Vector3D } from './types';

export class CelestialLayer {
  private mesh: THREE.Mesh;
  private material: THREE.ShaderMaterial;
  private initialPosition: Vector3D;
  private parallaxFactor: number;
  private loader: ProgressiveLoader;
  private quality: 'low' | 'medium' | 'high' = 'high';

  constructor({
    depth,
    content,
    parallaxFactor,
    position,
    loader,
    scene,
  }: CelestialLayerConfig) {
    this.initialPosition = position;
    this.parallaxFactor = parallaxFactor;
    this.loader = loader;

    // Create geometry (large plane to cover viewport)
    const geometry = new THREE.PlaneGeometry(2000, 2000);

    // Create shader material
    this.material = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        texture: { value: null },
        opacity: { value: 1.0 },
        parallaxOffset: { value: new THREE.Vector2(0, 0) },
      },
      vertexShader: `
        varying vec2 vUv;
        uniform vec2 parallaxOffset;
        
        void main() {
          vUv = uv + parallaxOffset;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D texture;
        uniform float opacity;
        uniform float time;
        varying vec2 vUv;
        
        void main() {
          vec4 color = texture2D(texture, vUv);
          
          // Add subtle animation based on time
          float brightness = 1.0 + 0.1 * sin(time * 0.001 + vUv.x * 10.0);
          
          gl_FragColor = vec4(color.rgb * brightness, color.a * opacity);
        }
      `,
      transparent: true,
      depthWrite: false,
    });

    // Create mesh and add to scene
    this.mesh = new THREE.Mesh(geometry, this.material);
    this.mesh.position.set(position.x, position.y, position.z);
    scene.add(this.mesh);

    // Load texture progressively
    this.loadTexture(content);
  }

  private async loadTexture(content: string) {
    const texturePath = `/textures/${content}.jpg`;
    const quality = this.getQualitySettings();

    try {
      const texture = await this.loader.loadCelestialTexture(
        texturePath,
        quality
      );
      
      if (this.material) {
        this.material.uniforms.texture.value = texture;
      }
    } catch (error) {
      console.error(`Failed to load texture: ${texturePath}`, error);
    }
  }

  public updatePosition(scrollPosition: number): void {
    if (!this.mesh) return;

    const parallaxX = scrollPosition * this.parallaxFactor * 0.1;
    const parallaxY = scrollPosition * this.parallaxFactor * 0.05;

    this.mesh.position.x = this.initialPosition.x + parallaxX;
    this.mesh.position.y = this.initialPosition.y + parallaxY;

    if (this.material && this.material.uniforms) {
      if (this.material.uniforms.parallaxOffset) {
        this.material.uniforms.parallaxOffset.value.set(
          parallaxX * 0.001,
          parallaxY * 0.001
        );
      }
      if (this.material.uniforms.time) {
        this.material.uniforms.time.value = performance.now();
      }
    }
  }

  public setQuality(quality: 'low' | 'medium' | 'high'): void {
    if (this.quality === quality) return;
    
    this.quality = quality;
    this.loadTexture(this.mesh.name);
  }

  private getQualitySettings() {
    const settings = {
      low: {
        size: 1024,
        mipmap: false,
        anisotropy: 1,
      },
      medium: {
        size: 2048,
        mipmap: true,
        anisotropy: 8,
      },
      high: {
        size: 4096,
        mipmap: true,
        anisotropy: 16,
      },
    };

    return settings[this.quality];
  }

  public dispose(): void {
    if (this.mesh) {
      this.mesh.geometry.dispose();
      (this.mesh.material as THREE.Material).dispose();
      this.mesh.removeFromParent();
    }
  }
}
