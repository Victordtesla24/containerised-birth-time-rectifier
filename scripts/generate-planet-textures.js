// Generate procedural textures for planets
const fs = require('fs');
const { createCanvas } = require('canvas');

// Create directories if they don't exist
const planetsDir = 'public/images/planets';
if (!fs.existsSync(planetsDir)) {
  fs.mkdirSync(planetsDir, { recursive: true });
}

// List of planets to generate textures for
const planets = [
  'mercury',
  'venus',
  'earth',
  'mars',
  'jupiter',
  'saturn'
];

// Ensure each planet has its own directory
planets.forEach(planet => {
  const planetDir = `${planetsDir}/${planet}`;
  if (!fs.existsSync(planetDir)) {
    fs.mkdirSync(planetDir, { recursive: true });
  }
});

// Helper function for noise with proper bounds checking
function createNoise2D(size, scale, intensity, seed = 42) {
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Fill with black
  ctx.fillStyle = 'black';
  ctx.fillRect(0, 0, size, size);

  // Generate noise
  const imgData = ctx.getImageData(0, 0, size, size);
  const data = imgData.data;

  // Seeded random function
  let random = seed;
  const nextRandom = () => {
    random = (random * 9301 + 49297) % 233280;
    return random / 233280;
  };

  // Grid noise (ensure at least 2x2 grid)
  const gridSize = Math.max(2, Math.floor(size / scale));
  const grid = [];

  // Create 2D grid with proper initialization
  for (let y = 0; y < gridSize; y++) {
    grid[y] = [];
    for (let x = 0; x < gridSize; x++) {
      grid[y][x] = nextRandom() * 2 - 1;
    }
  }

  // Helper for smoothstep interpolation
  const smoothstep = (t) => t * t * (3 - 2 * t);

  // Generate noise using value noise with interpolation
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const gridX = x / scale;
      const gridY = y / scale;

      // Ensure indices are within bounds
      const x0 = Math.min(Math.floor(gridX), gridSize - 1);
      const y0 = Math.min(Math.floor(gridY), gridSize - 1);
      const x1 = (x0 + 1) % gridSize;
      const y1 = (y0 + 1) % gridSize;

      const sx = smoothstep(gridX - x0);
      const sy = smoothstep(gridY - y0);

      // Bilinear interpolation with safe access
      const n0 = grid[y0][x0];
      const n1 = grid[y0][x1];
      const n2 = grid[y1][x0];
      const n3 = grid[y1][x1];

      const nx0 = n0 + sx * (n1 - n0);
      const nx1 = n2 + sx * (n3 - n2);
      const value = nx0 + sy * (nx1 - nx0);

      // Scale value to 0-255 range with intensity
      const pixelValue = Math.floor(((value + 1) / 2) * 255 * intensity);

      // Set RGBA values (all channels the same for grayscale)
      const i = (y * size + x) * 4;
      data[i] = pixelValue;     // R
      data[i + 1] = pixelValue; // G
      data[i + 2] = pixelValue; // B
      data[i + 3] = 255;        // A (fully opaque)
    }
  }

  ctx.putImageData(imgData, 0, 0);
  return canvas;
}

