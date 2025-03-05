/**
 * Questionnaire and Birth Time Rectification Tests
 *
 * This script tests:
 * 1. Questionnaire (UI/UX page)
 * 2. AI Analysis (Backend processing)
 * 3. Chart Visualization with Rectified Birth Time (UI/UX page)
 * 4. Results (UI/UX page)
 */

import { test, expect } from '@playwright/test';
import { API_ENDPOINTS, TEST_DATA } from './constants';

test.describe('Questionnaire and Rectification Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the questionnaire directly to start the test
    // In a real flow, this would follow chart generation
    await page.goto('/birth-time-rectifier/questionnaire');
    console.log('Navigating to questionnaire page');

    // If redirected to the start, we need to fill the birth details form first
    if (await page.url().includes('/birth-time-rectifier') && !await page.url().includes('questionnaire')) {
      console.log('Redirected to form page, filling birth details first');

      // Fill birth details form
      const dateInput = await page.$('input[type="date"], [data-testid="birth-date"]') ||
                        await page.$('input[name="birthDate"], input[name="date"]');
      const timeInput = await page.$('input[type="time"], [data-testid="birth-time"]') ||
                        await page.$('input[name="birthTime"], input[name="time"]');
      const locationInput = await page.$('input[placeholder*="location"], [data-testid="birth-location"]') ||
                            await page.$('input[name="location"], input[name="birthPlace"]');

      if (dateInput) await dateInput.fill(TEST_DATA.STANDARD.birthDate);
      if (timeInput) await timeInput.fill(TEST_DATA.STANDARD.birthTime);
      if (locationInput) await locationInput.fill(TEST_DATA.STANDARD.birthPlace);

      // If location fields aren't present, try direct coordinate entry
      if (!locationInput) {
        const latInput = await page.$('input[name="latitude"]');
        const longInput = await page.$('input[name="longitude"]');

        if (latInput && longInput) {
          await latInput.fill(String(TEST_DATA.STANDARD.latitude));
          await longInput.fill(String(TEST_DATA.STANDARD.longitude));
        }
      }

      // Submit form
      const submitButton = await page.$('button[type="submit"]') ||
                          await page.$('button:has-text("Generate"), button:has-text("Submit")');
      if (submitButton) await submitButton.click();

      // Wait for chart generation and click continue to questionnaire
      await page.waitForSelector('.chart-container, [data-testid="chart-container"], svg, canvas', {
        state: 'visible',
        timeout: 15000
      });

      const continueButton = page.getByRole('button', { name: /continue|next|questionnaire/i });
      if (await continueButton.count() > 0) {
        await continueButton.click();
      }
    }

    // Verify we're on the questionnaire page
    await page.waitForSelector('.questionnaire, [data-testid="questionnaire"]', {
      state: 'visible',
      timeout: 10000
    }).catch(e => {
      console.log('Error finding questionnaire container:', e.message);
      throw e;
    });

    console.log('Questionnaire page loaded');
  });

  test('should complete questionnaire and view rectified birth time', async ({ page }) => {
    // Take a screenshot at the start of the questionnaire
    await page.screenshot({ path: 'questionnaire-start.png' });

    // Answer questions in the questionnaire
    console.log('Starting to answer questionnaire');

    // Find and answer first question
    const firstQuestion = await page.waitForSelector('.question, [data-testid*="question"]', { timeout: 5000 });
    console.log('Found first question');

    // Determine the question type
    let questionCount = 0;
    let answeredQuestions = 0;

    // Try to answer up to 5 questions or until we reach the end
    while (questionCount < 5) {
      questionCount++;

      // Check if we need to answer more questions or if we're at the results
      const isResultsPage = await page.locator('.results, [data-testid="results"]').count() > 0;
      if (isResultsPage) {
        console.log('Reached results page after answering questions');
        break;
      }

      // Look for question container
      const questionExists = await page.locator('.question, [data-testid*="question"]').count() > 0;
      if (!questionExists) {
        console.log('No more questions found');
        break;
      }

      console.log(`Answering question ${questionCount}`);

      // Try different question formats
      // Multiple choice (radio buttons)
      const radioOptions = await page.locator('input[type="radio"]').count();
      if (radioOptions > 0) {
        console.log(`Found ${radioOptions} radio options`);
        // Select the first option
        await page.locator('input[type="radio"]').first().click();
        answeredQuestions++;
      }

      // Checkbox options
      else {
        const checkboxOptions = await page.locator('input[type="checkbox"]').count();
        if (checkboxOptions > 0) {
          console.log(`Found ${checkboxOptions} checkbox options`);
          // Select the first checkbox
          await page.locator('input[type="checkbox"]').first().click();
          answeredQuestions++;
        }
      }

      // If no question formats were found, this might be a text input
      if (answeredQuestions === questionCount - 1) {
        const textInputs = await page.locator('input[type="text"], textarea').count();
        if (textInputs > 0) {
          console.log(`Found ${textInputs} text inputs`);
          await page.locator('input[type="text"], textarea').first().fill('Test response');
          answeredQuestions++;
        }
      }

      // Click next/continue/submit button
      const nextButton = page.getByRole('button', {
        name: /next|continue|submit/i
      });

      if (await nextButton.count() > 0) {
        await nextButton.click();
        console.log('Clicked next button');

        // Wait for next question or results page
        await page.waitForTimeout(1000);
      } else {
        console.log('No next button found');
        break;
      }
    }

    console.log(`Answered ${answeredQuestions} questions out of ${questionCount} attempts`);
    expect(answeredQuestions).toBeGreaterThan(0);

    // Wait for AI analysis to complete
    console.log('Waiting for AI analysis to complete');
    await page.waitForSelector('.processing, .loading, [data-testid="processing"]', {
      state: 'visible',
      timeout: 5000
    }).catch(() => console.log('No processing indicator found'));

    // Wait for results (either the processing indicator disappears or results appear)
    await Promise.race([
      page.waitForSelector('.processing, .loading, [data-testid="processing"]', {
        state: 'hidden',
        timeout: 30000
      }),
      page.waitForSelector('.results, [data-testid="results"], [data-testid="rectified-time"]', {
        state: 'visible',
        timeout: 30000
      })
    ]);

    // Take a screenshot of the results
    await page.screenshot({ path: 'rectification-results.png' });

    // Check for rectified birth time
    const rectifiedTimeElement = await page.locator(
      '[data-testid="rectified-time"], .rectified-time, text:has-text("rectified"), text:has-text("Suggested")'
    ).first();

    if (await rectifiedTimeElement.count() > 0) {
      console.log('Rectified time found');

      // Check for confidence level
      const confidenceElement = await page.locator(
        '[data-testid="confidence"], .confidence, text:has-text("confidence"), text:has-text("reliability")'
      ).first();

      if (await confidenceElement.count() > 0) {
        console.log('Confidence level found');
        const confidenceText = await confidenceElement.textContent();
        console.log(`Confidence text: ${confidenceText}`);
      } else {
        console.log('No confidence indicator found');
      }

      // Check for comparison chart or original vs rectified time display
      const comparisonElement = await page.locator('.comparison, [data-testid="comparison"]').count();
      if (comparisonElement > 0) {
        console.log('Comparison view found');
      }

      // Check for detailed results button/link
      const detailedResultsButton = page.getByRole('button', {
        name: /detailed results|view results|complete results/i
      });

      if (await detailedResultsButton.count() > 0) {
        console.log('Detailed results button found');
        await detailedResultsButton.click();

        // Wait for detailed results page
        await page.waitForSelector('.detailed-results, [data-testid="detailed-results"]', {
          state: 'visible',
          timeout: 5000
        }).catch(() => console.log('Detailed results page not found or has different structure'));
      } else {
        console.log('No detailed results button found');
      }
    } else {
      console.log('No rectified time element found');

      // If we can't find specific elements, check for any result-like content
      const resultsContent = await page.locator('text:has-text("result"), text:has-text("birth time")').count();
      expect(resultsContent).toBeGreaterThan(0);
    }
  });
});
