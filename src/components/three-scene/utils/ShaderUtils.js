/**
 * Optimized shader utilities for Three.js applications
 * Contains common GLSL functions for noise, lighting, and post-processing effects
 */

// Noise utilities for various shader effects
const noiseUtils = `
  // Fast 2D noise function
  float noise2D(vec2 p) {
    return sin(p.x * 10.0) * sin(p.y * 10.0) * 0.5 + 0.5;
  }

  // 3D noise with different frequency components
  float noise3D(vec3 p) {
    p = fract(p * vec3(123.34, 234.34, 345.65));
    p += dot(p, p + 34.45);
    return fract((p.x + p.y) * p.z);
  }

  // Higher quality 3D noise (Perlin-like)
  vec3 hash3D(vec3 p) {
    p = vec3(
      dot(p, vec3(127.1, 311.7, 74.7)),
      dot(p, vec3(269.5, 183.3, 246.1)),
      dot(p, vec3(113.5, 271.9, 124.6))
    );
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
  }

  float perlinNoise(vec3 p) {
    vec3 pi = floor(p);
    vec3 pf = fract(p);

    // Hermite interpolation
    vec3 u = pf * pf * (3.0 - 2.0 * pf);

    // Gradients
    vec3 ga = hash3D(pi + vec3(0.0, 0.0, 0.0));
    vec3 gb = hash3D(pi + vec3(1.0, 0.0, 0.0));
    vec3 gc = hash3D(pi + vec3(0.0, 1.0, 0.0));
    vec3 gd = hash3D(pi + vec3(1.0, 1.0, 0.0));
    vec3 ge = hash3D(pi + vec3(0.0, 0.0, 1.0));
    vec3 gf = hash3D(pi + vec3(1.0, 0.0, 1.0));
    vec3 gg = hash3D(pi + vec3(0.0, 1.0, 1.0));
    vec3 gh = hash3D(pi + vec3(1.0, 1.0, 1.0));

    // Projections
    float va = dot(ga, pf - vec3(0.0, 0.0, 0.0));
    float vb = dot(gb, pf - vec3(1.0, 0.0, 0.0));
    float vc = dot(gc, pf - vec3(0.0, 1.0, 0.0));
    float vd = dot(gd, pf - vec3(1.0, 1.0, 0.0));
    float ve = dot(ge, pf - vec3(0.0, 0.0, 1.0));
    float vf = dot(gf, pf - vec3(1.0, 0.0, 1.0));
    float vg = dot(gg, pf - vec3(0.0, 1.0, 1.0));
    float vh = dot(gh, pf - vec3(1.0, 1.0, 1.0));

    // Interpolate
    float x1 = mix(va, vb, u.x);
    float x2 = mix(vc, vd, u.x);
    float x3 = mix(ve, vf, u.x);
    float x4 = mix(vg, vh, u.x);
    float y1 = mix(x1, x2, u.y);
    float y2 = mix(x3, x4, u.y);
    float result = mix(y1, y2, u.z);

    return result * 0.5 + 0.5;  // Map to [0, 1]
  }

  // Fractal Brownian Motion
  float fbm(vec3 p, int octaves) {
    float result = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    float total = 0.0;

    // Accumulate noise values with decreasing amplitude
    for (int i = 0; i < 8; ++i) {
      if (i >= octaves) break;
      result += amplitude * perlinNoise(p * frequency);
      total += amplitude;
      amplitude *= 0.5;
      frequency *= 2.0;
      p = p * 1.07 + vec3(0.25);  // Domain distortion
    }

    return result / total;
  }
`;

// Academy Color Encoding System (ACES) tonemapping for HDR-like effects
const acesTonemapping = `
  // ACES tone mapping function for HDR-like visuals
  vec3 aces(vec3 x) {
    float a = 2.51;
    float b = 0.03;
    float c = 2.43;
    float d = 0.59;
    float e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
  }
`;

// Utility for shader optimization
const optimizeShaders = (forceOptimization = false) => {
  console.log("Shader optimization standard mode enabled");
};