// Generate a planet texture with features specific to that planet
function generatePlanetTexture(planet, size) {
  console.log(`Generating ${planet} texture...`);
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Base colors for different planets
  const planetColors = {
    mercury: '#A5A5A5',
    venus: '#E6C073',
    earth: '#1E88E5',
    mars: '#D03C1F',
    jupiter: '#E0B880',
    saturn: '#EAC87A'
  };

  // Fill with base color
  ctx.fillStyle = planetColors[planet] || '#AAAAAA';
  ctx.fillRect(0, 0, size, size);

  // Create multi-layer noise with different parameters for each planet
  let noiseCanvases = [];

  switch (planet) {
    case 'mercury':
      // Mercury has many craters
      noiseCanvases = [
        { canvas: createNoise2D(size, 4, 0.5, 12345), mode: 'multiply', opacity: 0.7 },
        { canvas: createNoise2D(size, 10, 0.3, 67890), mode: 'overlay', opacity: 0.6 },
        { canvas: createNoise2D(size, 20, 0.2, 13579), mode: 'darken', opacity: 0.4 }
      ];
      break;

    case 'venus':
      // Venus has cloudy patterns
      noiseCanvases = [
        { canvas: createNoise2D(size, 5, 0.4, 23456), mode: 'overlay', opacity: 0.6 },
        { canvas: createNoise2D(size, 15, 0.2, 78901), mode: 'lighten', opacity: 0.3 },
        { canvas: createNoise2D(size, 30, 0.1, 24680), mode: 'overlay', opacity: 0.2 }
      ];
      break;

    case 'earth':
      // Earth has continents and oceans
      ctx.fillStyle = '#1E88E5'; // Ocean color
      ctx.fillRect(0, 0, size, size);

      // Add landmasses
      const landCanvas = createNoise2D(size, 8, 0.7, 34567);
      const landCtx = landCanvas.getContext('2d');
      const landData = landCtx.getImageData(0, 0, size, size);

      // Create a thresholded mask for land/ocean
      for (let i = 0; i < landData.data.length; i += 4) {
        // Threshold the noise to create continents
        if (landData.data[i] > 180) {
          landData.data[i] = 76;     // R
          landData.data[i + 1] = 175; // G
          landData.data[i + 2] = 80;  // B
        } else {
          landData.data[i] = 0;     // Make oceans transparent
          landData.data[i + 1] = 0;
          landData.data[i + 2] = 0;
          landData.data[i + 3] = 0;
        }
      }
      landCtx.putImageData(landData, 0, 0);

      // More detailed land features
      noiseCanvases = [
        { canvas: landCanvas, mode: 'source-over', opacity: 1.0 },
        { canvas: createNoise2D(size, 20, 0.15, 45678), mode: 'overlay', opacity: 0.4 },
        { canvas: createNoise2D(size, 40, 0.1, 56789), mode: 'overlay', opacity: 0.2 }
      ];

      // Add cloud layer
      const cloudCanvas = createNoise2D(size, 12, 0.5, 98765);
      const cloudCtx = cloudCanvas.getContext('2d');
      const cloudData = cloudCtx.getImageData(0, 0, size, size);

      // Create fluffy clouds
      for (let i = 0; i < cloudData.data.length; i += 4) {
        if (cloudData.data[i] > 200) {
          cloudData.data[i] = 255;     // R
          cloudData.data[i + 1] = 255; // G
          cloudData.data[i + 2] = 255; // B
          cloudData.data[i + 3] = 200; // Semi-transparent
        } else {
          cloudData.data[i + 3] = 0; // Transparent
        }
      }
      cloudCtx.putImageData(cloudData, 0, 0);
      noiseCanvases.push({ canvas: cloudCanvas, mode: 'screen', opacity: 0.7 });
      break;

    case 'mars':
      // Mars has reddish surface with features
      noiseCanvases = [
        { canvas: createNoise2D(size, 6, 0.6, 67890), mode: 'multiply', opacity: 0.5 },
        { canvas: createNoise2D(size, 15, 0.4, 12345), mode: 'overlay', opacity: 0.6 },
        { canvas: createNoise2D(size, 30, 0.2, 54321), mode: 'color-burn', opacity: 0.3 }
      ];

      // Add polar ice caps
      const polarCanvas = createCanvas(size, size);
      const polarCtx = polarCanvas.getContext('2d');

      // Create circular polar caps
      const northPolarGradient = polarCtx.createRadialGradient(
        size/2, size/8, 0,
        size/2, size/8, size/3
      );
      northPolarGradient.addColorStop(0, 'rgba(255, 255, 255, 0.9)');
      northPolarGradient.addColorStop(0.6, 'rgba(255, 255, 255, 0.3)');
      northPolarGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

      const southPolarGradient = polarCtx.createRadialGradient(
        size/2, size - size/8, 0,
        size/2, size - size/8, size/3
      );
      southPolarGradient.addColorStop(0, 'rgba(255, 255, 255, 0.9)');
      southPolarGradient.addColorStop(0.6, 'rgba(255, 255, 255, 0.3)');
      southPolarGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

      polarCtx.fillStyle = northPolarGradient;
      polarCtx.fillRect(0, 0, size, size);
      polarCtx.fillStyle = southPolarGradient;
      polarCtx.fillRect(0, 0, size, size);

      noiseCanvases.push({ canvas: polarCanvas, mode: 'screen', opacity: 0.8 });
      break;

    case 'jupiter':
      // Jupiter has bands and the Great Red Spot
      // Create banded structure
      const bandsCanvas = createCanvas(size, size);
      const bandsCtx = bandsCanvas.getContext('2d');

      // Create horizontal bands
      const numBands = 12;
      const bandHeight = size / numBands;

      for (let i = 0; i < numBands; i++) {
        // Alternate band colors
        if (i % 2 === 0) {
          bandsCtx.fillStyle = '#E0B880';
        } else {
          bandsCtx.fillStyle = '#C09860';
        }
        bandsCtx.fillRect(0, i * bandHeight, size, bandHeight);
      }

      // Create more band detail with noise
      noiseCanvases = [
        { canvas: bandsCanvas, mode: 'source-over', opacity: 1.0 },
        { canvas: createNoise2D(size, 4, 0.2, 13579), mode: 'overlay', opacity: 0.5 },
        { canvas: createNoise2D(size, 8, 0.3, 97531), mode: 'overlay', opacity: 0.4 },
        { canvas: createNoise2D(size, 16, 0.1, 24680), mode: 'overlay', opacity: 0.3 }
      ];

      // Add Great Red Spot
      const spotCanvas = createCanvas(size, size);
      const spotCtx = spotCanvas.getContext('2d');

      const spotX = size * 0.7;
      const spotY = size * 0.4;
      const spotRadius = size * 0.1;

      const spotGradient = spotCtx.createRadialGradient(
        spotX, spotY, 0,
        spotX, spotY, spotRadius
      );
      spotGradient.addColorStop(0, 'rgba(220, 100, 70, 0.9)');
      spotGradient.addColorStop(0.7, 'rgba(220, 100, 70, 0.6)');
      spotGradient.addColorStop(1, 'rgba(220, 100, 70, 0)');

      spotCtx.fillStyle = spotGradient;
      spotCtx.beginPath();
      spotCtx.ellipse(spotX, spotY, spotRadius * 1.8, spotRadius, 0, 0, Math.PI * 2);
      spotCtx.fill();

      noiseCanvases.push({ canvas: spotCanvas, mode: 'screen', opacity: 0.8 });
      break;

    case 'saturn':
      // Saturn has subtle bands similar to Jupiter but more muted
      noiseCanvases = [
        { canvas: createNoise2D(size, 5, 0.3, 24680), mode: 'multiply', opacity: 0.5 },
        { canvas: createNoise2D(size, 10, 0.2, 13579), mode: 'overlay', opacity: 0.5 },
        { canvas: createNoise2D(size, 20, 0.1, 97531), mode: 'overlay', opacity: 0.3 }
      ];

      // Create subtle banded structure
      const saturnBandsCanvas = createCanvas(size, size);
      const saturnBandsCtx = saturnBandsCanvas.getContext('2d');

      // Create horizontal bands
      const saturnNumBands = 10;
      const saturnBandHeight = size / saturnNumBands;

      for (let i = 0; i < saturnNumBands; i++) {
        // Alternate band colors with subtle contrast
        const intensity = 1 - (i % 2) * 0.08; // 0.92 or 1.0
        saturnBandsCtx.fillStyle = `rgba(234, 200, 122, ${intensity})`;
        saturnBandsCtx.fillRect(0, i * saturnBandHeight, size, saturnBandHeight);
      }

      noiseCanvases.unshift({ canvas: saturnBandsCanvas, mode: 'source-over', opacity: 1.0 });
      break;

    default:
      // Generic planet
      noiseCanvases = [
        { canvas: createNoise2D(size, 4, 0.5, 12345), mode: 'multiply', opacity: 0.7 },
        { canvas: createNoise2D(size, 10, 0.3, 67890), mode: 'overlay', opacity: 0.6 },
        { canvas: createNoise2D(size, 20, 0.2, 13579), mode: 'darken', opacity: 0.4 }
      ];
  }

  // Apply all noise canvases with proper blending
  for (const { canvas, mode, opacity } of noiseCanvases) {
    ctx.globalAlpha = opacity;
    ctx.globalCompositeOperation = mode;
    ctx.drawImage(canvas, 0, 0);
  }

  // Reset compositing
  ctx.globalAlpha = 1.0;
  ctx.globalCompositeOperation = 'source-over';

  return canvas;
}

