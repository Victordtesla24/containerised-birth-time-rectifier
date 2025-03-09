// Generate procedural textures for the sun
const fs = require('fs');
const { createCanvas } = require('canvas');

// Create directory if it doesn't exist
const outputDir = 'public/images/planets/sun';
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

// Helper function for noise
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

// Generate sun surface texture (orangish with granular pattern)
function generateSunSurface(size) {
  console.log('Generating sun surface texture...');
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Base orange color
  ctx.fillStyle = '#FF9D00';
  ctx.fillRect(0, 0, size, size);

  // Create multi-layer noise for granulation
  const noise1 = createNoise2D(size, 8, 0.6, 12345);
  const noise2 = createNoise2D(size, 16, 0.3, 67890);
  const noise3 = createNoise2D(size, 32, 0.1, 13579);

  // Draw the noise layers with different blending modes
  ctx.globalCompositeOperation = 'multiply';
  ctx.drawImage(noise1, 0, 0);

  ctx.globalCompositeOperation = 'overlay';
  ctx.drawImage(noise2, 0, 0);

  ctx.globalCompositeOperation = 'darken';
  ctx.drawImage(noise3, 0, 0);

  // Restore normal blending
  ctx.globalCompositeOperation = 'source-over';

  // Add radial gradient to simulate limb darkening
  const gradient = ctx.createRadialGradient(
    size/2, size/2, 0,          // inner circle center and radius
    size/2, size/2, size/2      // outer circle center and radius
  );
  gradient.addColorStop(0, 'rgba(255, 180, 50, 0.05)');  // center - barely visible
  gradient.addColorStop(0.7, 'rgba(255, 150, 30, 0.1)');  // mid-radius
  gradient.addColorStop(1, 'rgba(200, 100, 0, 0.3)');   // edge - more pronounced darkening

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  return canvas;
}

// Generate sun chromatic texture (yellower with flow patterns)
function generateSunChromatic(size) {
  console.log('Generating sun chromatic texture...');
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Base yellow color
  ctx.fillStyle = '#FFFF00';
  ctx.fillRect(0, 0, size, size);

  // Create flow pattern with noise
  const noise1 = createNoise2D(size, 6, 0.7, 24680);
  const noise2 = createNoise2D(size, 20, 0.4, 97531);

  // Draw with flow pattern
  ctx.globalCompositeOperation = 'multiply';
  ctx.drawImage(noise1, 0, 0);

  ctx.globalCompositeOperation = 'overlay';
  ctx.drawImage(noise2, 0, 0);

  // Restore normal blending
  ctx.globalCompositeOperation = 'source-over';

  // Add outer glow
  const gradient = ctx.createRadialGradient(
    size/2, size/2, size/2 * 0.7,  // inner circle
    size/2, size/2, size/2         // outer circle
  );
  gradient.addColorStop(0, 'rgba(255, 255, 200, 0)');
  gradient.addColorStop(1, 'rgba(255, 220, 150, 0.3)');

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  return canvas;
}

