#!/usr/bin/env node

/**
 * Directory Management Script
 * 
 * This script consolidates duplicate directories and files according to
 * the directory management protocol.
 * 
 * It follows these steps:
 * 1. Scan project directories and files
 * 2. Identify duplicates
 * 3. Consolidate duplicates (merge or remove)
 * 4. Update imports and references
 * 5. Clean up unused assets
 * 6. Verify integrity
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const crypto = require('crypto');

// Configuration
const config = {
  rootDir: path.resolve(__dirname, '..'),
  // Directories to consolidate: [source, target]
  directoriesToConsolidate: [
    ['frontend', 'src'],
    ['service-manager/frontend', 'src'],
    ['service-manager/ai_service', 'ai_service']
  ],
  // Files to consolidate: [source, target]
  filesToConsolidate: [
    ['start_services.sh', 'start.sh']
  ],
  // File patterns to scan
  filePatterns: [
    '**/*.py', 
    '**/*.js', 
    '**/*.ts', 
    '**/*.tsx', 
    '**/*.json', 
    '**/*.txt', 
    '**/*.yml', 
    '**/*.yaml', 
    '**/*.babelrc', 
    '**/*.env', 
    '**/*.sh', 
    '**/*.Dockerfile', 
    '**/*.conf', 
    '**/*.xml', 
    '**/*.css', 
    '**/*.html'
  ],
  // Directories to exclude from scanning
  excludeDirs: [
    'node_modules',
    '.git',
    '.next',
    '.venv',
    'build',
    'dist',
    '__pycache__'
  ],
  // Files to exclude from scanning
  excludeFiles: [
    'package-lock.json',
    '.DS_Store'
  ],
  // Backup directory for files before consolidation
  backupDir: '.backups/consolidation'
};

// Utility: Colored console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m'
};

// Utility: Logger
const logger = {
  info: (msg) => console.log(`${colors.blue}[INFO]${colors.reset} ${msg}`),
  success: (msg) => console.log(`${colors.green}[SUCCESS]${colors.reset} ${msg}`),
  warning: (msg) => console.log(`${colors.yellow}[WARNING]${colors.reset} ${msg}`),
  error: (msg) => console.log(`${colors.red}[ERROR]${colors.reset} ${msg}`),
  header: (msg) => console.log(`\n${colors.bright}${colors.cyan}=== ${msg} ===${colors.reset}\n`)
};

