#!/usr/bin/env node

/**
 * Script to consolidate and clean up the project structure for Vercel deployment
 * This script will:
 * 1. Scan for duplicate files in service-manager/frontend and src
 * 2. Move any unique files from service-manager/frontend to src if needed
 * 3. Remove redundant files and directories
 * 4. Update imports and references as needed
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const ROOT_DIR = process.cwd();
const SRC_DIR = path.join(ROOT_DIR, 'src');
const SERVICE_MANAGER_DIR = path.join(ROOT_DIR, 'service-manager');
const SERVICE_MANAGER_FRONTEND_DIR = path.join(SERVICE_MANAGER_DIR, 'frontend');
const AI_SERVICE_DIR = path.join(ROOT_DIR, 'ai_service');

// Console colors
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

console.log(`${colors.cyan}=== Birth Time Rectifier - Project Consolidation for Vercel ===${colors.reset}`);

// Helper functions
function ensureDirectoryExists(directory) {
  if (!fs.existsSync(directory)) {
    fs.mkdirSync(directory, { recursive: true });
  }
}

// 1. Scan for duplicates between service-manager/frontend and src
function scanForDuplicates() {
  console.log(`\n${colors.yellow}Scanning for duplicate files...${colors.reset}`);

  if (!fs.existsSync(SERVICE_MANAGER_FRONTEND_DIR)) {
    console.log(`${colors.blue}No service-manager/frontend directory found.${colors.reset}`);
    return { duplicates: [], uniqueInServiceManager: [] };
  }

  try {
    // Get all files from service-manager/frontend
    const serviceManagerFiles = execSync(`find ${SERVICE_MANAGER_FRONTEND_DIR} -type f | sort`)
      .toString()
      .split('\n')
      .filter(Boolean);

    const duplicates = [];
    const uniqueInServiceManager = [];

    // Check for duplicates
    for (const file of serviceManagerFiles) {
      const relativePath = path.relative(SERVICE_MANAGER_FRONTEND_DIR, file);
      const srcPath = path.join(SRC_DIR, relativePath);

      if (fs.existsSync(srcPath)) {
        duplicates.push({
          serviceManagerPath: file,
          srcPath,
          relativePath,
          identical: fs.readFileSync(file, 'utf8') === fs.readFileSync(srcPath, 'utf8')
        });
      } else {
        uniqueInServiceManager.push({
          serviceManagerPath: file,
          relativePath
        });
      }
    }

    // Report findings
    console.log(`Found ${duplicates.length} duplicate files and ${uniqueInServiceManager.length} unique files in service-manager/frontend`);

    return { duplicates, uniqueInServiceManager };
  } catch (error) {
    console.error(`${colors.red}Error scanning for duplicates:${colors.reset}`, error.message);
    return { duplicates: [], uniqueInServiceManager: [] };
  }
}

// 2. Consolidate duplicate files
function consolidateDuplicates(duplicates) {
  console.log(`\n${colors.yellow}Consolidating duplicate files...${colors.reset}`);

  const identicalCount = duplicates.filter(d => d.identical).length;
  const differentCount = duplicates.length - identicalCount;

  console.log(`${identicalCount} identical files, ${differentCount} different files`);

  // For identical files, we don't need to do anything
  if (identicalCount > 0) {
    console.log(`${colors.green}Skipping ${identicalCount} identical files${colors.reset}`);
  }

  // For different files, we need to decide what to do
  if (differentCount > 0) {
    console.log(`${colors.yellow}Found ${differentCount} files with differences:${colors.reset}`);

    // List the different files for manual review
    duplicates.filter(d => !d.identical).forEach(d => {
      console.log(`  ${colors.magenta}${d.relativePath}${colors.reset}`);
      console.log(`    Service Manager: ${d.serviceManagerPath}`);
      console.log(`    Src: ${d.srcPath}`);
    });

    console.log(`${colors.yellow}Please review these files manually to determine which version to keep.${colors.reset}`);
  }
}

// 3. Move unique files from service-manager to src
function moveUniqueFiles(uniqueFiles) {
  console.log(`\n${colors.yellow}Moving unique files from service-manager to src...${colors.reset}`);

  if (uniqueFiles.length === 0) {
    console.log(`${colors.blue}No unique files to move.${colors.reset}`);
    return;
  }

  let movedCount = 0;

  for (const file of uniqueFiles) {
    const targetPath = path.join(SRC_DIR, file.relativePath);
    const targetDir = path.dirname(targetPath);

    // Ensure the target directory exists
    ensureDirectoryExists(targetDir);

    try {
      // Copy the file
      fs.copyFileSync(file.serviceManagerPath, targetPath);
      console.log(`${colors.green}Copied${colors.reset} ${file.relativePath}`);
      movedCount++;
    } catch (error) {
      console.error(`${colors.red}Error copying ${file.relativePath}:${colors.reset} ${error.message}`);
    }
  }

  console.log(`${colors.green}Moved ${movedCount} unique files to src directory.${colors.reset}`);
}

// 4. Clean up API endpoints structure
function cleanupApiEndpoints() {
  console.log(`\n${colors.yellow}Cleaning up API endpoints structure...${colors.reset}`);

  const API_DIR = path.join(SRC_DIR, 'pages', 'api');

  if (!fs.existsSync(API_DIR)) {
    console.log(`${colors.blue}No API directory found.${colors.reset}`);
    return;
  }

  // Scan for duplicate API endpoints
  try {
    // Get all API files
    const apiFiles = fs.readdirSync(API_DIR, { withFileTypes: true });

    // Check for duplicates with similar functionality
    const apiEndpoints = new Map();
    let redundantCount = 0;

    // Group similar endpoints
    for (const dirent of apiFiles) {
      const name = dirent.name;

      // Skip directories for now
      if (dirent.isDirectory()) continue;

      // Check if this is a TypeScript file
      if (!name.endsWith('.ts') && !name.endsWith('.tsx')) continue;

      // Read the file to analyze its content
      const filePath = path.join(API_DIR, name);
      const content = fs.readFileSync(filePath, 'utf8');

      // Simple heuristic: files with similar function might have similar content
      const contentHash = content.length.toString(); // A very basic "hash"

      if (!apiEndpoints.has(contentHash)) {
        apiEndpoints.set(contentHash, []);
      }

      apiEndpoints.get(contentHash).push({ name, path: filePath, content });
    }

    // Check for similar endpoints
    for (const [hash, endpoints] of apiEndpoints.entries()) {
      if (endpoints.length > 1) {
        console.log(`${colors.yellow}Potentially similar endpoints:${colors.reset}`);
        endpoints.forEach(endpoint => {
          console.log(`  ${endpoint.name}`);
        });

        // If names are similar, they're likely duplicates
        const names = endpoints.map(ep => ep.name.replace('.ts', '').replace('.tsx', ''));

        // Check for simple variations like 'chart.ts' and 'charts.ts'
        const normalized = names.map(n => n.replace(/s$/, ''));
        const uniqueNormalized = new Set(normalized);

        if (uniqueNormalized.size < names.length) {
          console.log(`${colors.yellow}These endpoints appear to be variations of the same functionality.${colors.reset}`);
          console.log(`${colors.yellow}Consider consolidating them.${colors.reset}`);
          redundantCount++;
        }
      }
    }

    if (redundantCount === 0) {
      console.log(`${colors.green}No obviously redundant API endpoints found.${colors.reset}`);
    } else {
      console.log(`${colors.yellow}Found ${redundantCount} potentially redundant endpoint groups.${colors.reset}`);
      console.log(`${colors.yellow}Please review these manually.${colors.reset}`);
    }
  } catch (error) {
    console.error(`${colors.red}Error analyzing API endpoints:${colors.reset}`, error.message);
  }
}

// 5. Ensure proper Vercel configuration
function ensureVercelConfig() {
  console.log(`\n${colors.yellow}Ensuring proper Vercel configuration...${colors.reset}`);

  // Check for vercel.json
  const vercelConfigPath = path.join(ROOT_DIR, 'vercel.json');

  if (fs.existsSync(vercelConfigPath)) {
    console.log(`${colors.green}vercel.json exists.${colors.reset}`);
  } else {
    console.log(`${colors.red}vercel.json does not exist.${colors.reset}`);
    console.log(`${colors.yellow}Please run the prepare-vercel-deployment.js script first.${colors.reset}`);
  }

  // Check for proper Next.js configuration
  const nextConfigPath = path.join(ROOT_DIR, 'next.config.js');

  if (fs.existsSync(nextConfigPath)) {
    const nextConfig = fs.readFileSync(nextConfigPath, 'utf8');

    if (nextConfig.includes('process.env.VERCEL')) {
      console.log(`${colors.green}next.config.js has Vercel configuration.${colors.reset}`);
    } else {
      console.log(`${colors.yellow}next.config.js does not have Vercel-specific configuration.${colors.reset}`);
      console.log(`${colors.yellow}Please run the prepare-vercel-deployment.js script.${colors.reset}`);
    }
  } else {
    console.log(`${colors.red}next.config.js does not exist.${colors.reset}`);
  }
}

// 6. Create a consolidated file listing
function createFileListing() {
  console.log(`\n${colors.yellow}Creating consolidated file listing...${colors.reset}`);

  try {
    // Get all source files
    const sourceFiles = execSync(`find ${SRC_DIR} -type f -not -path "*/node_modules/*" -not -path "*/.next/*" | sort`)
      .toString()
      .split('\n')
      .filter(Boolean)
      .map(file => path.relative(ROOT_DIR, file));

    // Write to file listing
    const fileListPath = path.join(ROOT_DIR, 'vercel-deployment-files.txt');
    fs.writeFileSync(fileListPath, sourceFiles.join('\n'));

    console.log(`${colors.green}Created file listing at ${fileListPath}${colors.reset}`);
  } catch (error) {
    console.error(`${colors.red}Error creating file listing:${colors.reset}`, error.message);
  }
}

// Main function
function main() {
  try {
    // 1. Scan for duplicates
    const { duplicates, uniqueInServiceManager } = scanForDuplicates();

    // 2. Consolidate duplicates
    consolidateDuplicates(duplicates);

    // 3. Move unique files
    moveUniqueFiles(uniqueInServiceManager);

    // 4. Clean up API endpoints
    cleanupApiEndpoints();

    // 5. Ensure proper Vercel configuration
    ensureVercelConfig();

    // 6. Create file listing
    createFileListing();

    console.log(`\n${colors.green}=== Consolidation complete! ===${colors.reset}`);
    console.log(`${colors.cyan}Next steps:${colors.reset}`);
    console.log(`1. Review any duplicate files with differences`);
    console.log(`2. Review potentially redundant API endpoints`);
    console.log(`3. Run the prepare-vercel-deployment.js script if needed`);
    console.log(`4. Commit and push the changes to GitHub`);
    console.log(`5. Set up Vercel deployment as outlined in VERCEL_DEPLOYMENT.md`);
  } catch (error) {
    console.error(`${colors.red}Consolidation failed:${colors.reset}`, error.message);
  }
}

// Run the script
main();