// Physical light models (scientifically accurate)
const physicalLightModel = `
  // Fresnel equation (Schlick approximation)
  float fresnelSchlick(float cosTheta, float F0) {
    return F0 + (1.0 - F0) * pow(1.0 - cosTheta, 5.0);
  }

  // GGX/Trowbridge-Reitz normal distribution function
  float distributionGGX(float NdotH, float roughness) {
    float a = roughness * roughness;
    float a2 = a * a;
    float denom = NdotH * NdotH * (a2 - 1.0) + 1.0;
    return a2 / (3.14159265359 * denom * denom);
  }

  // Geometry function (Smith model)
  float geometrySchlickGGX(float NdotV, float roughness) {
    float r = roughness + 1.0;
    float k = (r * r) / 8.0;
    return NdotV / (NdotV * (1.0 - k) + k);
  }

  float geometrySmith(float NdotV, float NdotL, float roughness) {
    return geometrySchlickGGX(NdotV, roughness) * geometrySchlickGGX(NdotL, roughness);
  }
`;

// Atmospheric scattering utilities
const atmosphericScattering = `
  // Rayleigh scattering coefficient
  vec3 rayleighCoefficient(float wavelength) {
    float n = 1.0003;  // Refractive index of air
    float N = 2.545e25; // Molecular density of air
    float pn = 0.035;   // Depolarization factor

    float wavelength4 = pow(wavelength, 4.0);
    return vec3(8.0 * pow(3.14159265359, 3.0) * pow(n*n - 1.0, 2.0) * (6.0 + 3.0 * pn)) /
           (3.0 * N * wavelength4 * (6.0 - 7.0 * pn));
  }

  // Mie scattering phase function
  float miePhaseFn(float cosTheta, float g) {
    float g2 = g * g;
    return (1.0 - g2) / (4.0 * 3.14159265359 * pow(1.0 + g2 - 2.0 * g * cosTheta, 1.5));
  }
`;

// Color conversion utilities
const colorConversion = `
  // RGB to HSL conversion
  vec3 rgb2hsl(vec3 color) {
    float maxColor = max(max(color.r, color.g), color.b);
    float minColor = min(min(color.r, color.g), color.b);
    float delta = maxColor - minColor;

    float h = 0.0;
    float s = 0.0;
    float l = (maxColor + minColor) / 2.0;

    if (delta > 0.0) {
      s = l < 0.5 ? delta / (maxColor + minColor) : delta / (2.0 - maxColor - minColor);

      if (maxColor == color.r) {
        h = (color.g - color.b) / delta + (color.g < color.b ? 6.0 : 0.0);
      } else if (maxColor == color.g) {
        h = (color.b - color.r) / delta + 2.0;
      } else {
        h = (color.r - color.g) / delta + 4.0;
      }

      h /= 6.0;
    }

    return vec3(h, s, l);
  }

  // HSL to RGB conversion
  vec3 hsl2rgb(vec3 hsl) {
    float h = hsl.x;
    float s = hsl.y;
    float l = hsl.z;

    float r, g, b;

    if (s == 0.0) {
      r = g = b = l;
    } else {
      float q = l < 0.5 ? l * (1.0 + s) : l + s - l * s;
      float p = 2.0 * l - q;

      r = hueToRgb(p, q, h + 1.0/3.0);
      g = hueToRgb(p, q, h);
      b = hueToRgb(p, q, h - 1.0/3.0);
    }

    return vec3(r, g, b);
  }

  float hueToRgb(float p, float q, float t) {
    if (t < 0.0) t += 1.0;
    if (t > 1.0) t -= 1.0;
    if (t < 1.0/6.0) return p + (q - p) * 6.0 * t;
    if (t < 1.0/2.0) return q;
    if (t < 2.0/3.0) return p + (q - p) * (2.0/3.0 - t) * 6.0;
    return p;
  }
`;

// Export utilities and named function
const ShaderUtils = {
  noiseUtils,
  acesTonemapping,
  physicalLightModel,
  atmosphericScattering,
  colorConversion
};

export default ShaderUtils;
export { optimizeShaders };
