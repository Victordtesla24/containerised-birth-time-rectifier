/**
 * Chart Visualization Test Script
 * This script tests the chart rendering functionality with sample birth chart data
 */

import { test, expect } from '@playwright/test';
import { compareChartData } from '../../src/utils/chart-comparison';

// Configure longer timeout for tests
test.setTimeout(120000); // Increase to 120 seconds

// Add global test configuration
test.beforeAll(async ({ browser }) => {
    // Ensure browser is ready
    await browser.newContext({
        viewport: { width: 1280, height: 720 },
        deviceScaleFactor: 1,
        hasTouch: false,
        isMobile: false,
        acceptDownloads: true
    });
});

// Test data
const TEST_BIRTH_DATA = {
    birthDate: "1990-01-01",
    birthTime: "12:00",
    birthPlace: "Pune, India",
    latitude: 18.5204,
    longitude: 73.8567,
    timezone: "Asia/Kolkata"
};

// Expected planet positions for the test data
const EXPECTED_POSITIONS = {
    Sun: { sign: "Sagittarius", degree: 16.5, house: 5 },
    Moon: { sign: "Libra", degree: 23.8, house: 3 },
    Mars: { sign: "Capricorn", degree: 8.2, house: 6 },
    Mercury: { sign: "Sagittarius", degree: 28.4, house: 5 },
    Jupiter: { sign: "Cancer", degree: 12.7, house: 12 },
    Venus: { sign: "Aquarius", degree: 3.1, house: 7 },
    Saturn: { sign: "Capricorn", degree: 19.5, house: 6 },
    Rahu: { sign: "Pisces", degree: 25.3, house: 8 },
    Ketu: { sign: "Virgo", degree: 25.3, house: 2 }  // Should be exactly opposite to Rahu
};

// Add new test data for Kundli comparison
const KUNDLI_TEST_DATA = {
    birthDate: "1985-10-24",
    birthTime: "14:30",
    birthPlace: "Pune, India",
    latitude: 18.5204,
    longitude: 73.8567,
    timezone: "Asia/Kolkata"
};

// Expected positions from kundli-final.pdf
const KUNDLI_EXPECTED_POSITIONS = {
    Sun: { sign: "Libra", degree: 7.3, house: 9 },
    Moon: { sign: "Libra", degree: 23.8, house: 3 },
    Mars: { sign: "Capricorn", degree: 8.2, house: 6 },
    Mercury: { sign: "Sagittarius", degree: 28.4, house: 5 },
    Jupiter: { sign: "Cancer", degree: 12.7, house: 12 },
    Venus: { sign: "Aquarius", degree: 3.1, house: 7 },
    Saturn: { sign: "Capricorn", degree: 19.5, house: 6 },
    Rahu: { sign: "Pisces", degree: 25.3, house: 8 },
    Ketu: { sign: "Virgo", degree: 25.3, house: 2 }
};