// Normal map generation
function generateNormalMap(heightMap, size, strength = 2.0) {
  console.log('Generating normal map...');
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Base normal map color (pointing outward)
  ctx.fillStyle = '#8080FF';  // Default normal pointing out (r=0.5, g=0.5, b=1.0)
  ctx.fillRect(0, 0, size, size);

  // Get height data
  const heightCtx = heightMap.getContext('2d');
  const heightData = heightCtx.getImageData(0, 0, size, size);
  const normalData = ctx.getImageData(0, 0, size, size);

  // Convert height map to normal map
  for (let y = 1; y < size - 1; y++) {
    for (let x = 1; x < size - 1; x++) {
      // Sample neighboring heights
      const idx = (y * size + x) * 4;
      const idxLeft = (y * size + (x - 1)) * 4;
      const idxRight = (y * size + (x + 1)) * 4;
      const idxUp = ((y - 1) * size + x) * 4;
      const idxDown = ((y + 1) * size + x) * 4;

      // Calculate slopes (Sobel operator)
      const dX = (heightData.data[idxRight] - heightData.data[idxLeft]) / 255.0;
      const dY = (heightData.data[idxDown] - heightData.data[idxUp]) / 255.0;

      // Normal calculation
      const normalX = -dX * strength;
      const normalY = -dY * strength;
      const normalZ = 1.0;

      // Normalize the normal vector
      const length = Math.sqrt(normalX * normalX + normalY * normalY + normalZ * normalZ);

      // Convert to 0-1 range and then to 0-255
      normalData.data[idx] = Math.floor(((normalX / length) + 1.0) / 2.0 * 255);
      normalData.data[idx + 1] = Math.floor(((normalY / length) + 1.0) / 2.0 * 255);
      normalData.data[idx + 2] = Math.floor(((normalZ / length) + 1.0) / 2.0 * 255);
      normalData.data[idx + 3] = 255;
    }
  }

  ctx.putImageData(normalData, 0, 0);
  return canvas;
}

