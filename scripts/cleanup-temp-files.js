#!/usr/bin/env node

/**
 * Temporary File Cleanup Script
 * 
 * This script cleans up temporary files and maintains a clean directory structure.
 * It removes:
 * - Redis dump files
 * - Build artifacts
 * - Log files older than 7 days
 * - Temporary files and directories
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const config = {
  rootDir: path.resolve(__dirname, '..'),
  // Files to clean up
  tempFilesToClean: [
    'dump.rdb',
    '*.log.old',
    '.DS_Store',
    'Thumbs.db',
    '*.pyc',
    '*.pyo',
    '*.swp',
    '*.swo'
  ],
  // Directories to clean up
  tempDirsToClean: [
    '__pycache__',
    '.pytest_cache',
    '*.egg-info',
    '.coverage'
  ],
  // Log files to rotate (older than 7 days)
  logFilesToRotate: [
    'logs/*.log'
  ],
  // Maximum log file age in days
  maxLogAgeInDays: 7
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

// Function to find and delete temporary files
function cleanupTempFiles() {
  logger.header('Cleaning Up Temporary Files');
  
  try {
    // Find and remove temporary files
    for (const pattern of config.tempFilesToClean) {
      const command = `find ${config.rootDir} -type f -name "${pattern}" -not -path "*/node_modules/*" -not -path "*/.git/*" -print`;
      const files = execSync(command, { encoding: 'utf8' }).trim().split('\n').filter(Boolean);
      
      for (const file of files) {
        try {
          fs.unlinkSync(file);
          logger.success(`Removed file: ${path.relative(config.rootDir, file)}`);
        } catch (error) {
          logger.error(`Failed to remove file ${file}: ${error.message}`);
        }
      }
    }
    
    // Find and remove temporary directories
    for (const pattern of config.tempDirsToClean) {
      const command = `find ${config.rootDir} -type d -name "${pattern}" -not -path "*/node_modules/*" -not -path "*/.git/*" -print`;
      const dirs = execSync(command, { encoding: 'utf8' }).trim().split('\n').filter(Boolean);
      
      for (const dir of dirs) {
        try {
          fs.rmSync(dir, { recursive: true, force: true });
          logger.success(`Removed directory: ${path.relative(config.rootDir, dir)}`);
        } catch (error) {
          logger.error(`Failed to remove directory ${dir}: ${error.message}`);
        }
      }
    }
  } catch (error) {
    logger.error(`Error finding temporary files: ${error.message}`);
  }
}

// Function to rotate log files
function rotateLogFiles() {
  logger.header('Rotating Log Files');
  
  try {
    const now = new Date();
    const maxAgeMs = config.maxLogAgeInDays * 24 * 60 * 60 * 1000; // Convert days to milliseconds
    
    for (const pattern of config.logFilesToRotate) {
      const command = `find ${config.rootDir} -type f -path "${pattern}" -print`;
      const logFiles = execSync(command, { encoding: 'utf8' }).trim().split('\n').filter(Boolean);
      
      for (const logFile of logFiles) {
        try {
          const stats = fs.statSync(logFile);
          const fileAgeMs = now - stats.mtime;
          
          if (fileAgeMs > maxAgeMs) {
            // Rotate log file by appending timestamp to filename
            const timestamp = stats.mtime.toISOString().replace(/:/g, '-').replace(/\..+/, '');
            const rotatedFile = `${logFile}.${timestamp}`;
            
            fs.renameSync(logFile, rotatedFile);
            logger.success(`Rotated log file: ${path.relative(config.rootDir, logFile)} → ${path.basename(rotatedFile)}`);
            
            // Create an empty log file to replace the rotated one
            fs.writeFileSync(logFile, '');
          }
        } catch (error) {
          logger.error(`Failed to rotate log file ${logFile}: ${error.message}`);
        }
      }
    }
  } catch (error) {
    logger.error(`Error rotating log files: ${error.message}`);
  }
}

// Main function to execute the cleanup
function main() {
  logger.header('Temporary File Cleanup Script');
  
  try {
    // Clean up temporary files and directories
    cleanupTempFiles();
    
    // Rotate log files
    rotateLogFiles();
    
    logger.header('Cleanup Complete');
    logger.success('The project directory has been cleaned up');
  } catch (error) {
    logger.error(`Cleanup failed: ${error.message}`);
    process.exit(1);
  }
}

// Run the main function
main(); 