// Generate sun normal map (for surface relief)
function generateSunNormal(size) {
  console.log('Generating sun normal map...');
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Base normal map color (pointing outward)
  ctx.fillStyle = '#8080FF';  // Default normal pointing out (r=0.5, g=0.5, b=1.0)
  ctx.fillRect(0, 0, size, size);

  // Create height map with multiple noise layers
  const heightMapCanvas = createCanvas(size, size);
  const heightCtx = heightMapCanvas.getContext('2d');

  // Generate height map with multiple scales of noise
  heightCtx.fillStyle = 'black';
  heightCtx.fillRect(0, 0, size, size);

  // Add different scales of noise
  const noiseScales = [
    { scale: 4, intensity: 0.6, seed: 11111 },
    { scale: 8, intensity: 0.3, seed: 22222 },
    { scale: 16, intensity: 0.1, seed: 33333 }
  ];

  for (const { scale, intensity, seed } of noiseScales) {
    const noiseCanvas = createNoise2D(size, scale, intensity, seed);
    heightCtx.globalCompositeOperation = 'lighter';
    heightCtx.drawImage(noiseCanvas, 0, 0);
  }

  // Convert height map to normal map
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

      // Scale factor for normal intensity (higher = more pronounced bumps)
      const scale = 2.0;

      // Normal calculation
      const normalX = -dX * scale;
      const normalY = -dY * scale;
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

// Generate sun spots texture
function generateSunSpots(size) {
  console.log('Generating sun spots texture...');
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Black background (no spots)
  ctx.fillStyle = 'black';
  ctx.fillRect(0, 0, size, size);

  // Add some random sunspots
  const numSpots = Math.floor(5 + Math.random() * 10);  // 5-15 spots

  for (let i = 0; i < numSpots; i++) {
    // Random position - spots tend to form in bands around equator
    const angle = Math.random() * Math.PI * 2;
    const distanceFromCenter = (0.2 + Math.random() * 0.6) * size/2;  // Not too close to center or edge

    // Calculate latitude (y-coordinate in texture space)
    // Spots are more common at specific latitudes (band distribution)
    let latitude = (Math.random() - 0.5) * 0.6;  // -0.3 to 0.3 (restricted to bands)
    latitude = Math.sign(latitude) * Math.pow(Math.abs(latitude), 0.7);  // Concentrate in bands

    const x = size/2 + Math.cos(angle) * distanceFromCenter;
    const y = size/2 + latitude * size;

    // Random spot size
    const radius = 5 + Math.random() * 30;

    // Draw spot with gradient
    const gradient = ctx.createRadialGradient(
      x, y, 0,
      x, y, radius
    );
    gradient.addColorStop(0, 'rgba(255, 255, 255, 0.8)');  // White at center
    gradient.addColorStop(0.3, 'rgba(180, 100, 50, 0.6)');  // Brown middle
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');         // Transparent edge

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();

    // Sometimes add a secondary spot (bipolar spots)
    if (Math.random() < 0.5) {
      const deltaAngle = (Math.random() * 0.2 - 0.1) + Math.PI;  // Opposite side with small variation
      const deltaDistance = distanceFromCenter * (0.9 + Math.random() * 0.2);  // Similar distance

      const x2 = size/2 + Math.cos(angle + deltaAngle) * deltaDistance;
      const y2 = size/2 + latitude * size;

      const radius2 = radius * (0.7 + Math.random() * 0.6);  // Related size

      const gradient2 = ctx.createRadialGradient(
        x2, y2, 0,
        x2, y2, radius2
      );
      gradient2.addColorStop(0, 'rgba(255, 255, 255, 0.7)');
      gradient2.addColorStop(0.3, 'rgba(180, 100, 50, 0.5)');
      gradient2.addColorStop(1, 'rgba(0, 0, 0, 0)');

      ctx.fillStyle = gradient2;
      ctx.beginPath();
      ctx.arc(x2, y2, radius2, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  return canvas;
}

// Main function to generate all textures
async function generateTextures() {
  const textureSizes = [1024]; // We only need one size for now

  for (const size of textureSizes) {
    // Sun surface texture
    const surfaceCanvas = generateSunSurface(size);
    const surfaceBuffer = surfaceCanvas.toBuffer('image/jpeg', { quality: 0.9 });
    fs.writeFileSync(`${outputDir}/sun_surface.jpg`, surfaceBuffer);

    // Sun chromatic texture
    const chromaticCanvas = generateSunChromatic(size);
    const chromaticBuffer = chromaticCanvas.toBuffer('image/jpeg', { quality: 0.9 });
    fs.writeFileSync(`${outputDir}/sun_chromatic.jpg`, chromaticBuffer);

    // Sun normal map
    const normalCanvas = generateSunNormal(size);
    const normalBuffer = normalCanvas.toBuffer('image/jpeg', { quality: 0.9 });
    fs.writeFileSync(`${outputDir}/sun_normal.jpg`, normalBuffer);

    // Sun spots
    const spotsCanvas = generateSunSpots(size);
    const spotsBuffer = spotsCanvas.toBuffer('image/jpeg', { quality: 0.9 });
    fs.writeFileSync(`${outputDir}/sun_spots.jpg`, spotsBuffer);
  }

  console.log('All sun textures generated successfully!');
}

// Execute the main function
generateTextures().catch(err => {
  console.error('Error generating textures:', err);
});