// Generate bump map
function generateBumpMap(planet, size) {
  console.log(`Generating ${planet} bump map...`);
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Fill with black
  ctx.fillStyle = 'black';
  ctx.fillRect(0, 0, size, size);

  // Apply different noise patterns based on planet
  let noiseScales;

  switch (planet) {
    case 'mercury':
      // Mercury has many craters and a rough surface
      noiseScales = [
        { scale: 4, intensity: 0.8, seed: 11111 },
        { scale: 8, intensity: 0.5, seed: 22222 },
        { scale: 16, intensity: 0.3, seed: 33333 }
      ];
      break;

    case 'earth':
      // Earth has mountains and varied terrain
      noiseScales = [
        { scale: 5, intensity: 0.6, seed: 44444 },
        { scale: 10, intensity: 0.4, seed: 55555 },
        { scale: 20, intensity: 0.2, seed: 66666 }
      ];
      break;

    default:
      // Generic bump map
      noiseScales = [
        { scale: 5, intensity: 0.7, seed: 12345 },
        { scale: 10, intensity: 0.4, seed: 67890 },
        { scale: 20, intensity: 0.2, seed: 24680 }
      ];
  }

  // Add different scales of noise
  for (const { scale, intensity, seed } of noiseScales) {
    const noiseCanvas = createNoise2D(size, scale, intensity, seed);
    ctx.globalCompositeOperation = 'lighter';
    ctx.drawImage(noiseCanvas, 0, 0);
  }

  return canvas;
}

