/**
 * Test script for AI model integration.
 * Tests the model routing logic for Vedic Astrological Birth Time Rectification.
 */

import fetch from 'node-fetch';
import { API_ENDPOINTS } from './e2e/constants.js';

// Default API URL
const API_URL = process.env.API_URL || 'http://localhost:8000';

/**
 * Test the OpenAI model routing logic
 * This tests the routing of different tasks to different AI models
 */
async function testModelRouting() {
  console.log('Testing AI model routing logic...');

  // Test different task types
  const tasks = [
    { type: 'rectification', expectedModel: 'o1-preview', prompt: 'Please analyze this birth chart for rectification' },
    { type: 'explanation', expectedModel: 'gpt-4-turbo', prompt: 'Explain this birth time correction' },
    { type: 'confidence', expectedModel: 'gpt-4o-mini', prompt: 'Score the confidence of this birth time prediction' }
  ];

  let allPassed = true;

  for (const task of tasks) {
    try {
      const response = await fetch(`${API_URL}${API_ENDPOINTS.aiModelRouting}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          task_type: task.type,
          prompt: task.prompt
        })
      });

      if (!response.ok) {
        console.error(`❌ Failed to test ${task.type} task routing: HTTP ${response.status}`);
        allPassed = false;
        continue;
      }

      const data = await response.json();

      console.log(`Task type: ${task.type}`);
      console.log(`Expected model: ${task.expectedModel}`);
      console.log(`Actual model used: ${data.model_used}`);
      console.log(`Tokens used: ${data.tokens.total}`);
      console.log(`Cost: $${data.cost}`);
      console.log('---');

      if (data.model_used === task.expectedModel) {
        console.log(`✅ ${task.type} - Correct model selected (${data.model_used})`);
      } else {
        console.error(`❌ ${task.type} - Wrong model selected. Expected: ${task.expectedModel}, Got: ${data.model_used}`);
        allPassed = false;
      }
    } catch (error) {
      console.error(`❌ Error testing ${task.type} task: ${error.message}`);
      allPassed = false;
    }
  }

  return allPassed;
}

/**
 * Test the explanation generation from the UnifiedRectificationModel
 */
async function testExplanationGeneration() {
  console.log('\nTesting birth time explanation generation...');

  try {
    const testData = {
      adjustment_minutes: 15,
      reliability: 'high',
      questionnaire_data: {
        responses: [
          { question: 'Were you born in the morning or evening?', answer: 'Evening' },
          { question: 'Describe a significant life event', answer: 'Career change at 30' },
          { question: 'Do you feel your birth time is accurate?', answer: 'Somewhat uncertain' }
        ]
      }
    };

    const response = await fetch(`${API_URL}${API_ENDPOINTS.aiTest}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(testData)
    });

    if (!response.ok) {
      console.error(`❌ Failed to test explanation generation: HTTP ${response.status}`);
      return false;
    }

    const data = await response.json();

    console.log('Generated explanation:');
    console.log(data.explanation);
    console.log('\nUsage statistics:');
    console.log(`Total API calls: ${data.usage_statistics.calls_made}`);
    console.log(`Total tokens used: ${data.usage_statistics.total_tokens}`);
    console.log(`Estimated cost: $${data.usage_statistics.estimated_cost}`);

    return true;
  } catch (error) {
    console.error(`❌ Error testing explanation generation: ${error.message}`);
    return false;
  }
}

/**
 * Run all tests
 */
async function runTests() {
  console.log('=== Starting AI Model Integration Tests ===\n');

  const modelRoutingResult = await testModelRouting();
  const explanationResult = await testExplanationGeneration();

  console.log('\n=== Test Results ===');
  console.log(`Model Routing: ${modelRoutingResult ? '✅ PASSED' : '❌ FAILED'}`);
  console.log(`Explanation Generation: ${explanationResult ? '✅ PASSED' : '❌ FAILED'}`);
  console.log(`Overall: ${modelRoutingResult && explanationResult ? '✅ PASSED' : '❌ FAILED'}`);

  // Exit with appropriate code for CI/CD integration
  process.exit(modelRoutingResult && explanationResult ? 0 : 1);
}

// Run tests
runTests().catch(error => {
  console.error('Unhandled error in tests:', error);
  process.exit(1);
});
