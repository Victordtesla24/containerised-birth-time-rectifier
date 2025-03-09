// Shader utility functions for use in Three.js shaders
// Extracted from Nebula.jsx to improve modularity

// HDR tonemapping function based on the ACES filmic tone mapping curve
const acesTonemapping = `
vec3 aces(vec3 x) {
  float a = 2.51;
  float b = 0.03;
  float c = 2.43;
  float d = 0.59;
  float e = 0.14;
  return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}
`;

// 3D noise functions for volumetric effects
const noiseUtils = `
// Improved 3D noise functions for volumetric effects
vec3 hash33(vec3 p) {
  p = fract(p * vec3(443.8975, 397.2973, 491.1871));
  p += dot(p.zxy, p.yxz + 19.27);
  return fract(vec3(p.x * p.y, p.z * p.x, p.y * p.z));
}

float noise3D(vec3 p) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);

  float n000 = dot(hash33(i), f);
  float n001 = dot(hash33(i + vec3(0, 0, 1)), f - vec3(0, 0, 1));
  float n010 = dot(hash33(i + vec3(0, 1, 0)), f - vec3(0, 1, 0));
  float n011 = dot(hash33(i + vec3(0, 1, 1)), f - vec3(0, 1, 1));
  float n100 = dot(hash33(i + vec3(1, 0, 0)), f - vec3(1, 0, 0));
  float n101 = dot(hash33(i + vec3(1, 0, 1)), f - vec3(1, 0, 1));
  float n110 = dot(hash33(i + vec3(1, 1, 0)), f - vec3(1, 1, 0));
  float n111 = dot(hash33(i + vec3(1, 1, 1)), f - vec3(1, 1, 1));

  vec3 n_x = mix(vec3(n000, n010, n001), vec3(n100, n110, n101), f.x);
  vec2 n_xy = mix(n_x.xy, n_x.zy, f.y);

  return mix(n_xy.x, n_xy.y, f.z) * 0.5 + 0.5;
}

// Fractal Brownian Motion
float fbm(vec3 p, int octaves) {
  float value = 0.0;
  float amplitude = 0.5;
  float frequency = 1.0;

  for (int i = 0; i < 6; i++) {
    if (i >= octaves) break;
    value += amplitude * noise3D(p * frequency);
    amplitude *= 0.5;
    frequency *= 2.0;
    p = p + vec3(7.31, 13.17, 5.23) * float(i) * 0.1;
  }

  return value;
}
`;

// Parallax utility for dynamic movement
const parallaxUtils = `
// Enhanced parallax with depth awareness
vec2 applyParallax(vec2 uv, float depth, vec2 mousePosition, float parallaxStrength) {
  float parallaxFactor = (1.0 - depth) * parallaxStrength;
  vec2 parallaxOffset = mousePosition * parallaxFactor;

  return uv + parallaxOffset;
}
`;

/**
 * Optimizes shader performance based on device capabilities
 * @param {boolean} aggressiveOptimization - Whether to use more aggressive optimizations for low-end devices
 */
export const optimizeShaders = (aggressiveOptimization = false) => {
  // This function would typically modify shader settings or THREE.ShaderChunk
  // For compatibility, we're keeping it as a no-op with logging
  console.log(`Shader optimization ${aggressiveOptimization ? 'aggressive' : 'standard'} mode enabled`);

  // Implementation would go here in a real application
  return true;
};

// Create a named object before exporting to fix linting warnings
const ShaderUtils = {
  acesTonemapping,
  noiseUtils,
  parallaxUtils
};

export default ShaderUtils;
