#!/usr/bin/env node

/**
 * Perplexity Services Autostart
 * 
 * This script ensures that the Perplexity API bridge is running.
 * It's designed to be added to IDE startup or run from user's profile.
 */

const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Get the directory where this script is located
const scriptDir = __dirname;

// Path to the PID file
const pidFile = path.join(scriptDir, 'perplexity-bridge.pid');
const logFile = path.join(scriptDir, 'perplexity-autostart.log');

// Append to log with timestamp
function log(message) {
  const timestamp = new Date().toISOString();
  fs.appendFileSync(logFile, `[${timestamp}] ${message}\n`);
}

// Check if the service is already running
function isServiceRunning() {
  try {
    if (fs.existsSync(pidFile)) {
      const pid = fs.readFileSync(pidFile, 'utf8').trim();
      
      // Try to get process info - if it throws, the process doesn't exist
      try {
        if (process.platform === 'win32') {
          // Windows command to check if process exists
          execSync(`tasklist /FI "PID eq ${pid}" /NH`);
        } else {
          // Unix command to check if process exists
          execSync(`ps -p ${pid} -o pid=`);
        }
        
        // Also verify it's actually our process
        const cmdline = process.platform === 'win32' 
          ? execSync(`wmic process where processid=${pid} get commandline`).toString()
          : execSync(`ps -p ${pid} -o command=`).toString();
          
        if (cmdline.includes('direct-perplexity-bridge.js')) {
          log(`Service already running with PID ${pid}`);
          return true;
        }
      } catch (e) {
        // Process not found
        log(`PID ${pid} not found, removing stale PID file`);
        fs.unlinkSync(pidFile);
      }
    }
    
    return false;
  } catch (error) {
    log(`Error checking service status: ${error.message}`);
    return false;
  }
}

// Start the service
function startService() {
  try {
    log('Starting Perplexity API bridge...');
    
    // Check if direct-perplexity-bridge.js exists
    const bridgePath = path.join(scriptDir, 'direct-perplexity-bridge.js');
    if (!fs.existsSync(bridgePath)) {
      log(`ERROR: Bridge script not found at ${bridgePath}`);
      return false;
    }
    
    // Run the service
    const logStream = fs.createWriteStream(path.join(scriptDir, 'perplexity-bridge.log'), { flags: 'a' });
    
    const child = spawn('node', [bridgePath], {
      detached: true,
      stdio: ['ignore', logStream, logStream]
    });
    
    // Write PID to file
    fs.writeFileSync(pidFile, child.pid.toString());
    log(`Service started with PID ${child.pid}`);
    
    // Update Cursor MCP configuration
    const setupScript = path.join(scriptDir, 'cursor-mcp-setup.js');
    if (fs.existsSync(setupScript)) {
      log('Updating Cursor MCP configuration...');
      execSync(`node ${setupScript}`, { stdio: 'ignore' });
      log('Cursor MCP configuration updated');
    } else {
      log(`WARNING: Setup script not found at ${setupScript}`);
    }
    
    // Unref the child to let the parent exit
    child.unref();
    return true;
  } catch (error) {
    log(`Error starting service: ${error.message}`);
    return false;
  }
}

// Main function
function main() {
  log('=== Perplexity Autostart ===');
  
  // Check if service is already running
  if (!isServiceRunning()) {
    // If not, start it
    if (startService()) {
      log('Perplexity service started successfully');
    } else {
      log('Failed to start Perplexity service');
    }
  }
  
  log('Autostart check completed');
}

// Run the main function
main(); 