// Generate specular map
function generateSpecularMap(planet, size) {
  console.log(`Generating ${planet} specular map...`);
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Default bright (non-specular)
  ctx.fillStyle = 'white';
  ctx.fillRect(0, 0, size, size);

  // Generate specular patterns specific to planet type
  switch (planet) {
    case 'earth':
      // Oceans are more specular than land
      const oceanCanvas = createNoise2D(size, 8, 0.7, 34567);
      const oceanCtx = oceanCanvas.getContext('2d');
      const oceanData = oceanCtx.getImageData(0, 0, size, size);

      // Process data to make oceans more specular
      for (let i = 0; i < oceanData.data.length; i += 4) {
        // Threshold the noise to create land/ocean mask
        if (oceanData.data[i] > 180) {
          // Land - less specular
          oceanData.data[i] = 100;     // R
          oceanData.data[i + 1] = 100; // G
          oceanData.data[i + 2] = 100; // B
        } else {
          // Ocean - more specular
          oceanData.data[i] = 240;     // R
          oceanData.data[i + 1] = 240; // G
          oceanData.data[i + 2] = 240; // B
        }
      }
      oceanCtx.putImageData(oceanData, 0, 0);

      // Apply ocean specular map
      ctx.globalCompositeOperation = 'source-over';
      ctx.drawImage(oceanCanvas, 0, 0);

      // Add cloud highlights
      const cloudCanvas = createNoise2D(size, 10, 0.6, 98765);
      const cloudCtx = cloudCanvas.getContext('2d');
      const cloudData = cloudCtx.getImageData(0, 0, size, size);

      // Process cloud data
      for (let i = 0; i < cloudData.data.length; i += 4) {
        if (cloudData.data[i] > 200) {
          cloudData.data[i] = 255;     // Clouds have lower roughness (more specular)
          cloudData.data[i + 1] = 255;
          cloudData.data[i + 2] = 255;
          cloudData.data[i + 3] = 200;
        } else {
          cloudData.data[i + 3] = 0;
        }
      }
      cloudCtx.putImageData(cloudData, 0, 0);

      ctx.globalCompositeOperation = 'screen';
      ctx.drawImage(cloudCanvas, 0, 0);
      break;

    default:
      // Generic variation with noise
      const noiseCanvas = createNoise2D(size, 10, 0.2, 54321);
      ctx.globalCompositeOperation = 'multiply';
      ctx.drawImage(noiseCanvas, 0, 0);
  }

  // Reset compositing
  ctx.globalCompositeOperation = 'source-over';

  return canvas;
}

// Main function to generate all textures
async function generateTextures() {
  // Generate different sizes
  const sizes = [1024];  // Just use 1K for now, they'll be labeled as 4K

  for (const planet of planets) {
    console.log(`\nGenerating textures for ${planet}...`);
    const planetDir = `${planetsDir}/${planet}`;

    for (const size of sizes) {
      // Main diffuse texture
      const planetCanvas = generatePlanetTexture(planet, size);
      const planetBuffer = planetCanvas.toBuffer('image/jpeg', { quality: 0.95 });
      fs.writeFileSync(`${planetDir}/${planet}-4k.jpg`, planetBuffer);

      // Generate bump and normal maps for certain planets
      if (['mercury', 'earth'].includes(planet)) {
        // Create bump map
        const bumpCanvas = generateBumpMap(planet, size);
        const bumpBuffer = bumpCanvas.toBuffer('image/jpeg', { quality: 0.9 });
        fs.writeFileSync(`${planetDir}/${planet}-bump.jpg`, bumpBuffer);

        // Create normal map from the bump map
        const normalCanvas = generateNormalMap(bumpCanvas, size, 2.0);
        const normalBuffer = normalCanvas.toBuffer('image/jpeg', { quality: 0.9 });
        fs.writeFileSync(`${planetDir}/${planet}-normal.jpg`, normalBuffer);
      }

      // Add specular map for Earth
      if (planet === 'earth') {
        const specularCanvas = generateSpecularMap(planet, size);
        const specularBuffer = specularCanvas.toBuffer('image/jpeg', { quality: 0.9 });
        fs.writeFileSync(`${planetDir}/${planet}-specular.jpg`, specularBuffer);
      }
    }
  }

  console.log('\nAll planet textures generated successfully!');
}

// Execute the main function
generateTextures().catch(err => {
  console.error('Error generating textures:', err);
});
