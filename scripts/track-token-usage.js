/**
 * Token Usage Tracking Script for Cline Extension
 *
 * This script monitors and reports token usage across different models
 * to help optimize costs when using the Cline extension.
 *
 * Usage:
 * - Run manually: node scripts/track-token-usage.js
 * - Add to CI/CD: Include in GitHub Actions workflow
 */

const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
  logFile: path.join(__dirname, '../logs/token-usage.log'),
  thresholds: {
    daily: 100000,
    warning: 0.8, // 80% of daily limit
    critical: 0.95 // 95% of daily limit
  },
  models: {
    'deepseek-coder-v2': { costPer100kTokens: 0.20 },
    'claude-3-haiku': { costPer100kTokens: 0.25 },
    'claude-3.5-sonnet': { costPer100kTokens: 3.00 },
    'qwen-2.5-coder': { costPer100kTokens: 0.15 },
    'gemini-2.0-flash': { costPer100kTokens: 0.00 } // Free with limits
  }
};

// Ensure logs directory exists
const logsDir = path.dirname(CONFIG.logFile);
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

// Initialize or read existing log file
function initializeOrReadLog() {
  if (!fs.existsSync(CONFIG.logFile)) {
    const initialData = {
      dailyUsage: 0,
      totalUsage: 0,
      lastReset: new Date().toISOString(),
      modelUsage: {},
      history: []
    };
    fs.writeFileSync(CONFIG.logFile, JSON.stringify(initialData, null, 2));
    return initialData;
  }

  try {
    const data = JSON.parse(fs.readFileSync(CONFIG.logFile, 'utf8'));

    // Check if we need to reset daily usage (new day)
    const lastReset = new Date(data.lastReset);
    const now = new Date();
    if (lastReset.toDateString() !== now.toDateString()) {
      // Archive yesterday's usage
      data.history.push({
        date: lastReset.toISOString(),
        usage: data.dailyUsage,
        modelBreakdown: { ...data.modelUsage }
      });

      // Reset daily counters
      data.dailyUsage = 0;
      data.lastReset = now.toISOString();
      data.modelUsage = {};

      // Keep only last 30 days of history
      if (data.history.length > 30) {
        data.history = data.history.slice(-30);
      }

      fs.writeFileSync(CONFIG.logFile, JSON.stringify(data, null, 2));
    }

    return data;
  } catch (error) {
    console.error('Error reading token usage log:', error);
    return {
      dailyUsage: 0,
      totalUsage: 0,
      lastReset: new Date().toISOString(),
      modelUsage: {},
      history: []
    };
  }
}

// Track token usage
function trackTokenUsage(model, promptTokens, responseTokens) {
  const data = initializeOrReadLog();
  const total = promptTokens + responseTokens;

  // Update totals
  data.dailyUsage += total;
  data.totalUsage += total;

  // Update model-specific usage
  if (!data.modelUsage[model]) {
    data.modelUsage[model] = {
      promptTokens: 0,
      responseTokens: 0,
      totalTokens: 0
    };
  }

  data.modelUsage[model].promptTokens += promptTokens;
  data.modelUsage[model].responseTokens += responseTokens;
  data.modelUsage[model].totalTokens += total;

  // Save updated data
  fs.writeFileSync(CONFIG.logFile, JSON.stringify(data, null, 2));

  // Check thresholds and return status
  const dailyPercentage = data.dailyUsage / CONFIG.thresholds.daily;

  if (dailyPercentage >= CONFIG.thresholds.critical) {
    return { status: 'CRITICAL', percentage: dailyPercentage };
  } else if (dailyPercentage >= CONFIG.thresholds.warning) {
    return { status: 'WARNING', percentage: dailyPercentage };
  }

  return { status: 'OK', percentage: dailyPercentage };
}