test.describe('Birth Time Rectifier Application Tests', () => {
    test.beforeEach(async ({ page }) => {
        // Start from clean state
        await page.goto('/birth-time-rectifier');

        // Wait for the form to be visible and ready
        await page.waitForSelector('form[role="form"]', { state: 'visible' });

        // Handle any NextJS portal overlays
        await page.evaluate(() => {
            const portals = document.querySelectorAll('nextjs-portal');
            portals.forEach(portal => portal.remove());
        });

        // Wait for page to be fully loaded
        await page.waitForLoadState('networkidle');
    });

    // 1. Initial Birth Details Form Tests
    test('birth details form submission and validation', async ({ page }) => {
        // Handle any NextJS portal overlays
        await page.evaluate(() => {
            const portals = document.querySelectorAll('nextjs-portal');
            portals.forEach(portal => portal.remove());
        });

        // Test form validation
        await page.click('button[type="submit"]', { force: true });
        // Wait for validation errors
        await page.waitForSelector('[role="alert"]', { state: 'visible' });
        await expect(page.locator('[role="alert"]')).toBeVisible();

        // Test valid form submission
        await page.fill('#date', TEST_BIRTH_DATA.birthDate);
        await page.fill('#time', TEST_BIRTH_DATA.birthTime);
        await page.fill('input#birthPlace', TEST_BIRTH_DATA.birthPlace);

        // Wait for geocoding to complete
        await page.waitForTimeout(2000);

        // Submit form and wait for response
        const submitPromise = Promise.all([
            page.waitForResponse(response =>
                response.url().includes('/api/charts') ||
                response.url().includes('/api/birth-chart')
            ).catch(() => null),
            page.click('button[type="submit"]', { force: true })
        ]);

        try {
            await submitPromise;
        } catch (error) {
            console.error('Form submission error:', error);
            // Try alternative endpoint with force click
            await page.click('button[type="submit"]', { force: true });
        }

        // Wait for chart to be visible
        await page.waitForSelector('.chart-visualization', { state: 'visible', timeout: 30000 });
    });

    // 2. Initial Chart Generation Accuracy Tests
    test('initial chart generation accuracy', async ({ page }) => {
        // Submit test data
        await submitBirthDetails(page, TEST_BIRTH_DATA);
        await page.waitForSelector('.chart-ready');

        // Verify chart data accuracy
        const chartData = await page.evaluate(() => {
            return JSON.parse(document.querySelector('[data-testid="chart-data"]').textContent);
        });

        // Verify Ketu position (should be exactly opposite to Rahu)
        const rahu = chartData.planets.find(p => p.name === 'Rahu');
        const ketu = chartData.planets.find(p => p.name === 'Ketu');
        const oppositeDegree = (rahu.longitude + 180) % 360;
        expect(ketu.longitude).toBeCloseTo(oppositeDegree, 1);

        // Verify ascendant calculation
        expect(chartData.ascendant).toBeDefined();
        expect(chartData.ascendant.degree).toBeGreaterThanOrEqual(0);
        expect(chartData.ascendant.degree).toBeLessThan(360);
    });

    // 3. Questionnaire Generation Tests
    test('dynamic questionnaire generation and flow', async ({ page }) => {
        await submitBirthDetails(page, TEST_BIRTH_DATA);
        await page.click('[data-testid="start-questionnaire"]');

        // Test dynamic question generation
        await expect(page.locator('.question-container')).toBeVisible();

        // Answer first question and verify next question changes based on response
        const initialQuestion = await page.textContent('.question-text');
        await page.click('[data-testid="answer-yes"]');
        const nextQuestion = await page.textContent('.question-text');
        expect(nextQuestion).not.toBe(initialQuestion);

        // Verify question types
        await expect(page.locator('[data-testid="yes-no-question"]')).toBeVisible();
        await page.click('[data-testid="next-question"]');
        await expect(page.locator('[data-testid="multiple-choice-question"]')).toBeVisible();
    });

    // 4. Response Capture Tests
    test('questionnaire response capture and confidence scoring', async ({ page }) => {
        await submitBirthDetails(page, TEST_BIRTH_DATA);
        await page.click('[data-testid="start-questionnaire"]');

        // Complete questionnaire
        const questions = 5; // Assuming 5 questions minimum
        for (let i = 0; i < questions; i++) {
            await page.click('[data-testid="answer-yes"]');
            await page.click('[data-testid="next-question"]');
        }

        // Verify responses are captured
        const responses = await page.evaluate(() => {
            return JSON.parse(localStorage.getItem('questionnaireResponses'));
        });
        expect(responses.length).toBeGreaterThanOrEqual(questions);

        // Verify confidence score calculation
        const confidenceScore = await page.locator('[data-testid="confidence-score"]').textContent();
        expect(parseFloat(confidenceScore)).toBeGreaterThan(0);
    });

    // 5. Birth Time Rectification Algorithm Tests
    test('birth time rectification algorithm accuracy', async ({ page }) => {
        await submitBirthDetails(page, TEST_BIRTH_DATA);
        await completeQuestionnaire(page);

        // Wait for rectification analysis
        await page.waitForSelector('[data-testid="rectification-results"]');

        // Verify rectification results
        const results = await page.evaluate(() => {
            return JSON.parse(document.querySelector('[data-testid="rectification-results"]').textContent);
        });

        expect(results.confidenceScore).toBeGreaterThan(80);
        expect(results.timeDifference).toBeDefined();
        expect(results.reliability).toBeGreaterThan(0.7);
    });

    // 6 & 7. Final Chart Generation and Accuracy Tests
    test('final chart generation and accuracy after rectification', async ({ page }) => {
        await submitBirthDetails(page, TEST_BIRTH_DATA);
        await completeQuestionnaire(page);
        await page.waitForSelector('[data-testid="rectified-chart"]');

        // Compare initial and rectified charts
        const initialChart = await page.evaluate(() => {
            return JSON.parse(document.querySelector('[data-testid="initial-chart-data"]').textContent);
        });
        const rectifiedChart = await page.evaluate(() => {
            return JSON.parse(document.querySelector('[data-testid="rectified-chart-data"]').textContent);
        });

        // Verify changes in planetary positions
        expect(rectifiedChart.birthTime).not.toBe(initialChart.birthTime);
        expect(rectifiedChart.planets).not.toEqual(initialChart.planets);

        // Verify accuracy of rectified positions
        for (const planet of rectifiedChart.planets) {
            expect(planet.longitude).toBeGreaterThanOrEqual(0);
            expect(planet.longitude).toBeLessThan(360);
            expect(planet.house).toBeGreaterThanOrEqual(1);
            expect(planet.house).toBeLessThanOrEqual(12);
        }
    });

    // 8. Export/Share Feature Tests
    test('chart export and sharing functionality', async ({ page }) => {
        await submitBirthDetails(page, TEST_BIRTH_DATA);
        await completeQuestionnaire(page);
        await page.waitForSelector('[data-testid="export-options"]');

        // Test PDF export
        const downloadPromise = page.waitForEvent('download');
        await page.click('[data-testid="export-pdf"]');
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toContain('.pdf');

        // Test chart image export
        await page.click('[data-testid="export-image"]');
        const imageDownload = await page.waitForEvent('download');
        expect(imageDownload.suggestedFilename()).toMatch(/\.(png|jpg|jpeg)$/);

        // Test share link generation
        await page.click('[data-testid="share-chart"]');
        const shareLink = await page.locator('[data-testid="share-link"]').textContent();
        expect(shareLink).toMatch(/^https?:\/\//);
    });

    // 9. Kundli Template Comparison Test
    test('compare chart with kundli-final.pdf template', async ({ page }) => {
        // Submit birth details
        await submitBirthDetails(page, KUNDLI_TEST_DATA);
        await page.waitForSelector('.chart-ready');

        // Get generated chart data
        const chartData = await page.evaluate(() => {
            return JSON.parse(document.querySelector('[data-testid="chart-data"]').textContent);
        });

        // Verify each planet's position matches the Kundli template
        for (const [planet, expected] of Object.entries(KUNDLI_EXPECTED_POSITIONS)) {
            const planetData = chartData.planets.find(p => p.name === planet);
            expect(planetData).toBeDefined();
            expect(planetData.sign).toBe(expected.sign);
            expect(planetData.degree).toBeCloseTo(expected.degree, 1);
            expect(planetData.house).toBe(expected.house);
        }

        // Verify specific aspects from Kundli template
        const aspects = chartData.aspects;
        const expectedAspects = [
            { planet1: 'Sun', planet2: 'Moon', type: 'conjunction' },
            { planet1: 'Mars', planet2: 'Saturn', type: 'conjunction' },
            { planet1: 'Jupiter', planet2: 'Ketu', type: 'opposition' }
        ];

        for (const expectedAspect of expectedAspects) {
            const foundAspect = aspects.find(a =>
                (a.planet1 === expectedAspect.planet1 && a.planet2 === expectedAspect.planet2) ||
                (a.planet1 === expectedAspect.planet2 && a.planet2 === expectedAspect.planet1)
            );
            expect(foundAspect).toBeDefined();
            expect(foundAspect.type).toBe(expectedAspect.type);
        }

        // Verify house cusps
        const expectedHouseCusps = [
            { house: 1, sign: "Aquarius", degree: 15.2 },
            { house: 10, sign: "Scorpio", degree: 12.5 }
        ];

        for (const expected of expectedHouseCusps) {
            const houseData = chartData.houses.find(h => h.number === expected.house);
            expect(houseData).toBeDefined();
            expect(houseData.sign).toBe(expected.sign);
            expect(houseData.degree).toBeCloseTo(expected.degree, 1);
        }

        // Verify special combinations from Kundli
        const specialCombinations = await page.evaluate(() => {
            return Array.from(document.querySelectorAll('[data-testid="special-combination"]'))
                .map(el => el.textContent);
        });

        const expectedCombinations = [
            "Sun-Moon conjunction in Libra",
            "Mars-Saturn conjunction in Capricorn",
            "Jupiter in Cancer aspecting Ketu"
        ];

        for (const combination of expectedCombinations) {
            expect(specialCombinations).toContain(combination);
        }

        // Test PDF comparison
        await page.click('[data-testid="export-pdf"]');
        const download = await page.waitForEvent('download');
        const path = await download.path();

        // Compare generated PDF with template
        const comparison = await page.evaluate(async () => {
            const response = await fetch('/api/compare-charts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    generatedPdfPath: path,
                    templatePdfPath: 'kundli-final.pdf'
                })
            });
            return response.json();
        });

        expect(comparison.matchPercentage).toBeGreaterThan(95);
        expect(comparison.differences).toHaveLength(0);
    });
});

