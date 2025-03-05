/**
 * Basic Chart API Integration Test
 *
 * A simplified test to identify issues with the chart rendering
 * and API integration. This test focuses just on essential elements.
 */

import { test, expect } from '@playwright/test';
import { API_ENDPOINTS, TEST_DATA } from './constants';

test.describe('Basic Chart API Integration', () => {
  test('Chart rendering and structure test', async ({ page }) => {
    // Navigate to the application
    await page.goto('/birth-time-rectifier');
    console.log('Navigated to birth time rectifier page');

    // Take a screenshot of the initial state
    await page.screenshot({ path: 'initial-page.png' });
    console.log('Initial page screenshot saved');

    // Find and fill date input
    const dateInput = await page.locator('input[type="date"], [name="birthDate"]').first();
    if (await dateInput.count() > 0) {
      await dateInput.fill(TEST_DATA.STANDARD.birthDate);
      console.log(`Filled birth date: ${TEST_DATA.STANDARD.birthDate}`);
    } else {
      console.log('Date input not found');
    }

    // Find and fill time input
    const timeInput = await page.locator('input[type="time"], [name="birthTime"]').first();
    if (await timeInput.count() > 0) {
      await timeInput.fill(TEST_DATA.STANDARD.birthTime);
      console.log(`Filled birth time: ${TEST_DATA.STANDARD.birthTime}`);
    } else {
      console.log('Time input not found');
    }

    // Find and fill location input
    const locationInput = await page.locator('#birthPlace, input[name="birthPlace"]').first();
    if (await locationInput.count() > 0) {
      await locationInput.fill(TEST_DATA.STANDARD.birthPlace);
      console.log(`Filled birth location: ${TEST_DATA.STANDARD.birthPlace}`);
    } else {
      console.log('Location input not found, trying other selectors');

      const altLocationInput = await page.locator('input[placeholder*="location"], input[placeholder*="place"]').first();
      if (await altLocationInput.count() > 0) {
        await altLocationInput.fill(TEST_DATA.STANDARD.birthPlace);
        console.log(`Filled birth location using alternative selector: ${TEST_DATA.STANDARD.birthPlace}`);
      } else {
        console.log('Failed to find location input');
      }
    }

    // Try to locate and fill coordinates if available
    const latInput = await page.locator('input[name="latitude"]');
    const longInput = await page.locator('input[name="longitude"]');

    if (await latInput.count() > 0 && await longInput.count() > 0) {
      await latInput.fill(String(TEST_DATA.STANDARD.latitude));
      await longInput.fill(String(TEST_DATA.STANDARD.longitude));
      console.log('Filled latitude and longitude directly');
    }

    // Take screenshot after filling form
    await page.screenshot({ path: 'form-filled.png' });
    console.log('Form filled screenshot saved');

    // Find and click submit button
    const submitButton = await page.locator('button[type="submit"], button:has-text("Generate"), button:has-text("Submit")').first();
    if (await submitButton.count() > 0) {
      // Monitor network requests during form submission
      page.on('request', request => {
        const url = request.url();
        if (url.includes('/chart/generate') || url.includes('/api/chart/generate') ||
            url.includes('/chart') || url.includes('/api/chart')) {
          console.log(`API call detected: ${url}`);
        }
      });

      // Monitor network responses
      page.on('response', response => {
        const url = response.url();
        if (url.includes('/chart/generate') || url.includes('/api/chart/generate') ||
            url.includes('/chart') || url.includes('/api/chart')) {
          console.log(`API response received: ${url}, status: ${response.status()}`);
        }
      });

      await submitButton.click();
      console.log('Clicked submit button');

      // Wait for any form submission to complete
      await page.waitForTimeout(3000);
    } else {
      console.log('Submit button not found');
    }

    // Look for chart elements with very lenient detection
    await page.waitForSelector('svg, canvas, .chart, [class*="chart"], [data-testid*="chart"]', {
      timeout: 30000,
      state: 'visible'
    }).catch(() => console.log('No chart visualization found with common selectors'));

    // Take screenshot after chart generation
    await page.screenshot({ path: 'after-submission.png' });
    console.log('After submission screenshot saved');

    // Examine DOM structure to understand what's actually rendered
    const chartStructure = await page.evaluate(() => {
      // Helper to get a summary of an element and its children
      function summarizeElement(el, depth = 0) {
        if (!el) return '';

        const indent = ' '.repeat(depth * 2);
        const tag = el.tagName.toLowerCase();
        const id = el.id ? `#${el.id}` : '';
        const classes = el.className && typeof el.className === 'string' ? `.${el.className.replace(/\s+/g, '.')}` : '';
        const summary = `${indent}${tag}${id}${classes}`;

        let result = summary + '\n';

        // Get basic attributes
        const dataAttrs = {};
        for (const attr of el.attributes) {
          if (attr.name.startsWith('data-')) {
            dataAttrs[attr.name] = attr.value;
          }
        }

        if (Object.keys(dataAttrs).length > 0) {
          result += `${indent}  attributes: ${JSON.stringify(dataAttrs)}\n`;
        }

        // For SVG, look for specific elements
        if (tag === 'svg') {
          const circles = el.querySelectorAll('circle');
          const paths = el.querySelectorAll('path');
          const texts = el.querySelectorAll('text');

          result += `${indent}  SVG contains: ${circles.length} circles, ${paths.length} paths, ${texts.length} text elements\n`;

          // Sample a few text elements to see if they're planets
          if (texts.length > 0) {
            result += `${indent}  Sample text content: `;
            let sampleCount = Math.min(texts.length, 5);
            for (let i = 0; i < sampleCount; i++) {
              result += `"${texts[i].textContent}" `;
            }
            result += '\n';
          }
        }

        // For canvas, note dimensions
        if (tag === 'canvas') {
          result += `${indent}  Canvas dimensions: ${el.width}x${el.height}\n`;
        }

        // Recursively check children, but limit depth
        if (depth < 3) {
          for (const child of el.children) {
            result += summarizeElement(child, depth + 1);
          }
        }

        return result;
      }

      // Look for chart container
      const chartContainer = document.querySelector('.chart-container, .chart, [data-testid*="chart"]');
      if (chartContainer) {
        return {
          containerFound: true,
          structure: summarizeElement(chartContainer)
        };
      }

      // If no specific container, look for SVG or Canvas directly
      const svg = document.querySelector('svg');
      if (svg) {
        return {
          containerFound: true,
          structure: summarizeElement(svg),
          type: 'svg'
        };
      }

      const canvas = document.querySelector('canvas');
      if (canvas) {
        return {
          containerFound: true,
          structure: summarizeElement(canvas),
          type: 'canvas'
        };
      }

      // If nothing found, return the body structure for debugging
      return {
        containerFound: false,
        structure: 'No chart container found. Body structure:\n' + summarizeElement(document.body)
      };
    });

    console.log('Chart structure analysis:');
    console.log(chartStructure.containerFound ? 'Chart container found!' : 'No chart container found');
    console.log(chartStructure.structure);

    // Attempt to locate main chart elements with broader selectors
    const svgElements = await page.locator('svg').count();
    console.log(`Found ${svgElements} SVG elements on page`);

    const canvasElements = await page.locator('canvas').count();
    console.log(`Found ${canvasElements} Canvas elements on page`);

    // Check for any circular elements that might be planets
    const circleElements = await page.locator('circle, ellipse, .planet, [class*="planet"]').count();
    console.log(`Found ${circleElements} circular elements (potential planets)`);

    // Check for text elements that might be labels
    const textLabels = await page.locator('text, .label, [class*="label"]').count();
    console.log(`Found ${textLabels} text/label elements`);

    // Look for specific astrology-related elements with very broad matching
    const astroElements = await page.locator(':text("Sun"), :text("Moon"), :text("Mercury"), :text("Venus"), :text("Mars"), :text("Jupiter"), :text("Saturn"), :text("Ascendant"), :text("Ketu")').count();
    console.log(`Found ${astroElements} elements with astrological text content`);

    console.log('Test completed - screenshots saved for analysis');
  });

  test('Direct API testing for chart generation', async ({ request }) => {
    // Testing API connections directly
    console.log('Testing direct API integration');

    // Test both primary and alternative endpoints
    const testEndpoints = [
      { name: 'Chart Generate (Primary)', url: API_ENDPOINTS.chartGenerate },
      { name: 'Chart Generate (Alt)', url: API_ENDPOINTS.chartGenerateAlt }
    ];

    // Standard test payload
    const payload = {
      birth_date: TEST_DATA.STANDARD.birthDate,
      birth_time: TEST_DATA.STANDARD.birthTime,
      latitude: TEST_DATA.STANDARD.latitude,
      longitude: TEST_DATA.STANDARD.longitude,
      timezone: TEST_DATA.STANDARD.timezone,
      options: {
        house_system: "P",
        zodiac_type: "sidereal",
        ayanamsa: "lahiri"
      }
    };

    // Alternative payload format that might be required
    const altPayload = {
      birthDate: TEST_DATA.STANDARD.birthDate,
      birthTime: TEST_DATA.STANDARD.birthTime,
      latitude: TEST_DATA.STANDARD.latitude,
      longitude: TEST_DATA.STANDARD.longitude,
      timezone: TEST_DATA.STANDARD.timezone
    };

    // Check both potential payloads against both possible endpoints
    for (const endpoint of testEndpoints) {
      try {
        console.log(`Testing ${endpoint.name}: ${endpoint.url}`);

        // Try standard payload format
        const response = await request.post(endpoint.url, {
          data: payload,
          timeout: 30000
        });

        console.log(`Response status: ${response.status()}`);

        if (response.ok()) {
          console.log(`${endpoint.name} succeeded with standard payload`);
          const data = await response.json();
          console.log('Response data summary:');
          console.log(`- Contains planets: ${data.planets ? 'Yes (' + data.planets.length + ' planets)' : 'No'}`);
          console.log(`- Contains houses: ${data.houses ? 'Yes (' + data.houses.length + ' houses)' : 'No'}`);
          console.log(`- Contains ascendant: ${data.ascendant ? 'Yes' : 'No'}`);

          // Check for Ketu which was specifically mentioned in requirements
          if (data.planets) {
            const ketu = data.planets.find(p => p.name === 'Ketu');
            console.log(`- Contains Ketu: ${ketu ? 'Yes' : 'No'}`);
            if (ketu) {
              console.log(`  Ketu details: Sign: ${ketu.sign}, Degree: ${ketu.degree}`);
            }
          }

          break; // Success, no need to try alternative format
        } else {
          console.log(`${endpoint.name} failed with standard payload, trying alternative format`);

          // Try alternative payload format
          const altResponse = await request.post(endpoint.url, {
            data: altPayload,
            timeout: 30000
          });

          console.log(`Alternative format response status: ${altResponse.status()}`);

          if (altResponse.ok()) {
            console.log(`${endpoint.name} succeeded with alternative payload`);
            const data = await altResponse.json();
            console.log('Response data summary:');
            console.log(`- Contains planets: ${data.planets ? 'Yes (' + data.planets.length + ' planets)' : 'No'}`);
            console.log(`- Contains houses: ${data.houses ? 'Yes (' + data.houses.length + ' houses)' : 'No'}`);
            console.log(`- Contains ascendant: ${data.ascendant ? 'Yes' : 'No'}`);

            if (data.planets) {
              const ketu = data.planets.find(p => p.name === 'Ketu');
              console.log(`- Contains Ketu: ${ketu ? 'Yes' : 'No'}`);
              if (ketu) {
                console.log(`  Ketu details: Sign: ${ketu.sign}, Degree: ${ketu.degree}`);
              }
            }

            break; // Success with alternative format
          }
        }
      } catch (e) {
        console.log(`Error testing ${endpoint.name}: ${e.message}`);
      }
    }

    // Now test other related endpoints
    console.log('\nTesting chart questionnaire API');

    try {
      const questionnaireResponse = await request.get(API_ENDPOINTS.questionnaire);
      if (questionnaireResponse.ok()) {
        console.log('Questionnaire API succeeded');
        const questionData = await questionnaireResponse.json();
        console.log(`Retrieved ${Array.isArray(questionData) ? questionData.length : 'unknown number of'} questions`);
      } else {
        console.log(`Questionnaire API failed with status: ${questionnaireResponse.status()}`);

        // Try alternative endpoint
        const altQuestionnaireResponse = await request.get(API_ENDPOINTS.questionnaireAlt);
        if (altQuestionnaireResponse.ok()) {
          console.log('Alternative questionnaire API succeeded');
          const questionData = await altQuestionnaireResponse.json();
          console.log(`Retrieved ${Array.isArray(questionData) ? questionData.length : 'unknown number of'} questions`);
        } else {
          console.log(`Alternative questionnaire API failed with status: ${altQuestionnaireResponse.status()}`);
        }
      }
    } catch (e) {
      console.log(`Error testing questionnaire API: ${e.message}`);
    }

    // Test chart rectification API
    console.log('\nTesting chart rectification API');

    try {
      const rectifyPayload = {
        birthDetails: {
          birthDate: TEST_DATA.STANDARD.birthDate,
          birthTime: TEST_DATA.STANDARD.birthTime,
          latitude: TEST_DATA.STANDARD.latitude,
          longitude: TEST_DATA.STANDARD.longitude,
          timezone: TEST_DATA.STANDARD.timezone
        },
        questionnaire: {
          answers: [
            { question: "q1", answer: "yes" },
            { question: "q2", answer: "no" }
          ]
        }
      };

      const rectifyResponse = await request.post(API_ENDPOINTS.rectify, {
        data: rectifyPayload,
        timeout: 30000
      });

      if (rectifyResponse.ok()) {
        console.log('Rectification API succeeded');
        const rectifyData = await rectifyResponse.json();
        console.log('Rectification data summary:');
        console.log(`- Original time: ${rectifyData.originalTime || rectifyData.original_time}`);
        console.log(`- Rectified time: ${rectifyData.rectifiedTime || rectifyData.rectified_time}`);
        console.log(`- Confidence: ${rectifyData.confidence || rectifyData.confidence_score || 'Not provided'}`);
      } else {
        console.log(`Rectification API failed with status: ${rectifyResponse.status()}`);

        // Try alternative endpoint
        const altRectifyResponse = await request.post(API_ENDPOINTS.rectifyAlt, {
          data: rectifyPayload,
          timeout: 30000
        });

        if (altRectifyResponse.ok()) {
          console.log('Alternative rectification API succeeded');
          const rectifyData = await altRectifyResponse.json();
          console.log('Rectification data summary:');
          console.log(`- Original time: ${rectifyData.originalTime || rectifyData.original_time}`);
          console.log(`- Rectified time: ${rectifyData.rectifiedTime || rectifyData.rectified_time}`);
          console.log(`- Confidence: ${rectifyData.confidence || rectifyData.confidence_score || 'Not provided'}`);
        } else {
          console.log(`Alternative rectification API failed with status: ${altRectifyResponse.status()}`);

          // Try simpler payload as last resort
          const simplePayload = {
            date: TEST_DATA.STANDARD.birthDate,
            time: TEST_DATA.STANDARD.birthTime,
            latitude: TEST_DATA.STANDARD.latitude,
            longitude: TEST_DATA.STANDARD.longitude,
            timezone: TEST_DATA.STANDARD.timezone
          };

          const simpleRectifyResponse = await request.post(API_ENDPOINTS.rectify, {
            data: simplePayload,
            timeout: 30000
          });

          if (simpleRectifyResponse.ok()) {
            console.log('Simple format rectification API succeeded');
            const rectifyData = await simpleRectifyResponse.json();
            console.log('Rectification data summary:');
            console.log(`- Original time: ${rectifyData.originalTime || rectifyData.original_time}`);
            console.log(`- Rectified time: ${rectifyData.rectifiedTime || rectifyData.rectified_time}`);
            console.log(`- Confidence: ${rectifyData.confidence || rectifyData.confidence_score || 'Not provided'}`);
          } else {
            console.log(`Simple format rectification API failed with status: ${simpleRectifyResponse.status()}`);
          }
        }
      }
    } catch (e) {
      console.log(`Error testing rectification API: ${e.message}`);
    }

    console.log('Direct API testing completed');
  });
});
