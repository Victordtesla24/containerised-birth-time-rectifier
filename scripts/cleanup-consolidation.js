#!/usr/bin/env node

/**
 * Cleanup Consolidation Script
 * 
 * This script helps finalize the consolidation process by:
 * 1. Checking if any files remain in source directories
 * 2. Providing a summary of what will be removed
 * 3. Safely removing consolidated directories after confirmation
 * 4. Providing rollback instructions
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const readline = require('readline');

// Configuration
const config = {
  rootDir: path.resolve(__dirname, '..'),
  // Directories that have been consolidated and should be removed
  consolidatedDirs: [
    'frontend',
    'service-manager/frontend',
    'service-manager/ai_service'
  ],
  // Files that have been consolidated and should be removed
  consolidatedFiles: [
    'start_services.sh'
  ],
  // Backup directory created by the consolidation script
  backupDir: '.backups/consolidation',
  // Rollback backup directory
  rollbackDir: '.backups/rollback_consolidation'
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
    return true;
  }
  return false;
}

// Utility: Check if directory exists and is not empty
function directoryHasContents(dir) {
  if (!fs.existsSync(dir)) {
    return false;
  }
  
  const contents = fs.readdirSync(dir);
  return contents.length > 0;
}

// Utility: Get all files in a directory recursively
function getAllFiles(dir, results = []) {
  if (!fs.existsSync(dir)) {
    return results;
  }
  
  const files = fs.readdirSync(dir);
  
  files.forEach(file => {
    const fullPath = path.join(dir, file);
    
    if (fs.statSync(fullPath).isDirectory()) {
      getAllFiles(fullPath, results);
    } else {
      results.push(fullPath);
    }
  });
  
  return results;
}

// Utility: Create a backup of a directory or file before removing
function createBackup(sourcePath, backupDir) {
  const relativePath = path.relative(config.rootDir, sourcePath);
  const backupPath = path.join(config.rootDir, backupDir, relativePath);
  
  try {
    if (fs.existsSync(sourcePath)) {
      if (fs.statSync(sourcePath).isDirectory()) {
        // Create the backup directory
        mkdirp(backupPath);
        
        // Copy all files from source to backup
        const files = getAllFiles(sourcePath);
        files.forEach(file => {
          const relativeFilePath = path.relative(sourcePath, file);
          const backupFilePath = path.join(backupPath, relativeFilePath);
          
          // Create directory structure in backup
          mkdirp(path.dirname(backupFilePath));
          
          // Copy the file
          fs.copyFileSync(file, backupFilePath);
        });
        
        logger.info(`Backed up directory: ${relativePath}`);
        return true;
      } else {
        // Create the directory structure in backup
        mkdirp(path.dirname(backupPath));
        
        // Copy the file
        fs.copyFileSync(sourcePath, backupPath);
        
        logger.info(`Backed up file: ${relativePath}`);
        return true;
      }
    }
  } catch (error) {
    logger.error(`Failed to backup ${relativePath}: ${error.message}`);
    return false;
  }
  
  return false;
}

// Function to check consolidated directories and files
function checkConsolidatedItems() {
  logger.header('Checking Consolidated Items');
  
  const pendingRemovals = [];
  
  // Check directories
  config.consolidatedDirs.forEach(dirPath => {
    const fullDirPath = path.join(config.rootDir, dirPath);
    
    if (directoryHasContents(fullDirPath)) {
      const files = getAllFiles(fullDirPath);
      logger.warning(`Directory ${dirPath} still has ${files.length} files`);
      
      pendingRemovals.push({
        type: 'directory',
        path: dirPath,
        fileCount: files.length
      });
    } else if (fs.existsSync(fullDirPath)) {
      logger.info(`Directory ${dirPath} exists but is empty`);
      
      pendingRemovals.push({
        type: 'directory',
        path: dirPath,
        fileCount: 0
      });
    } else {
      logger.success(`Directory ${dirPath} doesn't exist, nothing to remove`);
    }
  });
  
  // Check files
  config.consolidatedFiles.forEach(filePath => {
    const fullFilePath = path.join(config.rootDir, filePath);
    
    if (fs.existsSync(fullFilePath)) {
      logger.warning(`File ${filePath} still exists`);
      
      pendingRemovals.push({
        type: 'file',
        path: filePath
      });
    } else {
      logger.success(`File ${filePath} already removed`);
    }
  });
  
  return pendingRemovals;
}

// Function to create a CLI interface for user confirmation
function createCLI() {
  return readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
}

// Function to prompt user for confirmation
function confirmAction(question) {
  const rl = createCLI();
  
  return new Promise(resolve => {
    rl.question(`${question} (y/n): `, answer => {
      rl.close();
      resolve(answer.trim().toLowerCase() === 'y');
    });
  });
}

// Function to remove a directory or file
function removeItem(itemPath, isDirectory) {
  const fullPath = path.join(config.rootDir, itemPath);
  
  try {
    if (isDirectory) {
      // Remove directory recursively
      fs.rmSync(fullPath, { recursive: true, force: true });
      logger.success(`Directory removed: ${itemPath}`);
    } else {
      // Remove file
      fs.unlinkSync(fullPath);
      logger.success(`File removed: ${itemPath}`);
    }
    
    return true;
  } catch (error) {
    logger.error(`Failed to remove ${itemPath}: ${error.message}`);
    return false;
  }
}

// Main function to execute the cleanup
async function main() {
  logger.header('Consolidation Cleanup Script');
  
  try {
    // Create rollback backup directory
    const rollbackDirPath = path.join(config.rootDir, config.rollbackDir);
    mkdirp(rollbackDirPath);
    logger.info(`Created rollback directory: ${config.rollbackDir}`);
    
    // Check consolidated items
    const pendingRemovals = checkConsolidatedItems();
    
    if (pendingRemovals.length === 0) {
      logger.success('No items need to be removed. Consolidation is complete.');
      return;
    }
    
    // Display summary of what will be removed
    logger.header('Removal Summary');
    
    let hasPendingFiles = false;
    
    pendingRemovals.forEach(item => {
      if (item.type === 'directory') {
        if (item.fileCount > 0) {
          logger.warning(`Directory: ${item.path} (contains ${item.fileCount} files)`);
          hasPendingFiles = true;
        } else {
          logger.info(`Directory: ${item.path} (empty)`);
        }
      } else {
        logger.info(`File: ${item.path}`);
      }
    });
    
    // Display warning about non-empty directories
    if (hasPendingFiles) {
      logger.warning('\nSome directories still contain files that may not have been properly consolidated.');
      logger.warning('Verify that all files have been properly moved and tested before proceeding.');
    }
    
    // Ask for confirmation
    const confirmed = await confirmAction('Do you want to proceed with removal?');
    
    if (!confirmed) {
      logger.info('Operation cancelled by user.');
      return;
    }
    
    // Create backups before removal
    logger.header('Creating Backups');
    
    for (const item of pendingRemovals) {
      const itemPath = path.join(config.rootDir, item.path);
      createBackup(itemPath, config.rollbackDir);
    }
    
    // Remove items
    logger.header('Removing Consolidated Items');
    
    for (const item of pendingRemovals) {
      removeItem(item.path, item.type === 'directory');
    }
    
    // Run lint check to verify everything is working
    logger.header('Verifying Project Integrity');
    
    try {
      logger.info('Running lint check...');
      execSync('npm run lint', { cwd: config.rootDir, stdio: 'inherit' });
      logger.success('Lint check passed');
    } catch (error) {
      logger.warning('Lint check found issues. Review the output to ensure no regressions were introduced.');
    }
    
    // Display rollback instructions
    logger.header('Rollback Instructions');
    
    logger.info(`Backups of all removed items are stored in: ${config.rollbackDir}`);
    logger.info('If you need to restore any items, you can copy them from the backup directory.');
    logger.info('For example:');
    logger.info(`  cp -r ${config.rollbackDir}/frontend .\n`);
    
    logger.success('Consolidation cleanup completed successfully.');
  } catch (error) {
    logger.error(`An error occurred during cleanup: ${error.message}`);
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