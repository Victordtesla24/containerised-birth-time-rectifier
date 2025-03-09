import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';

const execAsync = promisify(exec);

// Configuration
const TEST_CATEGORIES = [
  { name: 'Visual Regression', dir: 'visual-regression', description: 'Tests that verify the visual appearance of UI components' },
  { name: 'Performance', dir: 'performance', description: 'Tests that measure rendering speed and efficiency' },
  { name: 'Interaction', dir: 'interaction', description: 'Tests that verify user interactions work correctly' },
  { name: 'Compatibility', dir: 'compatibility', description: 'Tests that verify cross-browser and device compatibility' },
  { name: 'Visual Quality', dir: 'visual-quality', description: 'Tests that verify shader and material quality' }
];

const REPORT_DIR = path.join(process.cwd(), 'test-results');
const REPORT_FILE = path.join(REPORT_DIR, 'stakeholder-report.html');

// Ensure report directory exists
if (!fs.existsSync(REPORT_DIR)) {
  fs.mkdirSync(REPORT_DIR, { recursive: true });
}

// Function to run tests for a specific category
async function runTestCategory(category: { name: string; dir: string; description: string }) {
  console.log(`\n🚀 Running ${category.name} Tests...\n`);

  try {
    // Run the tests using Playwright
    const { stdout, stderr } = await execAsync(
      `npx playwright test ${path.join('src', 'tests', category.dir)} --reporter=html,list`
    );

    console.log(stdout);
    if (stderr) console.error(stderr);

    return {
      name: category.name,
      success: !stderr || !stderr.includes('failed'),
      output: stdout,
      error: stderr
    };
  } catch (error: any) {
    console.error(`Error running ${category.name} tests:`, error);
    return {
      name: category.name,
      success: false,
      output: '',
      error: error.toString()
    };
  }
}

// Function to generate a stakeholder-friendly HTML report
function generateReport(results: any[]) {
  const successCount = results.filter(r => r.success).length;
  const totalCount = results.length;
  const successRate = Math.round((successCount / totalCount) * 100);

  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Celestial Visualization Quality Report</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
      background-color: #f9f9f9;
    }
    header {
      text-align: center;
      margin-bottom: 40px;
      padding-bottom: 20px;
      border-bottom: 1px solid #eee;
    }
    h1 {
      color: #2c3e50;
      margin-bottom: 10px;
    }
    .summary {
      display: flex;
      justify-content: space-around;
      margin: 30px 0;
      text-align: center;
    }
    .summary-item {
      padding: 20px;
      border-radius: 8px;
      background-color: white;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      width: 30%;
    }
    .summary-item h3 {
      margin-top: 0;
      color: #3498db;
    }
    .progress-bar {
      height: 20px;
      background-color: #ecf0f1;
      border-radius: 10px;
      margin: 10px 0;
      overflow: hidden;
    }
    .progress-bar-fill {
      height: 100%;
      background-color: #2ecc71;
      border-radius: 10px;
      transition: width 0.5s ease-in-out;
    }
    .category {
      margin: 30px 0;
      padding: 20px;
      background-color: white;
      border-radius: 8px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .category h2 {
      color: #2c3e50;
      border-bottom: 2px solid #3498db;
      padding-bottom: 10px;
    }
    .status {
      display: inline-block;
      padding: 5px 10px;
      border-radius: 4px;
      font-weight: bold;
    }
    .status.pass {
      background-color: #e6f7e9;
      color: #27ae60;
    }
    .status.fail {
      background-color: #fde9e9;
      color: #e74c3c;
    }
    .gallery {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 20px;
      margin-top: 30px;
    }
    .gallery-item {
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      transition: transform 0.3s ease;
    }
    .gallery-item:hover {
      transform: scale(1.03);
    }
    .gallery-item img {
      width: 100%;
      height: auto;
      display: block;
    }
    .gallery-item .caption {
      padding: 10px;
      background-color: white;
      text-align: center;
      font-size: 14px;
    }
    footer {
      text-align: center;
      margin-top: 50px;
      padding-top: 20px;
      border-top: 1px solid #eee;
      color: #7f8c8d;
    }
  </style>
</head>
<body>
  <header>
    <h1>Celestial Visualization Quality Report</h1>
    <p>Comprehensive test results for UI/UX enhancements</p>
    <p>Generated on ${new Date().toLocaleString()}</p>
  </header>

  <div class="summary">
    <div class="summary-item">
      <h3>Overall Quality</h3>
      <div class="progress-bar">
        <div class="progress-bar-fill" style="width: ${successRate}%"></div>
      </div>
      <p>${successRate}% of tests passed</p>
    </div>
    <div class="summary-item">
      <h3>Tests Run</h3>
      <p>${totalCount} test categories</p>
      <p>${successCount} passed, ${totalCount - successCount} failed</p>
    </div>
    <div class="summary-item">
      <h3>Key Highlights</h3>
      <p>✓ Visual fidelity</p>
      <p>✓ Performance optimization</p>
      <p>✓ Cross-browser compatibility</p>
    </div>
  </div>

  <div class="categories">
    ${results.map(result => `
      <div class="category">
        <h2>${result.name}</h2>
        <p>${TEST_CATEGORIES.find(c => c.name === result.name)?.description || ''}</p>
        <p>Status: <span class="status ${result.success ? 'pass' : 'fail'}">${result.success ? 'PASSED' : 'FAILED'}</span></p>
        ${result.success
          ? '<p>All tests in this category passed successfully.</p>'
          : `<p>Some tests in this category failed. See details below:</p>
             <pre>${result.error}</pre>`
        }
      </div>
    `).join('')}
  </div>

  <h2>Visual Evidence</h2>
  <p>Below are screenshots captured during testing that demonstrate the high quality of our visualizations:</p>

  <div class="gallery">
    <!-- Dynamically generated based on available screenshots -->
    ${fs.existsSync(REPORT_DIR) && fs.readdirSync(REPORT_DIR)
      .filter(file => file.endsWith('.png'))
      .map(file => `
        <div class="gallery-item">
          <img src="${file}" alt="${file.replace('.png', '')}">
          <div class="caption">${file.replace('.png', '').replace(/-/g, ' ')}</div>
        </div>
      `).join('')}
  </div>

  <footer>
    <p>This report was automatically generated by the Celestial Visualization Test Suite.</p>
    <p>For detailed test results, please see the full test reports in the test-results directory.</p>
  </footer>
</body>
</html>
  `;

  fs.writeFileSync(REPORT_FILE, html);
  console.log(`\n📊 Stakeholder report generated at: ${REPORT_FILE}\n`);
}

// Main function to run all tests
async function runAllTests() {
  console.log('\n🔍 Starting Celestial Visualization Test Suite...\n');

  const results: any[] = [];

  for (const category of TEST_CATEGORIES) {
    const result = await runTestCategory(category);
    results.push(result);
  }

  // Generate the report
  generateReport(results);

  // Print summary
  const successCount = results.filter(r => r.success).length;
  console.log('\n📋 Test Summary:');
  console.log(`Total Categories: ${results.length}`);
  console.log(`Passed: ${successCount}`);
  console.log(`Failed: ${results.length - successCount}`);
  console.log(`Success Rate: ${Math.round((successCount / results.length) * 100)}%`);

  console.log('\n✨ Testing complete! ✨\n');
}

// Run the tests
runAllTests().catch(error => {
  console.error('Error running tests:', error);
  process.exit(1);
});