// Generate cost report
function generateCostReport() {
  const data = initializeOrReadLog();
  const report = {
    dailyUsage: data.dailyUsage,
    dailyPercentage: (data.dailyUsage / CONFIG.thresholds.daily * 100).toFixed(1) + '%',
    totalUsage: data.totalUsage,
    modelBreakdown: {},
    estimatedCosts: {
      daily: 0,
      total: 0
    }
  };

  // Calculate costs per model
  Object.entries(data.modelUsage).forEach(([model, usage]) => {
    const modelConfig = CONFIG.models[model] || { costPer100kTokens: 1.00 }; // Default if unknown
    const cost = (usage.totalTokens / 100000) * modelConfig.costPer100kTokens;

    report.modelBreakdown[model] = {
      tokens: usage.totalTokens,
      promptTokens: usage.promptTokens,
      responseTokens: usage.responseTokens,
      estimatedCost: cost.toFixed(2)
    };

    report.estimatedCosts.daily += cost;
  });

  // Calculate total historical cost
  data.history.forEach(day => {
    let dayCost = 0;
    Object.entries(day.modelBreakdown || {}).forEach(([model, usage]) => {
      const modelConfig = CONFIG.models[model] || { costPer100kTokens: 1.00 };
      dayCost += (usage.totalTokens / 100000) * modelConfig.costPer100kTokens;
    });
    report.estimatedCosts.total += dayCost;
  });

  // Add current day's cost to total
  report.estimatedCosts.total += report.estimatedCosts.daily;

  // Format costs as currency
  report.estimatedCosts.daily = '$' + report.estimatedCosts.daily.toFixed(2);
  report.estimatedCosts.total = '$' + report.estimatedCosts.total.toFixed(2);

  return report;
}

// Generate optimization recommendations
function generateOptimizationRecommendations() {
  const data = initializeOrReadLog();
  const recommendations = [];

  // Check for expensive model overuse
  const expensiveModelThreshold = 0.3; // 30% of total usage
  Object.entries(data.modelUsage).forEach(([model, usage]) => {
    if (model === 'claude-3.5-sonnet' && usage.totalTokens > data.dailyUsage * expensiveModelThreshold) {
      recommendations.push({
        priority: 'HIGH',
        issue: 'High usage of expensive model (Claude 3.5 Sonnet)',
        recommendation: 'Consider switching to DeepSeek-Coder-V2 for routine tasks',
        potentialSavings: 'Up to 93% cost reduction per token'
      });
    }
  });

  // Check for high prompt-to-response ratio
  Object.entries(data.modelUsage).forEach(([model, usage]) => {
    if (usage.promptTokens > usage.responseTokens * 1.5) {
      recommendations.push({
        priority: 'MEDIUM',
        issue: 'High prompt-to-response ratio for ' + model,
        recommendation: 'Optimize prompts by removing unnecessary context and using abbreviations',
        potentialSavings: 'Up to 30% reduction in prompt tokens'
      });
    }
  });

  // Check overall usage
  if (data.dailyUsage > CONFIG.thresholds.daily * 0.7) {
    recommendations.push({
      priority: 'HIGH',
      issue: 'Approaching daily token limit',
      recommendation: 'Implement token caching and template-based prompts',
      potentialSavings: 'Up to 40% reduction in total token usage'
    });
  }

  return recommendations;
}

// Main function
function main() {
  // For testing/demo purposes, simulate some token usage
  // In production, this would be called by your application
  trackTokenUsage('deepseek-coder-v2', 500, 1500);
  trackTokenUsage('claude-3.5-sonnet', 1000, 3000);

  // Generate and display reports
  const costReport = generateCostReport();
  const recommendations = generateOptimizationRecommendations();

  console.log('\n===== TOKEN USAGE REPORT =====');
  console.log(`Daily Usage: ${costReport.dailyUsage} tokens (${costReport.dailyPercentage} of limit)`);
  console.log(`Estimated Daily Cost: ${costReport.estimatedCosts.daily}`);
  console.log(`Total Historical Cost: ${costReport.estimatedCosts.total}`);

  console.log('\n----- Model Breakdown -----');
  Object.entries(costReport.modelBreakdown).forEach(([model, data]) => {
    console.log(`${model}: ${data.tokens} tokens ($${data.estimatedCost})`);
  });

  console.log('\n===== OPTIMIZATION RECOMMENDATIONS =====');
  if (recommendations.length === 0) {
    console.log('No optimization recommendations at this time.');
  } else {
    recommendations.forEach((rec, index) => {
      console.log(`\n[${rec.priority}] Recommendation #${index + 1}:`);
      console.log(`Issue: ${rec.issue}`);
      console.log(`Recommendation: ${rec.recommendation}`);
      console.log(`Potential Savings: ${rec.potentialSavings}`);
    });
  }

  // Set exit code for CI/CD integration
  const data = initializeOrReadLog();
  const dailyPercentage = data.dailyUsage / CONFIG.thresholds.daily;

  if (dailyPercentage >= CONFIG.thresholds.critical) {
    console.error('\n⚠️ CRITICAL: Token usage exceeding critical threshold!');
    process.exitCode = 1;
  } else if (dailyPercentage >= CONFIG.thresholds.warning) {
    console.warn('\n⚠️ WARNING: Token usage approaching daily limit!');
    process.exitCode = 0; // Warning but don't fail CI
  }
}

// Run the main function
main();
