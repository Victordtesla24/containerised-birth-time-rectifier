// @ts-check
const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './',
  testMatch: '**/*.js',
  use: {
    headless: true,
    launchOptions: {
      args: [
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--no-sandbox'
      ]
    }
  },
  reporter: 'list',
});