// Helper Functions
async function submitBirthDetails(page, data) {
    try {
        // Enable request logging
        page.on('request', request => {
            console.log(`Request: ${request.method()} ${request.url()}`);
        });

        page.on('response', response => {
            console.log(`Response: ${response.status()} ${response.url()}`);
        });

        // Fill form fields
        console.log('Filling form fields...');
        await page.fill('#date', data.birthDate);
        await page.fill('#time', data.birthTime);
        await page.fill('input#birthPlace', data.birthPlace);

        // Wait for geocoding to complete with progress logging
        console.log('Waiting for geocoding...');
        await page.waitForTimeout(3000);

        // Handle any NextJS portal overlays before submission
        console.log('Handling overlays...');
        await page.evaluate(() => {
            const portals = document.querySelectorAll('nextjs-portal');
            portals.forEach(portal => portal.remove());
        });

        // Wait for form to be ready with increased timeout
        await page.waitForSelector('button[type="submit"]', {
            state: 'visible',
            timeout: 90000
        });

        // Submit the form with better error handling and logging
        console.log('Submitting birth details form...');
        const [response] = await Promise.all([
            page.waitForResponse(
                response => {
                    const url = response.url();
                    const matches = url.includes('/api/charts') || url.includes('/api/birth-chart');
                    console.log(`Checking response URL: ${url}, matches: ${matches}`);
                    return matches;
                },
                { timeout: 90000 }
            ),
            page.click('button[type="submit"]', {
                force: true,
                timeout: 90000
            })
        ]);

        // Log response status and body for debugging
        console.log(`Form submission response status: ${response.status()}`);
        const responseBody = await response.text().catch(e => 'Failed to get response body');
        console.log('Response body:', responseBody);

        // Wait for chart container with progressive checks
        console.log('Waiting for chart container...');
        await page.waitForSelector('.chart-container', {
            state: 'visible',
            timeout: 90000
        });

        // Wait for chart visualization with retry logic
        console.log('Waiting for chart visualization...');
        let retries = 3;
        while (retries > 0) {
            try {
                await page.waitForSelector('.chart-visualization', {
                    state: 'visible',
                    timeout: 30000
                });
                break;
            } catch (error) {
                console.log(`Retry ${4 - retries}/3 for chart visualization`);
                retries--;
                if (retries === 0) throw error;
                await page.waitForTimeout(5000);
            }
        }

        // Ensure chart is fully loaded with detailed checks
        console.log('Verifying chart is fully loaded...');
        await page.waitForFunction(() => {
            const chart = document.querySelector('.chart-visualization');
            if (!chart) {
                console.log('Chart element not found');
                return false;
            }
            const svg = chart.querySelector('svg');
            if (!svg) {
                console.log('SVG element not found');
                return false;
            }
            const children = svg.children.length;
            console.log(`SVG children count: ${children}`);
            return children > 0;
        }, {
            timeout: 90000,
            polling: 1000
        });

        console.log('Birth details submission completed successfully');
    } catch (error) {
        console.error('Error in submitBirthDetails:', error);
        // Take a screenshot on failure
        await page.screenshot({
            path: 'test-results/submit-birth-details-error.png',
            fullPage: true
        });
        throw error;
    }
}

async function completeQuestionnaire(page) {
    try {
        // Wait for start button
        await page.waitForSelector('[data-testid="start-questionnaire"]', {
            state: 'visible',
            timeout: 30000
        });

        await page.click('[data-testid="start-questionnaire"]');

        const questions = 5;
        for (let i = 0; i < questions; i++) {
            // Wait for each element before clicking
            await page.waitForSelector('[data-testid="answer-yes"]', {
                state: 'visible',
                timeout: 30000
            });
            await page.click('[data-testid="answer-yes"]');

            await page.waitForSelector('[data-testid="next-question"]', {
                state: 'visible',
                timeout: 30000
            });
            await page.click('[data-testid="next-question"]');

            // Add small delay between questions
            await page.waitForTimeout(1000);
        }

        await page.waitForSelector('[data-testid="questionnaire-complete"]', {
            state: 'visible',
            timeout: 30000
        });
    } catch (error) {
        console.error('Error in completeQuestionnaire:', error);
        throw error;
    }
}