// Utility: Create directory recursively
function mkdirp(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

// Utility: Calculate file hash
function getFileHash(filePath) {
  try {
    const fileContent = fs.readFileSync(filePath);
    return crypto.createHash('md5').update(fileContent).digest('hex');
  } catch (error) {
    logger.error(`Failed to hash file ${filePath}: ${error.message}`);
    return null;
  }
}

// Utility: Compare files by content
function areFilesEqual(file1, file2) {
  return getFileHash(file1) === getFileHash(file2);
}

// Utility: Backup file before modification
function backupFile(filePath) {
  const relativePath = path.relative(config.rootDir, filePath);
  const backupPath = path.join(config.rootDir, config.backupDir, relativePath);
  
  mkdirp(path.dirname(backupPath));
  
  try {
    fs.copyFileSync(filePath, backupPath);
    return true;
  } catch (error) {
    logger.error(`Failed to backup file ${filePath}: ${error.message}`);
    return false;
  }
}

// Step 1: Scan project directories and files
function scanDirectory(dir, patterns, excludeDirs, excludeFiles) {
  logger.info(`Scanning directory: ${dir}`);
  
  const files = [];
  
  // Function to scan recursively
  function scan(currentDir) {
    const entries = fs.readdirSync(currentDir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      
      // Skip excluded directories and files
      if (entry.isDirectory()) {
        if (excludeDirs.includes(entry.name)) continue;
        scan(fullPath);
      } else {
        if (excludeFiles.includes(entry.name)) continue;
        
        // Check if file matches any pattern
        const relativePath = path.relative(dir, fullPath);
        if (patterns.some(pattern => matchPattern(relativePath, pattern))) {
          files.push(fullPath);
        }
      }
    }
  }
  
  // Start scanning from the root
  scan(dir);
  
  logger.success(`Found ${files.length} files matching patterns`);
  return files;
}

// Utility: Match file against glob pattern
function matchPattern(filePath, pattern) {
  // Simple glob pattern matching
  // For a real implementation, use a library like minimatch
  const regex = new RegExp(`^${pattern.replace(/\*/g, '.*')}$`);
  return regex.test(filePath);
}

// Step 2: Identify duplicates
function identifyDuplicates(files) {
  logger.info('Identifying duplicate files...');
  
  const filesByHash = {};
  const duplicates = [];
  
  for (const file of files) {
    const hash = getFileHash(file);
    if (!hash) continue;
    
    if (!filesByHash[hash]) {
      filesByHash[hash] = [file];
    } else {
      filesByHash[hash].push(file);
      if (filesByHash[hash].length === 2) {
        duplicates.push(filesByHash[hash]);
      }
    }
  }
  
  logger.success(`Found ${duplicates.length} sets of duplicate files`);
  return duplicates;
}

// Step 3: Consolidate directories
function consolidateDirectories() {
  logger.header('Consolidating Directories');
  
  for (const [sourceDir, targetDir] of config.directoriesToConsolidate) {
    const sourcePath = path.join(config.rootDir, sourceDir);
    const targetPath = path.join(config.rootDir, targetDir);
    
    if (!fs.existsSync(sourcePath)) {
      logger.warning(`Source directory ${sourcePath} does not exist, skipping`);
      continue;
    }
    
    if (!fs.existsSync(targetPath)) {
      logger.info(`Target directory ${targetPath} does not exist, creating it`);
      mkdirp(targetPath);
    }
    
    logger.info(`Consolidating: ${sourceDir} → ${targetDir}`);
    
    // Get files in source directory
    const sourceFiles = scanDirectory(
      sourcePath,
      config.filePatterns,
      config.excludeDirs,
      config.excludeFiles
    );
    
    // Process each file
    for (const sourceFile of sourceFiles) {
      const relativeToSource = path.relative(sourcePath, sourceFile);
      const targetFile = path.join(targetPath, relativeToSource);
      
      // Check if target file exists
      if (fs.existsSync(targetFile)) {
        // Compare files
        if (areFilesEqual(sourceFile, targetFile)) {
          logger.info(`Identical files: ${relativeToSource} (skipping)`);
        } else {
          // Files differ - need to merge or choose one
          logger.warning(`Files differ: ${relativeToSource}`);
          logger.info(`Source: ${sourceFile}`);
          logger.info(`Target: ${targetFile}`);
          
          // Backup both files
          backupFile(sourceFile);
          backupFile(targetFile);
          
          // For services, prefer src/services over others
          if (sourceFile.includes('/services/') && targetFile.includes('/services/')) {
            if (targetDir === 'src') {
              // Keep target (src/services)
              logger.info(`Keeping target file: ${targetFile}`);
            } else {
              // Copy from source
              fs.copyFileSync(sourceFile, targetFile);
              logger.info(`Updated target file: ${targetFile}`);
            }
          } else {
            // Default: keep target file
            logger.info(`Keeping target file (default): ${targetFile}`);
          }
        }
      } else {
        // Target file doesn't exist - copy from source
        logger.info(`Copying to target: ${relativeToSource}`);
        
        // Ensure target directory exists
        mkdirp(path.dirname(targetFile));
        
        // Copy file
        fs.copyFileSync(sourceFile, targetFile);
        logger.success(`Copied: ${targetFile}`);
      }
    }
  }
}

// Step 4: Consolidate specific files
function consolidateFiles() {
  logger.header('Consolidating Files');
  
  for (const [sourceFile, targetFile] of config.filesToConsolidate) {
    const sourcePath = path.join(config.rootDir, sourceFile);
    const targetPath = path.join(config.rootDir, targetFile);
    
    if (!fs.existsSync(sourcePath)) {
      logger.warning(`Source file ${sourcePath} does not exist, skipping`);
      continue;
    }
    
    logger.info(`Consolidating: ${sourceFile} → ${targetFile}`);
    
    // Check if target file exists
    if (fs.existsSync(targetPath)) {
      // Always backup before modifying
      backupFile(targetPath);
      
      if (areFilesEqual(sourcePath, targetPath)) {
        logger.info(`Files are identical, no merge needed`);
      } else {
        logger.info(`Keeping target file and backing up source`);
        backupFile(sourcePath);
      }
    } else {
      // Target doesn't exist - copy from source
      fs.copyFileSync(sourcePath, targetPath);
      logger.success(`Copied: ${sourcePath} → ${targetPath}`);
    }
  }
}

// Step 5: Update imports and references
function updateImports() {
  logger.header('Updating Imports and References');
  
  // Get all JavaScript/TypeScript files
  const jsFiles = scanDirectory(
    config.rootDir,
    ['**/*.js', '**/*.jsx', '**/*.ts', '**/*.tsx'],
    config.excludeDirs,
    config.excludeFiles
  );
  
  for (const file of jsFiles) {
    // Read file
    const content = fs.readFileSync(file, 'utf8');
    let updated = content;
    
    // Check for imports from consolidated directories
    for (const [sourceDir, targetDir] of config.directoriesToConsolidate) {
      // Replace import paths
      // This is a simplified approach - a real implementation would use an AST parser
      const sourceImport = new RegExp(`from\\s+['"]\\.\\.?\\/?${sourceDir}`, 'g');
      const targetImport = `from '@/${targetDir}`;
      updated = updated.replace(sourceImport, targetImport);
      
      // Also check for requires
      const sourceRequire = new RegExp(`require\\(['"]\\.\\.?\\/?${sourceDir}`, 'g');
      const targetRequire = `require('@/${targetDir}`;
      updated = updated.replace(sourceRequire, targetRequire);
    }
    
    // If changes were made, update the file
    if (updated !== content) {
      logger.info(`Updating imports in ${file}`);
      backupFile(file);
      fs.writeFileSync(file, updated, 'utf8');
    }
  }
}

// Step 6: Remove now-redundant directories and files
function cleanupRedundantAssets() {
  logger.header('Cleaning Up Redundant Assets');
  
  // We don't actually delete anything during the script run to prevent mistakes
  // Instead, we list directories that should be manually checked and removed
  
  for (const [sourceDir] of config.directoriesToConsolidate) {
    const sourcePath = path.join(config.rootDir, sourceDir);
    if (fs.existsSync(sourcePath)) {
      logger.warning(`Directory ${sourceDir} should be manually checked and removed after verification`);
    }
  }
  
  for (const [sourceFile] of config.filesToConsolidate) {
    const sourcePath = path.join(config.rootDir, sourceFile);
    if (fs.existsSync(sourcePath)) {
      logger.warning(`File ${sourceFile} should be manually checked and removed after verification`);
    }
  }
}

// Step 7: Verify integrity (simplified - just run npm build to check for errors)
function verifyIntegrity() {
  logger.header('Verifying Project Integrity');
  
  try {
    logger.info('Running lint check...');
    execSync('npm run lint', { cwd: config.rootDir, stdio: 'inherit' });
    logger.success('Lint check passed');
  } catch (error) {
    logger.error('Lint check failed');
  }
  
  try {
    logger.info('Building project to verify integrity...');
    execSync('npm run build', { cwd: config.rootDir, stdio: 'inherit' });
    logger.success('Build successful - project integrity verified');
  } catch (error) {
    logger.error('Build failed - project may have integrity issues');
  }
}

// Main function to orchestrate the process
async function main() {
  logger.header('Directory Management Script');
  
  // Create backup directory
  const backupDirPath = path.join(config.rootDir, config.backupDir);
  mkdirp(backupDirPath);
  logger.info(`Created backup directory: ${backupDirPath}`);
  
  try {
    // Step 3: Consolidate directories first
    consolidateDirectories();
    
    // Step 4: Consolidate individual files
    consolidateFiles();
    
    // Step 5: Update imports and references
    updateImports();
    
    // Step 6: Clean up redundant assets (list them)
    cleanupRedundantAssets();
    
    // Step 7: Verify project integrity
    verifyIntegrity();
    
    logger.header('Directory Management Complete');
    logger.success('The project structure has been consolidated according to the protocol.');
    logger.info(`Backups of modified files are in: ${backupDirPath}`);
    logger.warning('Please manually verify all changes before removing redundant files and directories.');
  } catch (error) {
    logger.error(`Directory management failed: ${error.message}`);
    logger.error(error.stack);
    process.exit(1);
  }
}

// Run the main function
main().catch(error => {
  logger.error(`Unhandled error: ${error.message}`);
  logger.error(error.stack);
  process.exit(1);
}); 