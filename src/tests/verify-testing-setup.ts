import * as fs from 'fs';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * This script verifies that our testing setup is ready for the stakeholder presentation
 * by checking all necessary files and dependencies.
 */

interface CheckResult {
  name: string;
  success: boolean;
  message: string;
  details?: string;
}

// Define checks to run
const checks = [
  checkTestCategories,
  checkTestPages,
  checkPlaywrightConfig,
  checkDependencies,
  checkDemoContent,
  checkDocumentation
];

async function main() {
  console.log('\n🔍 Verifying testing setup for stakeholder presentation...\n');

  const results: CheckResult[] = [];

  // Run all checks
  for (const check of checks) {
    try {
      const result = await check();
      results.push(result);

      // Log the result
      if (result.success) {
        console.log(`✅ ${result.name}: ${result.message}`);
      } else {
        console.log(`❌ ${result.name}: ${result.message}`);
        if (result.details) {
          console.log(`   ${result.details}`);
        }
      }
    } catch (error) {
      console.error(`Error running ${check.name}:`, error);
      results.push({
        name: check.name,
        success: false,
        message: 'Check failed with an error',
        details: String(error)
      });
    }
  }

  // Print summary
  const successCount = results.filter(r => r.success).length;
  console.log('\n📋 Verification Summary:');
  console.log(`Total Checks: ${results.length}`);
  console.log(`Passed: ${successCount}`);
  console.log(`Failed: ${results.length - successCount}`);

  if (successCount === results.length) {
    console.log('\n🎉 All checks passed! Setup is ready for stakeholder presentation.');
  } else {
    console.log('\n⚠️ Some checks failed. Please address the issues before the presentation.');
  }
}

// Check that all test categories have test files
async function checkTestCategories(): Promise<CheckResult> {
  const categories = [
    'visual-regression',
    'performance',
    'compatibility',
    'interaction',
    'visual-quality'
  ];

  const missingCategories: string[] = [];

  for (const category of categories) {
    const categoryPath = path.join(process.cwd(), 'src', 'tests', category);
    if (!fs.existsSync(categoryPath)) {
      missingCategories.push(category);
      continue;
    }

    const files = fs.readdirSync(categoryPath);
    if (files.length === 0) {
      missingCategories.push(`${category} (empty directory)`);
    }
  }

  if (missingCategories.length === 0) {
    return {
      name: 'Test Categories',
      success: true,
      message: 'All test categories have test files'
    };
  } else {
    return {
      name: 'Test Categories',
      success: false,
      message: 'Some test categories are missing or empty',
      details: `Missing: ${missingCategories.join(', ')}`
    };
  }
}

// Check that test pages exist
async function checkTestPages(): Promise<CheckResult> {
  const testPages = [
    'celestial-canvas.tsx',
    'sun-component.tsx',
    'planet-component.tsx',
    'nebula-component.tsx',
    'enhanced-space-scene.tsx',
    'planet-system.tsx',
    'shooting-stars.tsx',
    // Add any other test pages here
  ];

  const missingPages: string[] = [];

  for (const page of testPages) {
    const pagePath = path.join(process.cwd(), 'src', 'pages', 'test-pages', page);
    if (!fs.existsSync(pagePath)) {
      missingPages.push(page);
    }
  }

  if (missingPages.length === 0) {
    return {
      name: 'Test Pages',
      success: true,
      message: 'All test pages exist'
    };
  } else {
    return {
      name: 'Test Pages',
      success: false,
      message: 'Some test pages are missing',
      details: `Missing: ${missingPages.join(', ')}`
    };
  }
}

// Check that Playwright config exists
async function checkPlaywrightConfig(): Promise<CheckResult> {
  const configPath = path.join(process.cwd(), 'playwright.config.ts');

  if (fs.existsSync(configPath)) {
    return {
      name: 'Playwright Config',
      success: true,
      message: 'Playwright config exists'
    };
  } else {
    return {
      name: 'Playwright Config',
      success: false,
      message: 'Playwright config is missing',
      details: 'Create playwright.config.ts in the project root'
    };
  }
}

// Check that all dependencies are installed
async function checkDependencies(): Promise<CheckResult> {
  try {
    const { stdout } = await execAsync('npm list --depth=0');

    const requiredDeps = [
      '@playwright/test',
      '@percy/playwright',
      'pixelmatch',
      'canvas',
      'ts-node'
    ];

    const missingDeps: string[] = [];

    for (const dep of requiredDeps) {
      if (!stdout.includes(dep)) {
        missingDeps.push(dep);
      }
    }

    if (missingDeps.length === 0) {
      return {
        name: 'Dependencies',
        success: true,
        message: 'All required dependencies are installed'
      };
    } else {
      return {
        name: 'Dependencies',
        success: false,
        message: 'Some dependencies are missing',
        details: `Missing: ${missingDeps.join(', ')}. Run npm install to fix.`
      };
    }
  } catch (error) {
    return {
      name: 'Dependencies',
      success: false,
      message: 'Failed to check dependencies',
      details: String(error)
    };
  }
}

// Check that demo content exists or can be generated
async function checkDemoContent(): Promise<CheckResult> {
  const demoScriptPath = path.join(process.cwd(), 'src', 'tests', 'create-demo-content.ts');
  const reportPath = path.join(process.cwd(), 'test-results', 'stakeholder-report.html');

  if (fs.existsSync(demoScriptPath)) {
    if (fs.existsSync(reportPath)) {
      return {
        name: 'Demo Content',
        success: true,
        message: 'Demo content script and report exist'
      };
    } else {
      return {
        name: 'Demo Content',
        success: true,
        message: 'Demo content script exists but report needs to be generated',
        details: 'Run "npm run test:create-demo" to generate the report'
      };
    }
  } else {
    return {
      name: 'Demo Content',
      success: false,
      message: 'Demo content script is missing',
      details: 'Create src/tests/create-demo-content.ts'
    };
  }
}

// Check that documentation exists
async function checkDocumentation(): Promise<CheckResult> {
  const docsPath = path.join(process.cwd(), 'docs', 'testing-strategy.md');

  if (fs.existsSync(docsPath)) {
    return {
      name: 'Documentation',
      success: true,
      message: 'Testing strategy documentation exists'
    };
  } else {
    return {
      name: 'Documentation',
      success: false,
      message: 'Testing strategy documentation is missing',
      details: 'Create docs/testing-strategy.md'
    };
  }
}

// Run the script
main().catch(error => {
  console.error('Error verifying testing setup:', error);
  process.exit(1);
});
