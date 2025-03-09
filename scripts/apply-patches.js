/**
 * This script applies patches to node_modules libraries
 * to fix compatibility issues.
 */
const fs = require('fs');
const path = require('path');

// Paths
const ROOT_DIR = path.resolve(__dirname, '..');
const PATCHES_DIR = path.resolve(ROOT_DIR, 'patches');
const NODE_MODULES_DIR = path.resolve(ROOT_DIR, 'node_modules');

/**
 * Apply patches to three-mesh-bvh
 */
function applyThreeMeshBvhPatches() {
  console.log('Applying patches to three-mesh-bvh...');

  const sourcePath = path.resolve(PATCHES_DIR, 'three-mesh-bvh/fix-batched-mesh.js');
  const targetPath = path.resolve(NODE_MODULES_DIR, 'three-mesh-bvh/src/utils/ExtensionUtilities.js');

  if (!fs.existsSync(sourcePath)) {
    console.error(`Patch file not found: ${sourcePath}`);
    process.exit(1);
  }

  if (!fs.existsSync(targetPath)) {
    console.error(`Target file not found: ${targetPath}`);
    process.exit(1);
  }

  // Create a backup of the original file
  const backupPath = `${targetPath}.original`;
  if (!fs.existsSync(backupPath)) {
    console.log(`Creating backup of original file at ${backupPath}`);
    fs.copyFileSync(targetPath, backupPath);
  }

  // Apply the patch by reading and writing content to ensure proper encoding
  console.log(`Applying patch to ${targetPath}`);
  const patchContent = fs.readFileSync(sourcePath, 'utf8');
  fs.writeFileSync(targetPath, patchContent, 'utf8');

  console.log('Patch applied successfully!');
}

// Run all patches
function applyAllPatches() {
  // Apply patches to fix three-mesh-bvh BatchedMesh compatibility
  applyThreeMeshBvhPatches();

  console.log('All patches applied successfully!');
}

// Run the script
applyAllPatches();
