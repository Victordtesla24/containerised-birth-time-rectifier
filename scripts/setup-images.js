/**
 * This script copies images from the root /images directory to the Next.js public directory
 * so they can be served by the Next.js application.
 */

const fs = require('fs');
const path = require('path');

// Define source and destination directories
const sourceDir = path.join(__dirname, '..', 'images');
const targetDir = path.join(__dirname, '..', 'public', 'images');

// Create the target directory if it doesn't exist
function ensureDirectoryExists(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    console.log(`Created directory: ${dirPath}`);
  }
}

// Copy a file from source to destination
function copyFile(source, destination) {
  fs.copyFileSync(source, destination);
  console.log(`Copied: ${source} -> ${destination}`);
}

// Copy a directory recursively
function copyDirectory(source, destination) {
  ensureDirectoryExists(destination);
  
  const items = fs.readdirSync(source);
  
  for (const item of items) {
    const sourcePath = path.join(source, item);
    const destPath = path.join(destination, item);
    
    const stats = fs.statSync(sourcePath);
    
    if (stats.isDirectory()) {
      copyDirectory(sourcePath, destPath);
    } else {
      // Only copy image files
      const ext = path.extname(item).toLowerCase();
      if (['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'].includes(ext)) {
        copyFile(sourcePath, destPath);
      }
    }
  }
}

// Main function to copy all images
function setupImages() {
  console.log('Setting up images for the application...');
  
  try {
    ensureDirectoryExists(targetDir);
    copyDirectory(sourceDir, targetDir);
    console.log('Images setup completed successfully!');
  } catch (error) {
    console.error('Error setting up images:', error);
    process.exit(1);
  }
}

// Run the setup
setupImages(); 