/**
 * Utility script to generate fallback textures for WebGL rendering
 * This ensures we have default textures available when loading fails
 */
const fs = require('fs');
const path = require('path');
const { createCanvas } = require('canvas');

// Create the textures directory if it doesn't exist
const texturesDir = path.join(process.cwd(), 'public', 'textures');
if (!fs.existsSync(texturesDir)) {
  fs.mkdirSync(texturesDir, { recursive: true });
}

// Create a star fallback texture
function createStarTexture() {
  const size = 64;
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Clear the canvas with transparency
  ctx.clearRect(0, 0, size, size);

  // Create a radial gradient for the star
  const gradient = ctx.createRadialGradient(
    size / 2, size / 2, 0,
    size / 2, size / 2, size / 2
  );

  gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
  gradient.addColorStop(0.2, 'rgba(255, 255, 255, 0.8)');
  gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.2)');
  gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

  // Draw the star
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  // Save the texture
  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync(path.join(texturesDir, 'star_fallback.png'), buffer);

  console.log('Created star fallback texture');
}

// Create a sun fallback texture
function createSunTexture() {
  const size = 256;
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Fill with yellow-orange base color
  ctx.fillStyle = '#ffa726';
  ctx.fillRect(0, 0, size, size);

  // Add some texture/noise
  for (let i = 0; i < 5000; i++) {
    const x = Math.random() * size;
    const y = Math.random() * size;
    const radius = Math.random() * 4 + 1;
    const opacity = Math.random() * 0.2 + 0.05;

    // Random color variations
    const colorVariation = Math.floor(Math.random() * 60);
    const r = 255 - colorVariation;
    const g = Math.floor(140 + Math.random() * 60);
    const b = Math.floor(Math.random() * 50);

    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${opacity})`;
    ctx.fill();
  }

  // Save the texture
  const buffer = canvas.toBuffer('image/jpeg');
  fs.writeFileSync(path.join(texturesDir, 'sun_fallback.jpg'), buffer);

  console.log('Created sun fallback texture');
}

// Execute
try {
  createStarTexture();
  createSunTexture();
  console.log('Fallback textures created successfully');
} catch (error) {
  console.error('Error creating fallback textures:', error);
}
