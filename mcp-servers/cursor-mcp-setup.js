#!/usr/bin/env node

/**
 * Perplexity MCP Setup for Cursor
 * 
 * This script configures Cursor to use the Perplexity API bridge with the correct MCP configuration
 * by updating the .cursor/rules/mcp.json file.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Determine home directory
const homeDir = process.env.HOME || process.env.USERPROFILE;
const cursorDir = path.join(homeDir, '.cursor');
const rulesDir = path.join(cursorDir, 'rules');

// MCP configuration focused only on Perplexity
const mcpConfig = {
  mcpServers: {
    "github.com/pashpashpash/perplexity-mcp": {
      "command": "node",
      "args": [
        path.join(__dirname, "direct-perplexity-bridge.js")
      ],
      "env": {
        "PERPLEXITY_API_KEY": "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"
      },
      "disabled": false,
      "autoApprove": [
        "get_documentation",
        "find_apis",
        "check_deprecated_code",
        "chat_perplexity",
        "search"
      ],
      "transport": "http",
      "url": "http://localhost:3336"
    }
  }
};

// Colorful console output
const colors = {
  reset: "\x1b[0m",
  bright: "\x1b[1m",
  dim: "\x1b[2m",
  underscore: "\x1b[4m",
  blink: "\x1b[5m",
  reverse: "\x1b[7m",
  hidden: "\x1b[8m",
  
  black: "\x1b[30m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  magenta: "\x1b[35m",
  cyan: "\x1b[36m",
  white: "\x1b[37m",
};

// Create required directories
function ensureDirectories() {
  if (!fs.existsSync(cursorDir)) {
    console.log(`Creating Cursor directory at: ${cursorDir}`);
    fs.mkdirSync(cursorDir, { recursive: true });
  }
  
  if (!fs.existsSync(rulesDir)) {
    console.log(`Creating Cursor rules directory at: ${rulesDir}`);
    fs.mkdirSync(rulesDir, { recursive: true });
  }
  
  return true;
}

// Write MCP configuration to file
function writeMcpConfig() {
  const mcpConfigPath = path.join(rulesDir, 'mcp.json');
  
  try {
    // Backup existing configuration if any
    if (fs.existsSync(mcpConfigPath)) {
      const backupPath = `${mcpConfigPath}.bak.${Date.now()}`;
      console.log(`Backing up existing MCP configuration...`);
      fs.copyFileSync(mcpConfigPath, backupPath);
      console.log(`Backup saved to: ${backupPath}`);
    }
    
    // Write new configuration
    console.log(`Writing MCP configuration to: ${mcpConfigPath}`);
    fs.writeFileSync(mcpConfigPath, JSON.stringify(mcpConfig, null, 2));
    console.log(`MCP configuration updated successfully!`);
    return true;
  } catch (error) {
    console.error('Error writing MCP configuration:', error);
    return false;
  }
}

// Ensure Perplexity MCP is set up
function setupPerplexityMcp() {
  const perplexityDir = path.join(__dirname, 'repos/perplexity-mcp');
  
  if (!fs.existsSync(perplexityDir)) {
    console.log('Setting up Perplexity MCP...');
    
    try {
      // Create repos directory if it doesn't exist
      if (!fs.existsSync(path.join(__dirname, 'repos'))) {
        fs.mkdirSync(path.join(__dirname, 'repos'), { recursive: true });
      }
      
      // Clone repository
      console.log('Cloning Perplexity MCP repository...');
      execSync('git clone https://github.com/pashpashpash/perplexity-mcp.git', {
        cwd: path.join(__dirname, 'repos'),
        stdio: 'inherit'
      });
      
      // Install dependencies and build
      console.log('Installing dependencies and building Perplexity MCP...');
      execSync('npm install && npm run build', {
        cwd: perplexityDir,
        stdio: 'inherit'
      });
      
      console.log('Perplexity MCP set up successfully!');
    } catch (error) {
      console.error('Error setting up Perplexity MCP:', error);
      return false;
    }
  } else {
    console.log('Perplexity MCP already set up.');
  }
  
  return true;
}

// Main function
function main() {
  console.log(`${colors.blue}=== Cursor MCP Setup ===${colors.reset}`);
  
  // Set up Perplexity MCP
  setupPerplexityMcp();
  
  // Ensure directories exist
  if (!ensureDirectories()) {
    console.error('Failed to create required directories');
    process.exit(1);
  }
  
  // Write MCP configuration
  if (!writeMcpConfig()) {
    console.error('Failed to write MCP configuration');
    process.exit(1);
  }
  
  // Print success message
  console.log(`\n${colors.green}╔════════════════════════════════════════════════════════╗${colors.reset}`);
  console.log(`${colors.green}║                MCP SETUP SUCCESSFUL                    ║${colors.reset}`);
  console.log(`${colors.green}╚════════════════════════════════════════════════════════╝${colors.reset}\n`);
  
  console.log(`Perplexity MCP configuration has been updated successfully.`);
  console.log(`\nTo use Perplexity in Cursor chat:`);
  console.log(`1. Restart Cursor to load the new configuration`);
  console.log(`2. Use the following commands in chat:`);
  console.log(`   - @search [query]`);
  console.log(`   - @documentation [topic]`);
  console.log(`   - @apis [requirement]`);
  console.log(`   - @code-analysis [code]`);
  console.log(`   - @perplexity [message]`);
  
  console.log(`\nFor more information, see the CURSOR-INTEGRATION.md file.`);
}

// Run the main function
main();