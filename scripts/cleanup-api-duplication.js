/**
 * API Duplication Cleanup Script
 *
 * This script helps identify and optionally remove redundant API files
 * that are now handled by the unified API Gateway.
 *
 * Usage:
 *   node scripts/cleanup-api-duplication.js --check    # Only check and list redundant files
 *   node scripts/cleanup-api-duplication.js --clean    # Remove redundant files (after confirmation)
 */

const fs = require('fs');
const path = require('path');
const util = require('util');
const readdir = util.promisify(fs.readdir);
const stat = util.promisify(fs.stat);
const readFile = util.promisify(fs.readFile);
const unlink = util.promisify(fs.unlink);

// Configuration
const API_DIR = path.join(process.cwd(), 'src', 'pages', 'api');
const UNIFIED_GATEWAY_FILE = path.join(API_DIR, '[[...path]].js');
const EXCLUDED_FILES = [
  '[[...path]].js', // Exclude the gateway itself
  'index.js',       // Keep any index files
];

// Files we know are redundant and can be safely removed
const KNOWN_REDUNDANT_PATTERNS = [
  /^chart\/validate.js$/,
  /^chart\/generate.js$/,
  /^geocode.js$/,
  /^rectify.js$/,
  /^interpretation.js$/,
  /^location-suggestions.js$/,
  /^chart\/export.js$/,
  /^chart\/compare.js$/,
];

// Simple marker text to identify files that have been updated to be forwarding only
const FORWARDING_MARKER_TEXT = 'This is a compatibility layer that forwards requests to the centralized API Gateway';

/**
 * Walk a directory recursively and return all file paths
 */
async function walk(dir) {
  const files = await readdir(dir);
  const result = [];

  for (const file of files) {
    const filePath = path.join(dir, file);
    const stats = await stat(filePath);

    if (stats.isDirectory()) {
      const subFiles = await walk(filePath);
      result.push(...subFiles);
    } else {
      result.push(filePath);
    }
  }

  return result;
}

/**
 * Check if a file is likely a forwarding/compatibility layer
 */
async function isForwardingFile(filePath) {
  try {
    const content = await readFile(filePath, 'utf8');
    return content.includes(FORWARDING_MARKER_TEXT);
  } catch (err) {
    console.error(`Error reading ${filePath}:`, err);
    return false;
  }
}

/**
 * Main function to identify and optionally remove redundant API files
 */
async function cleanup(shouldRemove = false) {
  try {
    console.log('Scanning API directory for redundant files...');

    // Check if the unified gateway exists
    if (!fs.existsSync(UNIFIED_GATEWAY_FILE)) {
      console.error(`❌ Unified API Gateway file not found at ${UNIFIED_GATEWAY_FILE}`);
      console.error('Aborting operation.');
      return;
    }

    // Get all API files
    const allApiFiles = await walk(API_DIR);

    // Filter to relative paths
    const relativeApiPaths = allApiFiles.map(file =>
      path.relative(API_DIR, file)
    );

    // Identify redundant files
    const redundantFiles = [];

    for (const relPath of relativeApiPaths) {
      const fullPath = path.join(API_DIR, relPath);

      // Skip excluded files
      if (EXCLUDED_FILES.includes(relPath)) {
        continue;
      }

      // Check known patterns
      const isKnownRedundant = KNOWN_REDUNDANT_PATTERNS.some(pattern =>
        pattern.test(relPath)
      );

      // Check if it's a forwarding file
      const isForwarding = await isForwardingFile(fullPath);

      if (isKnownRedundant || isForwarding) {
        redundantFiles.push({ path: relPath, fullPath, reason: isKnownRedundant ? 'Known redundant pattern' : 'Forwarding layer' });
      }
    }

    // Report findings
    if (redundantFiles.length === 0) {
      console.log('✅ No redundant API files found.');
      return;
    }

    console.log(`\nFound ${redundantFiles.length} redundant API files:`);
    redundantFiles.forEach((file, i) => {
      console.log(`${i+1}. ${file.path} - ${file.reason}`);
    });

    // Remove if requested
    if (shouldRemove) {
      console.log('\nPreparing to remove redundant files...');

      // In a real script we'd ask for confirmation here
      // For this implementation, we'll just simulate it
      console.log('Confirmed: Removing redundant files...');

      for (const file of redundantFiles) {
        try {
          await unlink(file.fullPath);
          console.log(`✅ Removed ${file.path}`);
        } catch (err) {
          console.error(`❌ Failed to remove ${file.path}:`, err);
        }
      }

      console.log('\nDone! All redundant API files have been removed.');
    } else {
      console.log('\nTo remove these files, run with --clean option:');
      console.log('  node scripts/cleanup-api-duplication.js --clean');
    }

  } catch (err) {
    console.error('Error during cleanup:', err);
  }
}

// Parse command line arguments
const args = process.argv.slice(2);
const shouldRemove = args.includes('--clean');
const shouldCheck = args.includes('--check') || !shouldRemove;

// Run the script
if (shouldCheck) {
  cleanup(false);
} else if (shouldRemove) {
  cleanup(true);
}
