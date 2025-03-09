import ShaderUtils from '../utils/ShaderUtils';

// Vertex shader for nebula with improved depth and parallax effects
const vertexShader = `
  varying vec2 vUv;
  varying vec3 vPosition;
  varying vec3 vNormal;
  varying vec3 vViewPosition;
  varying vec3 vWorldPosition;
  varying float vDepthFactor;

  void main() {
    vUv = uv;
    vPosition = position;
    vNormal = normalize(normalMatrix * normal);

    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPosition.xyz;

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vViewPosition = -mvPosition.xyz;

    // Calculate depth factor for effects that vary with depth
    vDepthFactor = (position.z + 1.0) * 0.5;
    vDepthFactor = pow(vDepthFactor, 1.8); // Non-linear depth for more dramatic effect

    gl_Position = projectionMatrix * mvPosition;
  }
`;

// Fragment shader for advanced volumetric and parallax effects
const fragmentShader = `
  uniform float time;
  uniform sampler2D nebulaTextures[4]; // Fixed maximum size for compatibility
  uniform int textureCount;
  uniform vec3 baseColor;
  uniform vec3 accentColor;
  uniform vec3 glowColor;
  uniform vec3 dustColor;
  uniform vec3 cloudColor;
  uniform vec2 resolution;
  uniform float intensity;
  uniform vec3 viewerPosition; // Renamed from cameraPosition to avoid conflict
  uniform vec2 mousePosition;
  uniform vec2 mouseVelocity;
  uniform float parallaxStrength;
  uniform float viewportAspect;

  varying vec2 vUv;
  varying vec3 vPosition;
  varying vec3 vNormal;
  varying vec3 vViewPosition;
  varying vec3 vWorldPosition;
  varying float vDepthFactor;

  const float PI = 3.14159265359;

  ${ShaderUtils.noiseUtils}

  // Fixed parallax function to use updated parameters
  vec2 applyParallax(vec2 uv, float depth) {
    float parallaxFactor = (1.0 - depth) * parallaxStrength;
    vec2 parallaxOffset = mousePosition * parallaxFactor;
    return uv + parallaxOffset;
  }

  // Optimized volumetric ray marching with adaptive sampling
  vec4 volumeRayMarch(vec3 rayOrigin, vec3 rayDir, vec2 movingUv, float time) {
    vec4 accumulatedColor = vec4(0.0);
    float accumulatedAlpha = 0.0;

    // Adaptive detail based on texture count (quality level proxy)
    int octaves = textureCount <= 1 ? 2 : (textureCount < 3 ? 3 : 4);
    int maxSteps = textureCount <= 1 ? 8 : (textureCount < 3 ? 12 : 16);

    // Adaptive step size based on quality
    float stepSize = textureCount <= 1 ? 0.2 : (textureCount < 3 ? 0.15 : 0.12);
    float densityMultiplier = 1.2 * intensity;

    // Optimization: Start deeper in the volume for better initial samples
    float t = 0.3;

    // Early ray termination when opacity threshold reached
    float opacityThreshold = 0.95;

    // Primary ray marching loop with early termination
    for (int i = 0; i < 24; i++) {
      if (i >= maxSteps || accumulatedAlpha >= opacityThreshold) break;

      // Calculate sample position with better scaling
      vec3 samplePos = rayOrigin + rayDir * t;
      samplePos *= 0.75; // Tighter scaling for more detailed nebula

      // Optimization: Skip samples outside nebula bounds
      float distFromCenter = length(samplePos);
      if (distFromCenter > 1.5) {
        t += stepSize;
        continue;
      }

      // Process each texture layer
      for (int texIndex = 0; texIndex < 4; texIndex++) {
        if (texIndex >= textureCount) break;

        // Improved animation parameters for more natural movement
        float rotation = time * 0.008 * float(texIndex + 1);
        float scale = 1.0 + float(texIndex) * 0.25;
        float offsetX = sin(time * 0.04 * float(texIndex + 1)) * 0.1;
        float offsetY = cos(time * 0.03 * float(texIndex + 1)) * 0.1;

        // Enhanced parallax based on depth
        float depthFactor = t / 2.0;
        vec2 parallaxUv = applyParallax(movingUv, depthFactor);

        // More efficient UV rotation calculation
        float cosRot = cos(rotation);
        float sinRot = sin(rotation);
        vec2 centeredUv = parallaxUv - 0.5;
        vec2 rotatedUv = vec2(
          cosRot * centeredUv.x + sinRot * centeredUv.y + 0.5 + offsetX,
          cosRot * centeredUv.y - sinRot * centeredUv.x + 0.5 + offsetY
        );

        vec2 scaledUv = (rotatedUv - 0.5) / scale + 0.5;

        // Optimized texture sampling with conditional branching
        vec4 texColor;
        if (texIndex == 0) texColor = texture2D(nebulaTextures[0], scaledUv);
        else if (texIndex == 1 && textureCount > 1) texColor = texture2D(nebulaTextures[1], scaledUv);
        else if (texIndex == 2 && textureCount > 2) texColor = texture2D(nebulaTextures[2], scaledUv);
        else if (texIndex == 3 && textureCount > 3) texColor = texture2D(nebulaTextures[3], scaledUv);
        else continue;

        // Improved noise position for more interesting patterns
        vec3 noisePos = samplePos + vec3(
          time * 0.02 * float(texIndex + 1),
          time * 0.015 * float(texIndex + 1),
          time * 0.01 * float(texIndex + 1)
        );

        // Optimized FBM calculation with fewer octaves
        float baseDensity = fbm(noisePos * (0.6 + float(texIndex) * 0.15), octaves);
        float density = baseDensity * texColor.r * densityMultiplier;

        // Simple but effective animation
        density *= 1.0 + 0.3 * sin(noisePos.x * 4.0 + time * 0.08) *
                  cos(noisePos.z * 3.0 + time * 0.06);

        // Skip low-density areas for performance
        if (density < 0.04) continue;

        // Enhanced gas coloring with better blending
        vec3 gasColor;
        if (texIndex == 0) {
          // Warm dust regions
          gasColor = mix(dustColor, vec3(1.0, 0.8, 0.8), baseDensity * baseDensity);
        } else if (texIndex == 1) {
          // Cool cloud regions
          gasColor = mix(cloudColor, vec3(0.7, 0.9, 1.0), baseDensity);
        } else {
          // Accent and glow regions with improved noise variation
          float colorMix = noise3D(noisePos * 2.5 + vec3(float(texIndex) * 10.0));
          gasColor = mix(accentColor, glowColor, colorMix * colorMix);
        }

        // Improved physical light model
        float edgeBrightness = 1.0 - exp(-density * stepSize * 2.5);
        float volumeTransmittance = exp(-density * stepSize);

        // Quadratic distance attenuation for better depth perception
        float distanceAttenuation = 1.0 / (1.0 + t * t * 0.15);

        // Improved opacity calculation
        vec4 sampleColor = vec4(gasColor * edgeBrightness * distanceAttenuation, 1.0 - volumeTransmittance);

        // Standard volume rendering equation
        accumulatedColor += sampleColor * (1.0 - accumulatedAlpha);
        accumulatedAlpha += sampleColor.a * (1.0 - accumulatedAlpha);

        // Early termination check
        if (accumulatedAlpha >= opacityThreshold) break;
      }

      // Adaptive step size that increases with distance for performance
      t += stepSize * (1.0 + t * 0.1);
    }

    return accumulatedColor;
  }

  // Process a single texture
  vec4 processTexture(int index, vec2 movingUv, float depth, float time) {
    float rotation = time * 0.01 * float(index + 1);
    float scale = 1.0 + float(index) * 0.2;
    float offsetX = sin(time * 0.05 * float(index + 1)) * 0.1;
    float offsetY = cos(time * 0.04 * float(index + 1)) * 0.1;

    vec2 parallaxUv = applyParallax(movingUv, depth);

    vec2 rotatedUv = vec2(
      cos(rotation) * (parallaxUv.x - 0.5) + sin(rotation) * (parallaxUv.y - 0.5) + 0.5 + offsetX,
      cos(rotation) * (parallaxUv.y - 0.5) - sin(rotation) * (parallaxUv.x - 0.5) + 0.5 + offsetY
    );

    vec2 scaledUv = (rotatedUv - 0.5) / scale + 0.5;

    vec4 texColor;
    if (index == 0) texColor = texture2D(nebulaTextures[0], scaledUv);
    else if (index == 1) texColor = texture2D(nebulaTextures[1], scaledUv);
    else if (index == 2) texColor = texture2D(nebulaTextures[2], scaledUv);
    else texColor = texture2D(nebulaTextures[3], scaledUv);

    float w = 1.0 / float(textureCount);
    if (index == 0) w *= 1.5;

    float parallax = sin(depth * 3.14159 + time * 0.2 + float(index)) * 0.5 + 0.5;
    w *= parallax;

    return vec4(texColor.rgb * w, w);
  }

  ${ShaderUtils.acesTonemapping}

  void main() {
    vec2 movingUv = vUv + vec2(
      sin(time * 0.1) * 0.02,
      cos(time * 0.08) * 0.02
    );

    float depth = (vPosition.z + 1.0) * 0.5;
    depth = pow(depth, 2.0);

    vec4 backgroundNebula = vec4(0.0);
    float weight = 0.0;

    // Process background textures
    if (textureCount > 0) {
      vec4 result0 = processTexture(0, movingUv, depth, time);
      backgroundNebula += vec4(result0.rgb, 0.0);
      weight += result0.a;
    }

    if (textureCount > 1) {
      vec4 result1 = processTexture(1, movingUv, depth, time);
      backgroundNebula += vec4(result1.rgb, 0.0);
      weight += result1.a;
    }

    if (textureCount > 2) {
      vec4 result2 = processTexture(2, movingUv, depth, time);
      backgroundNebula += vec4(result2.rgb, 0.0);
      weight += result2.a;
    }

    if (textureCount > 3) {
      vec4 result3 = processTexture(3, movingUv, depth, time);
      backgroundNebula += vec4(result3.rgb, 0.0);
      weight += result3.a;
    }

    if (weight > 0.0) backgroundNebula /= weight;

    vec3 rayOrigin = vPosition * 0.8;
    vec3 rayDir = normalize(vNormal);

    vec4 volumetricNebula = volumeRayMarch(rayOrigin, rayDir, movingUv, time);

    vec4 finalColor = mix(backgroundNebula, volumetricNebula, 0.7);

    vec3 viewDir = normalize(vViewPosition);
    float fresnel = pow(1.0 - abs(dot(vNormal, viewDir)), 3.0);
    vec3 edgeGlow = glowColor * fresnel * 0.6;

    vec3 emission = dustColor * pow(finalColor.rgb, vec3(2.0)) * 0.5;

    finalColor.rgb += emission + edgeGlow;

    finalColor.rgb = aces(finalColor.rgb * 1.2);

    float opacity = finalColor.a * 0.8;
    opacity *= (1.0 - fresnel * 0.2);

    float pulsation = sin(time * 0.2) * 0.5 + 0.5;
    pulsation = pulsation * 0.1 + 0.9;
    opacity *= pulsation;

    gl_FragColor = vec4(finalColor.rgb, opacity);
  }
`;

// Create a named shader object to fix ESLint warnings
const NebulaShaders = {
  vertexShader,
  fragmentShader
};

export default NebulaShaders;
